"""
Friday Policy Engine

Manages security policies and access controls.
"""

from typing import Any, Dict, List

from ..logging import get_logger


class PolicyEngine:
    """
    Manages security policies and access controls for Friday.

    This is a skeleton implementation for Milestone 1.
    """

    def __init__(self, security_config: Dict[str, Any]):
        self.config = security_config
        self.logger = get_logger()

        # Default policies
        self._policies = {
            "deny_by_default": True,
            "require_chain_of_trust": self.config.get("chain_of_trust", True),
            "sandbox_all": self.config.get("sandbox_all", True)
        }

    def check_permission(self, action: str, resource: str, context: Dict[str, Any] = None) -> bool:
        """
        Check if an action is permitted on a resource.

        Args:
            action: Action to check (e.g., "read", "write", "execute")
            resource: Resource being accessed
            context: Additional context for the check

        Returns:
            True if permitted, False otherwise
        """
        context = context or {}

        # Check security level requirements
        security_level = context.get("security_level", "safe")
        plugin_id = context.get("plugin_id", "unknown")
        tool_name = context.get("tool_name", action)

        self.logger.debug(f"Policy check: {action} on {resource} (security_level: {security_level}, plugin: {plugin_id})")

        # Handle privileged operations
        if security_level == "privileged":
            # Log privileged access attempt
            self.logger.audit(
                f"Privileged operation attempted: {tool_name}",
                action="privileged_access_check",
                plugin_id=plugin_id,
                tool_name=tool_name,
                resource=resource,
                security_level=security_level
            )

            # Check if privileged operations are allowed in this environment
            if not self.config.get("allow_privileged", False):
                self.logger.warning(f"Privileged operation denied: {tool_name} (environment restriction)")
                return False

            # Additional checks for system-critical operations
            if any(dangerous in tool_name.lower() for dangerous in ["shutdown", "restart", "kill"]):
                # In production, might require additional confirmation
                self.logger.audit(
                    f"System-critical operation: {tool_name}",
                    action="system_critical_operation",
                    plugin_id=plugin_id,
                    tool_name=tool_name,
                    approved=True
                )

        # Log successful policy check
        self.logger.audit(
            f"Policy check passed: {tool_name}",
            action="policy_check_passed",
            plugin_id=plugin_id,
            tool_name=tool_name,
            resource=resource,
            security_level=security_level
        )

        return True

    def add_policy(self, name: str, policy: Dict[str, Any]):
        """Add a new policy."""
        self._policies[name] = policy
        self.logger.audit(f"Policy added: {name}", action="policy_add", policy_name=name)

    def remove_policy(self, name: str):
        """Remove a policy."""
        if name in self._policies:
            del self._policies[name]
            self.logger.audit(f"Policy removed: {name}", action="policy_remove", policy_name=name)

    def get_policies(self) -> Dict[str, Any]:
        """Get all policies."""
        return self._policies.copy()