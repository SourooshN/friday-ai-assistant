"""
Policy Engine for Friday AI Assistant
Handles security policies, guardrails, and safety checks
"""

import re
import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from loguru import logger

from core.common_types import Task


class PolicyLevel(Enum):
    """Security policy levels"""
    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class PolicyCheckResult:
    """Result of a policy check"""
    allowed: bool
    level: PolicyLevel
    risk: RiskLevel
    reason: Optional[str] = None
    suggestions: Optional[List[str]] = None
    require_confirmation: bool = False


@dataclass
class SecurityPolicy:
    """Individual security policy"""
    name: str
    description: str
    pattern: Optional[str] = None  # Regex pattern
    keywords: Optional[List[str]] = None
    level: PolicyLevel = PolicyLevel.CONFIRM
    risk: RiskLevel = RiskLevel.MEDIUM
    applies_to: Optional[List[str]] = None  # Task types or agent names


class PolicyEngine:
    """Security and safety policy enforcement"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize policy engine"""
        self.config = config
        self.enabled = config.get('sandbox_enabled', True)
        self.require_confirmation = config.get('require_confirmation', [])
        
        # Guardrail settings
        self.guardrails = config.get('guardrails', {})
        self.check_ethical = self.guardrails.get('check_ethical', True)
        self.check_legal = self.guardrails.get('check_legal', True)
        self.check_harmful = self.guardrails.get('check_harmful', True)
        
        # Policies
        self.policies: List[SecurityPolicy] = []
        self.blocked_patterns: List[re.Pattern] = []
        self.allowed_paths: Set[Path] = set()
        self.blocked_commands: Set[str] = set()
        
        # Initialize default policies
        self._init_default_policies()
        
        logger.info("Initialized PolicyEngine")

    def _init_default_policies(self):
        """Initialize default security policies"""
        
        # File system policies
        self.policies.extend([
            SecurityPolicy(
                name="system_file_protection",
                description="Protect system files",
                pattern=r"(C:\\Windows|C:\\Program Files|/etc|/usr|/bin)",
                keywords=None,
                level=PolicyLevel.DENY,
                risk=RiskLevel.CRITICAL,
                applies_to=["file_operations", "system_control"]
            ),
            SecurityPolicy(
                name="delete_protection",
                description="Confirm file deletions",
                keywords=["delete", "remove", "rm", "del", "erase"],
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.HIGH,
                applies_to=["file_operations"]
            ),
            SecurityPolicy(
                name="format_protection",
                description="Block disk formatting",
                keywords=["format", "fdisk", "diskpart"],
                level=PolicyLevel.DENY,
                risk=RiskLevel.CRITICAL,
                applies_to=["system_control"]
            )
        ])
        
        # Network policies
        self.policies.extend([
            SecurityPolicy(
                name="network_scan_control",
                description="Control network scanning",
                keywords=["nmap", "scan", "port scan", "vulnerability scan"],
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.MEDIUM,
                applies_to=["cybersecurity", "network"]
            ),
            SecurityPolicy(
                name="exploit_control",
                description="Control exploit usage",
                keywords=["exploit", "metasploit", "payload", "backdoor"],
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.HIGH,
                applies_to=["cybersecurity"]
            )
        ])
        
        # Code execution policies
        self.policies.extend([
            SecurityPolicy(
                name="code_execution_control",
                description="Control code execution",
                keywords=["exec", "eval", "subprocess", "os.system"],
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.HIGH,
                applies_to=["coding", "system_control"]
            ),
            SecurityPolicy(
                name="malware_protection",
                description="Block malware patterns",
                keywords=["virus", "trojan", "ransomware", "keylogger"],
                level=PolicyLevel.DENY,
                risk=RiskLevel.CRITICAL,
                applies_to=["all"]
            )
        ])
        
        # Load blocked patterns from config
        if 'blocked_patterns' in self.config.get('system_control', {}):
            for pattern in self.config['system_control']['blocked_patterns']:
                self.blocked_patterns.append(re.compile(pattern, re.IGNORECASE))
        
        # Load allowed paths
        if 'allowed_paths' in self.config.get('file_operations', {}):
            for path in self.config['file_operations']['allowed_paths']:
                self.allowed_paths.add(Path(path).resolve())
        
        # Load blocked commands
        if 'blocked_commands' in self.config.get('system_control', {}):
            self.blocked_commands.update(self.config['system_control']['blocked_commands'])

    async def check_task(self, task: Task) -> PolicyCheckResult:
        """Check if a task complies with security policies"""
        
        if not self.enabled:
            return PolicyCheckResult(
                allowed=True,
                level=PolicyLevel.ALLOW,
                risk=RiskLevel.LOW,
                reason="Policy engine disabled"
            )
        
        # Check for blocked patterns
        task_text = f"{task.type} {task.description} {str(task.parameters)}"
        
        for pattern in self.blocked_patterns:
            if pattern.search(task_text):
                return PolicyCheckResult(
                    allowed=False,
                    level=PolicyLevel.DENY,
                    risk=RiskLevel.CRITICAL,
                    reason=f"Blocked pattern detected: {pattern.pattern}"
                )
        
        # Check policies
        worst_level = PolicyLevel.ALLOW
        highest_risk = RiskLevel.LOW
        reasons = []
        require_confirmation = False
        
        for policy in self.policies:
            if self._policy_applies(policy, task):
                if self._matches_policy(policy, task_text):
                    # Update worst level
                    if policy.level == PolicyLevel.DENY:
                        return PolicyCheckResult(
                            allowed=False,
                            level=PolicyLevel.DENY,
                            risk=policy.risk,
                            reason=f"Policy '{policy.name}': {policy.description}"
                        )
                    elif policy.level == PolicyLevel.CONFIRM:
                        worst_level = PolicyLevel.CONFIRM
                        require_confirmation = True
                    
                    # Update highest risk
                    if policy.risk.value > highest_risk.value:
                        highest_risk = policy.risk
                    
                    reasons.append(f"{policy.name}: {policy.description}")
        
        # Check if task type requires confirmation
        if task.type in self.require_confirmation:
            require_confirmation = True
            worst_level = PolicyLevel.CONFIRM
            reasons.append(f"Task type '{task.type}' requires confirmation")
        
        # Additional checks
        if self.check_ethical:
            ethical_check = await self._check_ethical_compliance(task)
            if not ethical_check[0]:
                return PolicyCheckResult(
                    allowed=False,
                    level=PolicyLevel.DENY,
                    risk=RiskLevel.HIGH,
                    reason=ethical_check[1]
                )
        
        return PolicyCheckResult(
            allowed=worst_level != PolicyLevel.DENY,
            level=worst_level,
            risk=highest_risk,
            reason="; ".join(reasons) if reasons else None,
            require_confirmation=require_confirmation
        )

    async def check_file_operation(self, path: Path, operation: str) -> PolicyCheckResult:
        """Check if a file operation is allowed"""
        
        path = path.resolve()
        
        # Check if path is in allowed directories
        allowed = False
        for allowed_path in self.allowed_paths:
            try:
                path.relative_to(allowed_path)
                allowed = True
                break
            except ValueError:
                continue
        
        if not allowed:
            return PolicyCheckResult(
                allowed=False,
                level=PolicyLevel.DENY,
                risk=RiskLevel.HIGH,
                reason=f"Path '{path}' is not in allowed directories"
            )
        
        # Check operation type
        if operation in ["delete", "remove"]:
            return PolicyCheckResult(
                allowed=True,
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.MEDIUM,
                reason="File deletion requires confirmation",
                require_confirmation=True
            )
        
        return PolicyCheckResult(
            allowed=True,
            level=PolicyLevel.ALLOW,
            risk=RiskLevel.LOW
        )

    async def check_command(self, command: str) -> PolicyCheckResult:
        """Check if a system command is allowed"""
        
        # Split command to get base command
        parts = command.strip().split()
        if not parts:
            return PolicyCheckResult(
                allowed=False,
                level=PolicyLevel.DENY,
                risk=RiskLevel.MEDIUM,
                reason="Empty command"
            )
        
        base_command = parts[0].lower()
        
        # Check against blocked commands
        if base_command in self.blocked_commands:
            return PolicyCheckResult(
                allowed=False,
                level=PolicyLevel.DENY,
                risk=RiskLevel.HIGH,
                reason=f"Command '{base_command}' is blocked"
            )
        
        # Check for dangerous patterns
        dangerous_patterns = [
            r"rm\s+-rf\s+/",
            r"format\s+[a-zA-Z]:",
            r"del\s+/f\s+/s\s+/q",
            r":(){ :|:& };:",  # Fork bomb
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return PolicyCheckResult(
                    allowed=False,
                    level=PolicyLevel.DENY,
                    risk=RiskLevel.CRITICAL,
                    reason="Dangerous command pattern detected"
                )
        
        # Commands that need confirmation
        confirm_commands = ["shutdown", "reboot", "kill", "taskkill", "stop-service"]
        if base_command in confirm_commands:
            return PolicyCheckResult(
                allowed=True,
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.MEDIUM,
                reason=f"Command '{base_command}' requires confirmation",
                require_confirmation=True
            )
        
        return PolicyCheckResult(
            allowed=True,
            level=PolicyLevel.ALLOW,
            risk=RiskLevel.LOW
        )

    async def check_network_operation(
        self,
        operation: str,
        target: str,
        port: Optional[int] = None
    ) -> PolicyCheckResult:
        """Check if a network operation is allowed"""
        
        # Check for localhost/private network only
        private_patterns = [
            r"^127\.",
            r"^10\.",
            r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
            r"^192\.168\.",
            r"^localhost$",
            r"^local$"
        ]
        
        is_private = any(re.match(pattern, target, re.IGNORECASE) for pattern in private_patterns)
        
        if operation in ["scan", "exploit", "attack"]:
            if not is_private:
                return PolicyCheckResult(
                    allowed=False,
                    level=PolicyLevel.DENY,
                    risk=RiskLevel.CRITICAL,
                    reason="Security operations only allowed on private networks"
                )
            
            return PolicyCheckResult(
                allowed=True,
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.HIGH,
                reason=f"Security operation '{operation}' requires confirmation",
                require_confirmation=True
            )
        
        return PolicyCheckResult(
            allowed=True,
            level=PolicyLevel.ALLOW,
            risk=RiskLevel.LOW
        )

    def add_policy(self, policy: SecurityPolicy):
        """Add a custom security policy"""
        self.policies.append(policy)
        logger.info(f"Added policy: {policy.name}")

    def remove_policy(self, policy_name: str) -> bool:
        """Remove a policy by name"""
        self.policies = [p for p in self.policies if p.name != policy_name]
        logger.info(f"Removed policy: {policy_name}")
        return True

    def get_policies(self) -> List[SecurityPolicy]:
        """Get all active policies"""
        return self.policies.copy()

    # Private methods
    
    def _policy_applies(self, policy: SecurityPolicy, task: Task) -> bool:
        """Check if a policy applies to a task"""
        if not policy.applies_to or "all" in policy.applies_to:
            return True
        
        return task.type in policy.applies_to

    def _matches_policy(self, policy: SecurityPolicy, text: str) -> bool:
        """Check if text matches policy criteria"""
        # Check pattern
        if policy.pattern:
            if re.search(policy.pattern, text, re.IGNORECASE):
                return True
        
        # Check keywords
        if policy.keywords:
            text_lower = text.lower()
            for keyword in policy.keywords:
                if keyword.lower() in text_lower:
                    return True
        
        return False

    async def _check_ethical_compliance(self, task: Task) -> Tuple[bool, Optional[str]]:
        """Check ethical compliance of a task"""
        # Basic ethical checks
        unethical_keywords = [
            "harm", "hurt", "damage", "illegal", "crack", "pirate",
            "steal", "fraud", "scam", "phishing", "ddos"
        ]
        
        task_text = f"{task.type} {task.description}".lower()
        
        for keyword in unethical_keywords:
            if keyword in task_text:
                return False, f"Task contains potentially unethical keyword: {keyword}"
        
        return True, None

    async def get_risk_assessment(self, task: Task) -> RiskLevel:
        """Get risk level for a task"""
        check_result = await self.check_task(task)
        return check_result.risk

    def export_policies(self) -> Dict[str, Any]:
        """Export policies to dictionary"""
        return {
            'policies': [
                {
                    'name': p.name,
                    'description': p.description,
                    'pattern': p.pattern,
                    'keywords': p.keywords,
                    'level': p.level.value,
                    'risk': p.risk.name.lower(),
                    'applies_to': p.applies_to
                }
                for p in self.policies
            ],
            'blocked_patterns': [p.pattern for p in self.blocked_patterns],
            'allowed_paths': [str(p) for p in self.allowed_paths],
            'blocked_commands': list(self.blocked_commands)
        }

    def import_policies(self, data: Dict[str, Any]):
        """Import policies from dictionary"""
        # Import policies
        for policy_data in data.get('policies', []):
            # Convert risk string to enum
            risk_str = policy_data['risk']
            risk_map = {'low': RiskLevel.LOW, 'medium': RiskLevel.MEDIUM, 
                       'high': RiskLevel.HIGH, 'critical': RiskLevel.CRITICAL}
            
            policy = SecurityPolicy(
                name=policy_data['name'],
                description=policy_data['description'],
                pattern=policy_data.get('pattern'),
                keywords=policy_data.get('keywords'),
                level=PolicyLevel(policy_data['level']),
                risk=risk_map.get(risk_str, RiskLevel.MEDIUM),
                applies_to=policy_data.get('applies_to')
            )
            self.add_policy(policy)
        
        # Import blocked patterns
        for pattern in data.get('blocked_patterns', []):
            self.blocked_patterns.append(re.compile(pattern, re.IGNORECASE))
        
        # Import allowed paths
        for path in data.get('allowed_paths', []):
            self.allowed_paths.add(Path(path).resolve())
        
        # Import blocked commands
        self.blocked_commands.update(data.get('blocked_commands', []))


class PolicyEngine:
    """Security and safety policy enforcement"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize policy engine"""
        self.config = config
        self.enabled = config.get('sandbox_enabled', True)
        self.require_confirmation = config.get('require_confirmation', [])
        
        # Guardrail settings
        self.guardrails = config.get('guardrails', {})
        self.check_ethical = self.guardrails.get('check_ethical', True)
        self.check_legal = self.guardrails.get('check_legal', True)
        self.check_harmful = self.guardrails.get('check_harmful', True)
        
        # Policies
        self.policies: List[SecurityPolicy] = []
        self.blocked_patterns: List[re.Pattern] = []
        self.allowed_paths: Set[Path] = set()
        self.blocked_commands: Set[str] = set()
        
        # Initialize default policies
        self._init_default_policies()
        
        logger.info("Initialized PolicyEngine")

    def _init_default_policies(self):
        """Initialize default security policies"""
        
        # File system policies
        self.policies.extend([
            SecurityPolicy(
                name="system_file_protection",
                description="Protect system files",
                pattern=r"(C:\\Windows|C:\\Program Files|/etc|/usr|/bin)",
                level=PolicyLevel.DENY,
                risk=RiskLevel.CRITICAL,
                applies_to=["file_operations", "system_control"]
            ),
            SecurityPolicy(
                name="delete_protection",
                description="Confirm file deletions",
                keywords=["delete", "remove", "rm", "del", "erase"],
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.HIGH,
                applies_to=["file_operations"]
            ),
            SecurityPolicy(
                name="format_protection",
                description="Block disk formatting",
                keywords=["format", "fdisk", "diskpart"],
                level=PolicyLevel.DENY,
                risk=RiskLevel.CRITICAL,
                applies_to=["system_control"]
            )
        ])
        
        # Network policies
        self.policies.extend([
            SecurityPolicy(
                name="network_scan_control",
                description="Control network scanning",
                keywords=["nmap", "scan", "port scan", "vulnerability scan"],
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.MEDIUM,
                applies_to=["cybersecurity", "network"]
            ),
            SecurityPolicy(
                name="exploit_control",
                description="Control exploit usage",
                keywords=["exploit", "metasploit", "payload", "backdoor"],
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.HIGH,
                applies_to=["cybersecurity"]
            )
        ])
        
        # Code execution policies
        self.policies.extend([
            SecurityPolicy(
                name="code_execution_control",
                description="Control code execution",
                keywords=["exec", "eval", "subprocess", "os.system"],
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.HIGH,
                applies_to=["coding", "system_control"]
            ),
            SecurityPolicy(
                name="malware_protection",
                description="Block malware patterns",
                keywords=["virus", "trojan", "ransomware", "keylogger"],
                level=PolicyLevel.DENY,
                risk=RiskLevel.CRITICAL,
                applies_to=["all"]
            )
        ])
        
        # Load blocked patterns from config
        if 'blocked_patterns' in self.config.get('system_control', {}):
            for pattern in self.config['system_control']['blocked_patterns']:
                self.blocked_patterns.append(re.compile(pattern, re.IGNORECASE))
        
        # Load allowed paths
        if 'allowed_paths' in self.config.get('file_operations', {}):
            for path in self.config['file_operations']['allowed_paths']:
                self.allowed_paths.add(Path(path).resolve())
        
        # Load blocked commands
        if 'blocked_commands' in self.config.get('system_control', {}):
            self.blocked_commands.update(self.config['system_control']['blocked_commands'])

    async def check_task(self, task: Task) -> PolicyCheckResult:
        """Check if a task complies with security policies"""
        
        if not self.enabled:
            return PolicyCheckResult(
                allowed=True,
                level=PolicyLevel.ALLOW,
                risk=RiskLevel.LOW,
                reason="Policy engine disabled"
            )
        
        # Check for blocked patterns
        task_text = f"{task.type} {task.description} {str(task.parameters)}"
        
        for pattern in self.blocked_patterns:
            if pattern.search(task_text):
                return PolicyCheckResult(
                    allowed=False,
                    level=PolicyLevel.DENY,
                    risk=RiskLevel.CRITICAL,
                    reason=f"Blocked pattern detected: {pattern.pattern}"
                )
        
        # Check policies
        worst_level = PolicyLevel.ALLOW
        highest_risk = RiskLevel.LOW
        reasons = []
        require_confirmation = False
        
        for policy in self.policies:
            if self._policy_applies(policy, task):
                if self._matches_policy(policy, task_text):
                    # Update worst level
                    if policy.level == PolicyLevel.DENY:
                        return PolicyCheckResult(
                            allowed=False,
                            level=PolicyLevel.DENY,
                            risk=policy.risk,
                            reason=f"Policy '{policy.name}': {policy.description}"
                        )
                    elif policy.level == PolicyLevel.CONFIRM:
                        worst_level = PolicyLevel.CONFIRM
                        require_confirmation = True
                    
                    # Update highest risk
                    if policy.risk.value > highest_risk.value:
                        highest_risk = policy.risk
                    
                    reasons.append(f"{policy.name}: {policy.description}")
        
        # Check if task type requires confirmation
        if task.type in self.require_confirmation:
            require_confirmation = True
            worst_level = PolicyLevel.CONFIRM
            reasons.append(f"Task type '{task.type}' requires confirmation")
        
        # Additional checks
        if self.check_ethical:
            ethical_check = await self._check_ethical_compliance(task)
            if not ethical_check[0]:
                return PolicyCheckResult(
                    allowed=False,
                    level=PolicyLevel.DENY,
                    risk=RiskLevel.HIGH,
                    reason=ethical_check[1]
                )
        
        return PolicyCheckResult(
            allowed=worst_level != PolicyLevel.DENY,
            level=worst_level,
            risk=highest_risk,
            reason="; ".join(reasons) if reasons else None,
            require_confirmation=require_confirmation
        )

    async def check_file_operation(self, path: Path, operation: str) -> PolicyCheckResult:
        """Check if a file operation is allowed"""
        
        path = path.resolve()
        
        # Check if path is in allowed directories
        allowed = False
        for allowed_path in self.allowed_paths:
            try:
                path.relative_to(allowed_path)
                allowed = True
                break
            except ValueError:
                continue
        
        if not allowed:
            return PolicyCheckResult(
                allowed=False,
                level=PolicyLevel.DENY,
                risk=RiskLevel.HIGH,
                reason=f"Path '{path}' is not in allowed directories"
            )
        
        # Check operation type
        if operation in ["delete", "remove"]:
            return PolicyCheckResult(
                allowed=True,
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.MEDIUM,
                reason="File deletion requires confirmation",
                require_confirmation=True
            )
        
        return PolicyCheckResult(
            allowed=True,
            level=PolicyLevel.ALLOW,
            risk=RiskLevel.LOW
        )

    async def check_command(self, command: str) -> PolicyCheckResult:
        """Check if a system command is allowed"""
        
        # Split command to get base command
        parts = command.strip().split()
        if not parts:
            return PolicyCheckResult(
                allowed=False,
                level=PolicyLevel.DENY,
                risk=RiskLevel.MEDIUM,
                reason="Empty command"
            )
        
        base_command = parts[0].lower()
        
        # Check against blocked commands
        if base_command in self.blocked_commands:
            return PolicyCheckResult(
                allowed=False,
                level=PolicyLevel.DENY,
                risk=RiskLevel.HIGH,
                reason=f"Command '{base_command}' is blocked"
            )
        
        # Check for dangerous patterns
        dangerous_patterns = [
            r"rm\s+-rf\s+/",
            r"format\s+[a-zA-Z]:",
            r"del\s+/f\s+/s\s+/q",
            r":(){ :|:& };:",  # Fork bomb
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return PolicyCheckResult(
                    allowed=False,
                    level=PolicyLevel.DENY,
                    risk=RiskLevel.CRITICAL,
                    reason="Dangerous command pattern detected"
                )
        
        # Commands that need confirmation
        confirm_commands = ["shutdown", "reboot", "kill", "taskkill", "stop-service"]
        if base_command in confirm_commands:
            return PolicyCheckResult(
                allowed=True,
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.MEDIUM,
                reason=f"Command '{base_command}' requires confirmation",
                require_confirmation=True
            )
        
        return PolicyCheckResult(
            allowed=True,
            level=PolicyLevel.ALLOW,
            risk=RiskLevel.LOW
        )

    async def check_network_operation(
        self,
        operation: str,
        target: str,
        port: Optional[int] = None
    ) -> PolicyCheckResult:
        """Check if a network operation is allowed"""
        
        # Check for localhost/private network only
        private_patterns = [
            r"^127\.",
            r"^10\.",
            r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
            r"^192\.168\.",
            r"^localhost$",
            r"^local$"
        ]
        
        is_private = any(re.match(pattern, target, re.IGNORECASE) for pattern in private_patterns)
        
        if operation in ["scan", "exploit", "attack"]:
            if not is_private:
                return PolicyCheckResult(
                    allowed=False,
                    level=PolicyLevel.DENY,
                    risk=RiskLevel.CRITICAL,
                    reason="Security operations only allowed on private networks"
                )
            
            return PolicyCheckResult(
                allowed=True,
                level=PolicyLevel.CONFIRM,
                risk=RiskLevel.HIGH,
                reason=f"Security operation '{operation}' requires confirmation",
                require_confirmation=True
            )
        
        return PolicyCheckResult(
            allowed=True,
            level=PolicyLevel.ALLOW,
            risk=RiskLevel.LOW
        )

    def add_policy(self, policy: SecurityPolicy):
        """Add a custom security policy"""
        self.policies.append(policy)
        logger.info(f"Added policy: {policy.name}")

    def remove_policy(self, policy_name: str) -> bool:
        """Remove a policy by name"""
        self.policies = [p for p in self.policies if p.name != policy_name]
        logger.info(f"Removed policy: {policy_name}")
        return True

    def get_policies(self) -> List[SecurityPolicy]:
        """Get all active policies"""
        return self.policies.copy()

    # Private methods
    
    def _policy_applies(self, policy: SecurityPolicy, task: Task) -> bool:
        """Check if a policy applies to a task"""
        if not policy.applies_to or "all" in policy.applies_to:
            return True
        
        return task.type in policy.applies_to

    def _matches_policy(self, policy: SecurityPolicy, text: str) -> bool:
        """Check if text matches policy criteria"""
        # Check pattern
        if policy.pattern:
            if re.search(policy.pattern, text, re.IGNORECASE):
                return True
        
        # Check keywords
        if policy.keywords:
            text_lower = text.lower()
            for keyword in policy.keywords:
                if keyword.lower() in text_lower:
                    return True
        
        return False

    async def _check_ethical_compliance(self, task: Task) -> Tuple[bool, Optional[str]]:
        """Check ethical compliance of a task"""
        # Basic ethical checks
        unethical_keywords = [
            "harm", "hurt", "damage", "illegal", "crack", "pirate",
            "steal", "fraud", "scam", "phishing", "ddos"
        ]
        
        task_text = f"{task.type} {task.description}".lower()
        
        for keyword in unethical_keywords:
            if keyword in task_text:
                return False, f"Task contains potentially unethical keyword: {keyword}"
        
        return True, None

    def get_risk_assessment(self, task: Task) -> RiskLevel:
        """Get risk level for a task"""
        check_result = asyncio.run(self.check_task(task))
        return check_result.risk

    def export_policies(self) -> Dict[str, Any]:
        """Export policies to dictionary"""
        return {
            'policies': [
                {
                    'name': p.name,
                    'description': p.description,
                    'pattern': p.pattern,
                    'keywords': p.keywords,
                    'level': p.level.value,
                    'risk': p.risk.value,
                    'applies_to': p.applies_to
                }
                for p in self.policies
            ],
            'blocked_patterns': [p.pattern for p in self.blocked_patterns],
            'allowed_paths': [str(p) for p in self.allowed_paths],
            'blocked_commands': list(self.blocked_commands)
        }

    def import_policies(self, data: Dict[str, Any]):
        """Import policies from dictionary"""
        # Import policies
        for policy_data in data.get('policies', []):
            policy = SecurityPolicy(
                name=policy_data['name'],
                description=policy_data['description'],
                pattern=policy_data.get('pattern'),
                keywords=policy_data.get('keywords'),
                level=PolicyLevel(policy_data['level']),
                risk=RiskLevel(policy_data['risk']),
                applies_to=policy_data.get('applies_to')
            )
            self.add_policy(policy)
        
        # Import blocked patterns
        for pattern in data.get('blocked_patterns', []):
            self.blocked_patterns.append(re.compile(pattern, re.IGNORECASE))
        
        # Import allowed paths
        for path in data.get('allowed_paths', []):
            self.allowed_paths.add(Path(path).resolve())
        
        # Import blocked commands
        self.blocked_commands.update(data.get('blocked_commands', []))