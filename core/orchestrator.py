"""
Orchestrator module for Friday AI Assistant.
Coordinates agents, manages tasks, and handles complex request processing.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from enum import Enum
import json
import traceback

from core.models.model_manager import ModelManager
from core.memory.short_term import ShortTermMemory
from core.memory.long_term import LongTermMemory
from core.security.policy_engine import PolicyEngine
from agents.base_agent import BaseAgent, Task, TaskType, TaskStatus


class PlanStatus(Enum):
    """Execution plan status."""
    CREATED = "created"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionPlan:
    """Represents a plan for executing a complex request."""
    def __init__(self, request: str):
        self.id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self.request = request
        self.tasks: List[Task] = []
        self.dependencies: Dict[str, List[str]] = {}  # task_id -> [dependency_ids]
        self.status = PlanStatus.CREATED
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.results: Dict[str, Any] = {}


class Orchestrator:
    """Central orchestrator that coordinates all agents and manages execution."""
    
    def __init__(self, model_manager: ModelManager, short_term_memory: ShortTermMemory,
                 long_term_memory: LongTermMemory, policy_engine: PolicyEngine):
        """Initialize the orchestrator."""
        self.model_manager = model_manager
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.policy_engine = policy_engine
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Agent registry
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}
        
        # Task management
        self.active_tasks: Dict[str, Task] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.execution_plans: Dict[str, ExecutionPlan] = {}
        
        # Worker tasks
        self.workers: List[asyncio.Task] = []
        self.num_workers = 3
        self.is_running = False
        
        self.logger.info("Initialized Orchestrator")
    
    async def initialize(self):
        """Initialize the orchestrator and start worker tasks."""
        self.logger.info("Initializing Orchestrator...")
        
        # Start worker tasks
        self.is_running = True
        for i in range(self.num_workers):
            worker = asyncio.create_task(self._task_worker(i))
            self.workers.append(worker)
        
        self.logger.info(f"Orchestrator initialized with {len(self.agents)} agents")
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator."""
        self.agents[agent.name] = agent
        self.agent_capabilities[agent.name] = agent.capabilities
        self.logger.info(f"Registered agent: {agent.name} with capabilities: {agent.capabilities}")
    
    async def process_request(self, request: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a user request and return results."""
        self.logger.info(f"Processing request: {request}...")
        
        try:
            # Check if this is a simple informational query
            if self._is_simple_query(request):
                # Handle directly without complex task decomposition
                return await self._handle_simple_query(request)
            
            # For complex requests, create execution plan
            plan = await self._create_execution_plan(request, context)
            
            if not plan or not plan.get('tasks'):
                return {
                    'status': 'error',
                    'message': 'Could not create an execution plan for this request.',
                    'suggestion': 'Please try rephrasing your request or use /help for available commands.'
                }
            
            # Create and execute task
            task = await self._create_task_from_plan(plan, request)
            result = await self.execute_task(task, plan)
            
            # Store in history
            await self.long_term_memory.add_interaction(request, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to process request: {str(e)}',
                'details': traceback.format_exc() if self.logger.level <= 10 else None
            }
    
    def _is_simple_query(self, request: str) -> bool:
        """Check if this is a simple informational query."""
        simple_patterns = [
            'what is', 'what are', 'who is', 'who are',
            'tell me about', 'explain', 'describe',
            'list', 'show', 'help with', 'how to',
            'define', 'why', 'when', 'where'
        ]
        request_lower = request.lower().strip()
        
        # Check if it's asking about agents specifically
        if any(word in request_lower for word in ['agent', 'agents']):
            return True
            
        return any(request_lower.startswith(pattern) for pattern in simple_patterns)
    
    async def _handle_simple_query(self, request: str) -> Dict[str, Any]:
        """Handle simple informational queries directly."""
        try:
            # Check if asking about agents
            if 'agent' in request.lower():
                return self._get_agents_info()
            
            # Use the supervisor agent or model directly for simple queries
            supervisor = self.agents.get('OrchestratorAgent')
            if supervisor and supervisor.model_manager:
                response = await supervisor.model_manager.generate(
                    prompt=f"Answer this query concisely and helpfully: {request}",
                    max_tokens=500
                )
            else:
                # Fallback to orchestrator's model
                response = await self.model_manager.generate(
                    prompt=f"Answer this query concisely and helpfully: {request}",
                    max_tokens=500
                )
            
            return {
                'status': 'success',
                'response': response,
                'type': 'simple_query'
            }
        except Exception as e:
            self.logger.error(f"Error handling simple query: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to process query: {str(e)}'
            }
    
    def _get_agents_info(self) -> Dict[str, Any]:
        """Get information about available agents."""
        agents_info = []
        
        for agent_name, agent in self.agents.items():
            agents_info.append({
                'name': agent_name,
                'type': agent.__class__.__name__,
                'capabilities': agent.capabilities,
                'description': self._get_agent_description(agent_name)
            })
        
        response = "Here are the available agents in the Friday system:\n\n"
        
        for info in agents_info:
            response += f"**{info['name']}**\n"
            response += f"- Type: {info['type']}\n"
            response += f"- Capabilities: {', '.join(info['capabilities'])}\n"
            response += f"- Description: {info['description']}\n\n"
        
        return {
            'status': 'success',
            'response': response,
            'agents': agents_info,
            'type': 'agent_info'
        }
    
    def _get_agent_description(self, agent_name: str) -> str:
        """Get description for an agent."""
        descriptions = {
            "ScannerAgent": "Performs security scans, vulnerability assessments, and threat detection",
            "CodingAgent": "Writes code, creates applications, and handles software development tasks",
            "AutomationAgent": "Automates web browsing, form filling, and online tasks",
            "OSControlAgent": "Controls OS functions, manages files, and system settings",
            "OrchestratorAgent": "Coordinates other agents and plans complex multi-step tasks"
        }
        return descriptions.get(agent_name, "Specialized task agent")
    
    async def _create_execution_plan(self, request: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create an execution plan for a complex request."""
        try:
            # Use the supervisor agent to create a plan
            supervisor = self.agents.get('OrchestratorAgent')
            if not supervisor:
                # Fallback to direct model usage
                return await self._create_simple_plan(request)
            
            prompt = f"""As an AI orchestrator, create an execution plan for this request: {request}

Available agents and their capabilities:
{json.dumps(self.agent_capabilities, indent=2)}

Create a plan with:
1. A list of tasks to accomplish the request
2. Which agent should handle each task
3. Any dependencies between tasks

Respond in JSON format:
{{
    "tasks": [
        {{
            "id": "task1",
            "description": "...",
            "agent": "AgentName",
            "dependencies": []
        }}
    ],
    "summary": "Brief summary of the plan"
}}"""

            response = await supervisor.model_manager.generate(
                prompt=prompt,
                max_tokens=800
            )
            
            # Try to parse JSON response
            try:
                # Clean up response if needed
                if '```json' in response:
                    response = response.split('```json')[1].split('```')[0]
                elif '```' in response:
                    response = response.split('```')[1].split('```')[0]
                
                plan = json.loads(response.strip())
                return plan
            except json.JSONDecodeError:
                # If JSON parsing fails, create a simple plan
                return await self._create_simple_plan(request)
                
        except Exception as e:
            self.logger.error(f"Error creating execution plan: {str(e)}")
            return await self._create_simple_plan(request)
    
    async def _create_simple_plan(self, request: str) -> Dict[str, Any]:
        """Create a simple execution plan when complex planning fails."""
        # Determine the best agent based on keywords
        request_lower = request.lower()
        
        agent_name = "OrchestratorAgent"  # Default
        
        if any(word in request_lower for word in ['scan', 'security', 'vulnerability', 'port']):
            agent_name = "ScannerAgent"
        elif any(word in request_lower for word in ['code', 'program', 'script', 'develop']):
            agent_name = "CodingAgent"
        elif any(word in request_lower for word in ['browse', 'web', 'website', 'scrape']):
            agent_name = "AutomationAgent"
        elif any(word in request_lower for word in ['file', 'folder', 'system', 'desktop']):
            agent_name = "OSControlAgent"
        
        return {
            "tasks": [{
                "id": f"task_{uuid.uuid4().hex[:8]}",
                "description": request,
                "agent": agent_name,
                "dependencies": []
            }],
            "summary": f"Execute request using {agent_name}"
        }
    
    async def _create_task_from_plan(self, plan: Dict[str, Any], request: str) -> Task:
        """Create a task from the execution plan."""
        # For now, just create a single task from the first item in the plan
        task_info = plan['tasks'][0] if plan.get('tasks') else {}
        
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        task = Task(
            id=task_id,
            type=TaskType.EXECUTION,
            description=task_info.get('description', request),
            data={
                'original_request': request,
                'agent': task_info.get('agent', 'OrchestratorAgent'),
                'plan': plan
            }
        )
        
        return task
    
    async def execute_task(self, task: Task, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task according to the plan."""
        start_time = datetime.now()
        
        try:
            # Add task to active tasks
            self.active_tasks[task.id] = task
            
            # Get the designated agent
            agent_name = task.data.get('agent', 'OrchestratorAgent')
            agent = self.agents.get(agent_name)
            
            if not agent:
                raise ValueError(f"Agent {agent_name} not found")
            
            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            # Execute the task
            self.logger.info(f"Assigning task {task.id} to {agent_name}")
            result = await agent.execute(task)
            
            # Update task status
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            # Calculate execution time
            execution_time = (task.completed_at - start_time).total_seconds()
            
            # Format response
            return {
                'status': 'success',
                'response': result.get('result', result.get('response', str(result))),
                'task_id': task.id,
                'agent_used': agent_name,
                'execution_time': execution_time,
                'details': result
            }
            
        except Exception as e:
            self.logger.error(f"Task execution failed: {str(e)}")
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            
            return {
                'status': 'error',
                'message': f'Task execution failed: {str(e)}',
                'task_id': task.id,
                'agent_used': agent_name if 'agent_name' in locals() else 'unknown'
            }
        finally:
            # Remove from active tasks
            self.active_tasks.pop(task.id, None)
    
    async def _task_worker(self, worker_id: int):
        """Worker coroutine that processes tasks from the queue."""
        self.logger.info(f"Task worker {worker_id} started")
        
        while self.is_running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                # Process the task
                await self._process_queued_task(task)
                
            except asyncio.TimeoutError:
                # No task available, continue
                continue
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {str(e)}")
                await asyncio.sleep(1)
    
    async def _process_queued_task(self, task_data: Dict[str, Any]):
        """Process a task from the queue."""
        try:
            # Extract task information
            task_id = task_data.get('task_id')
            agent_name = task_data.get('agent')
            
            # Get the agent
            agent = self.agents.get(agent_name)
            if not agent:
                self.logger.error(f"Agent {agent_name} not found for task {task_id}")
                return
            
            # Execute the task
            result = await agent.execute(task_data)
            
            # Store result
            await self.short_term_memory.store(
                key=f"task_result_{task_id}",
                value=result,
                metadata={'type': 'task_result', 'agent': agent_name}
            )
            
        except Exception as e:
            self.logger.error(f"Error processing queued task: {str(e)}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get orchestrator and system status."""
        # Get agent statuses
        agent_statuses = {}
        for name, agent in self.agents.items():
            agent_statuses[name] = await agent.get_status()
        
        # Get memory usage
        memory_stats = await self.short_term_memory.get_stats()
        
        # Get model information
        models_available = len(self.model_manager.available_models)
        
        return {
            'is_running': self.is_running,
            'agents': agent_statuses,
            'active_tasks': len(self.active_tasks),
            'queued_tasks': self.task_queue.qsize(),
            'workers': len(self.workers),
            'memory_usage': memory_stats.get('size_mb', 0),
            'models_available': models_available,
            'uptime': (datetime.now() - self.short_term_memory.created_at).total_seconds()
        }
    
    async def cleanup(self):
        """Cleanup orchestrator resources."""
        self.logger.info("Cleaning up orchestrator...")
        
        # Stop accepting new tasks
        self.is_running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Cleanup agents
        for agent in self.agents.values():
            await agent.shutdown()
        
        self.logger.info("Orchestrator cleanup complete")