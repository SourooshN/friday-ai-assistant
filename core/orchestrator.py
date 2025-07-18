"""
Core Orchestrator for Friday AI Assistant
Manages agent coordination, task planning, and execution
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Set, Type
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import importlib
import inspect
from loguru import logger

from agents.base_agent import BaseAgent, Task, TaskResult, AgentCapability
from core.models.model_manager import ModelManager
from core.memory.short_term import ShortTermMemory
from core.memory.long_term import LongTermMemory
from core.security.policy_engine import PolicyEngine
from scripts.utils.helpers import generate_id


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    PLANNING = "planning"
    ASSIGNED = "assigned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskPlan:
    """Execution plan for a task"""
    task_id: str
    steps: List[Dict[str, Any]]
    dependencies: Dict[str, List[str]]  # step_id -> [dependency_ids]
    assigned_agents: Dict[str, str]  # step_id -> agent_name
    estimated_duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class Orchestrator:
    """Central orchestration engine for Friday"""
    
    def __init__(
        self,
        model_manager: ModelManager,
        memory: LongTermMemory,
        policy_engine: PolicyEngine,
        config: Dict[str, Any]
    ):
        """Initialize orchestrator"""
        self.model_manager = model_manager
        self.long_term_memory = memory
        self.policy_engine = policy_engine
        self.config = config
        
        # Agent management
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_capabilities: Dict[AgentCapability, List[str]] = {}
        
        # Task management
        self.active_tasks: Dict[str, Task] = {}
        self.task_status: Dict[str, TaskStatus] = {}
        self.task_plans: Dict[str, TaskPlan] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        
        # Memory
        self.short_term_memory = ShortTermMemory(config.get('memory', {}).get('short_term', {}))
        
        # Configuration
        self.max_concurrent_tasks = config.get('max_agents', 10)
        self.task_timeout = config.get('task_timeout', 300)
        self.planning_model = config.get('planning_model', 'mistral:latest')
        self.reflection_enabled = config.get('reflection_enabled', True)
        
        # Execution tracking
        self.execution_history: List[Dict[str, Any]] = []
        self.current_executions: Set[str] = set()
        
        # Background tasks
        self.worker_tasks: List[asyncio.Task] = []
        
        logger.info("Initialized Orchestrator")

    async def initialize(self):
        """Initialize orchestrator and load agents"""
        logger.info("Initializing Orchestrator...")
        
        # Start memory systems
        await self.short_term_memory.start()
        
        # Load available agents
        await self._discover_agents()
        
        # Start worker tasks
        for i in range(min(3, self.max_concurrent_tasks)):
            worker = asyncio.create_task(self._task_worker(i))
            self.worker_tasks.append(worker)
        
        logger.info(f"Orchestrator initialized with {len(self.agents)} agents")

    async def _discover_agents(self):
        """Discover and load available agents"""
        # Import agent modules
        agent_modules = [
            "agents.cybersecurity.scanner_agent",
            "agents.development.coding_agent",
            "agents.web.automation_agent",
            "agents.system.os_control_agent",
            "agents.supervisor.orchestrator_agent"
        ]
        
        for module_name in agent_modules:
            try:
                module = importlib.import_module(module_name)
                
                # Find agent classes in module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseAgent) and 
                        obj != BaseAgent):
                        
                        # Create agent instance
                        agent_config = self._get_agent_config(name)
                        agent = obj(
                            config=agent_config,
                            model_manager=self.model_manager,
                            memory=self.short_term_memory,
                            policy_engine=self.policy_engine
                        )
                        
                        # Register agent
                        self.register_agent(agent)
                        
            except ImportError as e:
                logger.warning(f"Could not import agent module {module_name}: {e}")
            except Exception as e:
                logger.error(f"Error loading agent from {module_name}: {e}")

    def _get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for specific agent"""
        # Load from agent_configs.yaml if available
        # For now, return default config
        from agents.base_agent import AgentConfig, AgentCapability
        
        return AgentConfig(
            name=agent_name,
            description=f"Agent: {agent_name}",
            capabilities=[AgentCapability.PLANNING]  # Default capability
        )

    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator"""
        name = agent.config.name
        self.agents[name] = agent
        
        # Index capabilities
        for capability in agent.config.capabilities:
            if capability not in self.agent_capabilities:
                self.agent_capabilities[capability] = []
            self.agent_capabilities[capability].append(name)
        
        logger.info(f"Registered agent: {name} with capabilities: {[c.value for c in agent.config.capabilities]}")

    async def process_request(self, request: str, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """Process a user request"""
        logger.info(f"Processing request: {request[:100]}...")
        
        # Add to conversation history
        await self.short_term_memory.add_conversation_turn("user", request, context)
        
        # Create task
        task = await self._create_task_from_request(request, context)
        
        # Plan execution
        plan = await self._plan_task_execution(task)
        
        # Execute task
        result = await self.execute_task(task, plan)
        
        # Add result to conversation
        await self.short_term_memory.add_conversation_turn(
            "assistant",
            result.result if result.success else f"Error: {result.error}",
            {"task_id": task.id, "success": result.success}
        )
        
        return result

    async def _create_task_from_request(self, request: str, context: Optional[Dict[str, Any]] = None) -> Task:
        """Create a task from user request"""
        # Use LLM to parse request into task
        prompt = f"""
Given the user request, create a structured task.

User request: {request}
Context: {json.dumps(context or {})}

Respond with a JSON object containing:
- type: The type of task (e.g., "coding", "web_search", "system_control")
- description: Clear description of what needs to be done
- priority: 1-5 (5 being highest)
- parameters: Any specific parameters needed

JSON response:
"""
        
        result = await self.model_manager.generate(
            prompt=prompt,
            model=self.planning_model,
            temperature=0.3,
            max_tokens=500
        )
        
        try:
            # Parse LLM response
            task_data = json.loads(result.text)
            
            task = Task(
                id=generate_id("task"),
                description=task_data.get("description", request),
                type=task_data.get("type", "general"),
                priority=task_data.get("priority", 3),
                parameters=task_data.get("parameters", {})
            )
            
        except json.JSONDecodeError:
            # Fallback to simple task
            task = Task(
                id=generate_id("task"),
                description=request,
                type="general",
                priority=3,
                parameters={}
            )
        
        # Store task
        self.active_tasks[task.id] = task
        self.task_status[task.id] = TaskStatus.PENDING
        
        return task

    async def _plan_task_execution(self, task: Task) -> TaskPlan:
        """Create execution plan for a task"""
        self.task_status[task.id] = TaskStatus.PLANNING
        
        # Use LLM to break down task
        prompt = f"""
Create an execution plan for this task:

Task: {task.description}
Type: {task.type}
Parameters: {json.dumps(task.parameters)}

Available agents and their capabilities:
{self._format_agent_capabilities()}

Break down the task into steps and assign appropriate agents.

Respond with a JSON object containing:
- steps: Array of step objects with id, description, agent_type, and parameters
- dependencies: Object mapping step_id to array of dependency step_ids

JSON response:
"""
        
        result = await self.model_manager.generate(
            prompt=prompt,
            model=self.planning_model,
            temperature=0.3,
            max_tokens=1000
        )
        
        try:
            plan_data = json.loads(result.text)
            
            # Create plan
            plan = TaskPlan(
                task_id=task.id,
                steps=plan_data.get("steps", [{"id": "1", "description": task.description, "agent_type": "general"}]),
                dependencies=plan_data.get("dependencies", {}),
                assigned_agents={},
                estimated_duration=len(plan_data.get("steps", [])) * 30  # 30s per step estimate
            )
            
            # Assign agents to steps
            for step in plan.steps:
                agent_name = await self._select_agent_for_step(step)
                if agent_name:
                    plan.assigned_agents[step["id"]] = agent_name
            
        except json.JSONDecodeError:
            # Fallback to simple plan
            plan = TaskPlan(
                task_id=task.id,
                steps=[{"id": "1", "description": task.description}],
                dependencies={},
                assigned_agents={},
                estimated_duration=30
            )
        
        self.task_plans[task.id] = plan
        return plan

    async def _select_agent_for_step(self, step: Dict[str, Any]) -> Optional[str]:
        """Select best agent for a step"""
        agent_type = step.get("agent_type", "general")
        
        # Find agents with matching capabilities
        # For now, return first available agent
        for agent_name, agent in self.agents.items():
            # Check if agent can handle this type of step
            if await agent.can_handle(Task(
                id=step["id"],
                description=step["description"],
                type=agent_type,
                parameters=step.get("parameters", {})
            )):
                return agent_name
        
        return None

    async def execute_task(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Execute a task according to plan"""
        self.task_status[task.id] = TaskStatus.ASSIGNED
        
        # Add to queue for execution
        await self.task_queue.put((task, plan))
        
        # Wait for completion
        while self.task_status[task.id] not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            await asyncio.sleep(0.5)
        
        # Get result
        for record in reversed(self.execution_history):
            if record["task_id"] == task.id:
                return record["result"]
        
        # Shouldn't happen
        return TaskResult(
            task_id=task.id,
            success=False,
            result=None,
            error="Task result not found"
        )

    async def _task_worker(self, worker_id: int):
        """Background worker for task execution"""
        logger.info(f"Task worker {worker_id} started")
        
        while True:
            try:
                # Get task from queue
                task, plan = await self.task_queue.get()
                
                if task.id in self.current_executions:
                    continue
                
                self.current_executions.add(task.id)
                self.task_status[task.id] = TaskStatus.EXECUTING
                
                # Execute plan steps
                result = await self._execute_plan(task, plan)
                
                # Update status
                self.task_status[task.id] = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
                self.current_executions.remove(task.id)
                
                # Store result
                self.execution_history.append({
                    "task_id": task.id,
                    "timestamp": datetime.now(),
                    "result": result,
                    "plan": plan
                })
                
                # Log to long-term memory
                await self.long_term_memory.log_agent_task(
                    agent_name="orchestrator",
                    task_id=task.id,
                    task_type=task.type,
                    success=result.success,
                    duration=0,  # TODO: Track actual duration
                    result=result.result,
                    metadata={"plan": plan.steps}
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)

    async def _execute_plan(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Execute a task plan"""
        step_results = {}
        overall_success = True
        final_result = None
        errors = []
        
        # Execute steps in dependency order
        executed_steps = set()
        
        while len(executed_steps) < len(plan.steps):
            # Find steps that can be executed
            ready_steps = []
            
            for step in plan.steps:
                step_id = step["id"]
                
                if step_id in executed_steps:
                    continue
                
                # Check dependencies
                deps = plan.dependencies.get(step_id, [])
                if all(dep in executed_steps for dep in deps):
                    ready_steps.append(step)
            
            if not ready_steps:
                # No steps ready - might be circular dependency
                errors.append("Circular dependency detected in plan")
                overall_success = False
                break
            
            # Execute ready steps in parallel
            step_tasks = []
            for step in ready_steps:
                agent_name = plan.assigned_agents.get(step["id"])
                if agent_name and agent_name in self.agents:
                    agent = self.agents[agent_name]
                    
                    # Create sub-task for step
                    sub_task = Task(
                        id=f"{task.id}_{step['id']}",
                        description=step["description"],
                        type=step.get("type", "general"),
                        parameters=step.get("parameters", {}),
                        dependencies=plan.dependencies.get(step["id"], [])
                    )
                    
                    step_tasks.append(self._execute_step(agent, sub_task, step_results))
                else:
                    errors.append(f"No agent available for step {step['id']}")
            
            # Wait for steps to complete
            if step_tasks:
                results = await asyncio.gather(*step_tasks, return_exceptions=True)
                
                for i, result in enumerate(results):
                    step = ready_steps[i]
                    step_id = step["id"]
                    
                    if isinstance(result, Exception):
                        step_results[step_id] = TaskResult(
                            task_id=step_id,
                            success=False,
                            result=None,
                            error=str(result)
                        )
                        errors.append(f"Step {step_id} failed: {result}")
                        overall_success = False
                    else:
                        step_results[step_id] = result
                        if not result.success:
                            errors.append(f"Step {step_id} failed: {result.error}")
                            overall_success = False
                    
                    executed_steps.add(step_id)
        
        # Compile final result
        if plan.steps:
            # Get result from last step
            last_step_id = plan.steps[-1]["id"]
            if last_step_id in step_results:
                final_result = step_results[last_step_id].result
        
        # Apply reflection if enabled
        if self.reflection_enabled and overall_success:
            final_result = await self._reflect_on_result(task, final_result, step_results)
        
        return TaskResult(
            task_id=task.id,
            success=overall_success,
            result=final_result,
            error="; ".join(errors) if errors else None,
            metadata={
                "steps_executed": len(executed_steps),
                "total_steps": len(plan.steps),
                "step_results": {k: v.success for k, v in step_results.items()}
            }
        )

    async def _execute_step(
        self,
        agent: BaseAgent,
        task: Task,
        previous_results: Dict[str, TaskResult]
    ) -> TaskResult:
        """Execute a single step with an agent"""
        # Add previous results to task parameters
        if task.dependencies:
            task.parameters["previous_results"] = {
                dep_id: previous_results[dep_id].result
                for dep_id in task.dependencies
                if dep_id in previous_results
            }
        
        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                agent.execute(task),
                timeout=self.task_timeout
            )
            return result
        except asyncio.TimeoutError:
            return TaskResult(
                task_id=task.id,
                success=False,
                result=None,
                error=f"Task timed out after {self.task_timeout}s"
            )

    async def _reflect_on_result(
        self,
        task: Task,
        result: Any,
        step_results: Dict[str, TaskResult]
    ) -> Any:
        """Use reflection to improve result"""
        prompt = f"""
Review this task execution and result:

Original Task: {task.description}
Result: {json.dumps(result) if isinstance(result, (dict, list)) else str(result)}

Step Results:
{json.dumps({k: v.success for k, v in step_results.items()}, indent=2)}

Is the result complete and correct? If not, what improvements could be made?
If the result is good, respond with "APPROVED".
If improvements are needed, describe them.
"""
        
        reflection = await self.model_manager.generate(
            prompt=prompt,
            model=self.planning_model,
            temperature=0.5,
            max_tokens=500
        )
        
        if "APPROVED" not in reflection.text:
            # Log reflection feedback
            logger.info(f"Reflection feedback: {reflection.text[:200]}...")
            
            # Could implement automatic improvement here
            # For now, just return original result with reflection note
            if isinstance(result, dict):
                result["reflection_note"] = reflection.text
        
        return result

    def _format_agent_capabilities(self) -> str:
        """Format agent capabilities for prompt"""
        lines = []
        for agent_name, agent in self.agents.items():
            caps = [c.value for c in agent.config.capabilities]
            lines.append(f"- {agent_name}: {', '.join(caps)}")
        return "\n".join(lines)

    async def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "agents": {
                name: agent.get_status()
                for name, agent in self.agents.items()
            },
            "active_tasks": len(self.active_tasks),
            "task_queue_size": self.task_queue.qsize(),
            "current_executions": len(self.current_executions),
            "memory_stats": self.short_term_memory.get_stats(),
            "recent_tasks": [
                {
                    "task_id": record["task_id"],
                    "timestamp": record["timestamp"].isoformat(),
                    "success": record["result"].success
                }
                for record in self.execution_history[-10:]
            ]
        }

    async def cleanup(self):
        """Clean up orchestrator resources"""
        logger.info("Cleaning up orchestrator...")
        
        # Cancel worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # Stop memory
        await self.short_term_memory.stop()
        
        # Shutdown agents
        for agent in self.agents.values():
            await agent.shutdown()
        
        logger.info("Orchestrator cleanup complete")