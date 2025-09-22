"""
Integration tests for Milestone 6: Self-Modification Pipeline
Tests the AI self-improvement capabilities with comprehensive safety controls.
"""
import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime
import sys

# Import our self-modification plugins
sys.path.append(str(Path(__file__).parent.parent.parent))

# Initialize logging for tests
from core.logging import initialize_logger
config = {
    "path": "./data/logs",
    "level": "INFO",
    "console": False,
    "file": False,
    "format": "structured"
}
initialize_logger(config)

from plugins.available.self_modification import SelfModificationPlugin
from plugins.available.deployment_automation import DeploymentAutomationPlugin
from scripts.safety.rollback_manager import RollbackManager


class TestMilestone6SelfModification:
    """Test suite for Milestone 6 self-modification pipeline features."""

    @pytest.fixture
    def self_modification_plugin(self):
        """Create self-modification plugin instance."""
        return SelfModificationPlugin()

    @pytest.fixture
    def deployment_plugin(self):
        """Create deployment automation plugin instance."""
        return DeploymentAutomationPlugin()

    @pytest.fixture
    def rollback_manager(self):
        """Create rollback manager instance."""
        return RollbackManager()

    @pytest.mark.asyncio
    async def test_self_modification_plugin_initialization(self, self_modification_plugin):
        """Test self-modification plugin initializes correctly."""
        result = await self_modification_plugin.initialize()
        assert result is True
        assert self_modification_plugin.name == "self_modification"
        assert self_modification_plugin.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_deployment_plugin_initialization(self, deployment_plugin):
        """Test deployment automation plugin initializes correctly."""
        result = await deployment_plugin.initialize()
        assert result is True
        assert deployment_plugin.name == "deployment_automation"
        assert deployment_plugin.version == "1.0.0"

    def test_rollback_manager_initialization(self, rollback_manager):
        """Test rollback manager initializes correctly."""
        status = rollback_manager.get_system_status()
        assert status["success"] is True
        assert "system_hash" in status
        assert "system_checks" in status

    @pytest.mark.asyncio
    async def test_modification_proposal_system(self, self_modification_plugin):
        """Test code modification proposal system."""
        # Test proposing a modification
        proposal_result = self_modification_plugin.propose_modification(
            modification_type="enhancement",
            description="Add enhanced greeting functionality",
            files_to_modify=["plugins/available/os_hello.py"],
            proposed_changes={"say_hello": "Add timestamp to greeting"},
            justification="Improve user experience"
        )

        assert proposal_result["success"] is True
        assert "proposal_id" in proposal_result
        assert "proposal" in proposal_result

        # Verify proposal structure
        proposal = proposal_result["proposal"]
        assert "impact_analysis" in proposal
        assert "safety_validation" in proposal

        # Check impact analysis
        impact_analysis = proposal["impact_analysis"]
        assert "risk_level" in impact_analysis
        assert impact_analysis["risk_level"] in ["low", "medium", "high", "critical"]

        # Check safety validation
        safety_validation = proposal["safety_validation"]
        assert "safe" in safety_validation
        assert isinstance(safety_validation["safe"], bool)

    @pytest.mark.asyncio
    async def test_proposal_validation(self, self_modification_plugin):
        """Test proposal validation system."""
        # Create a test proposal first
        test_modification = {
            "type": "bugfix",
            "target_file": "core/kernel.py",
            "description": "Fix minor logging issue",
            "changes": [{"operation": "modify_line", "line": 100, "new_content": "logger.info('test')"}],
            "rationale": "Improve logging"
        }

        proposal_result = await self_modification_plugin.propose_modification(test_modification)
        assert proposal_result["success"] is True

        proposal_id = proposal_result["proposal_id"]

        # Test validation
        validation_result = await self_modification_plugin.validate_proposal(proposal_id)

        assert validation_result["success"] is True
        assert "valid" in validation_result
        assert "syntax_valid" in validation_result
        assert "dependencies_ok" in validation_result
        assert "security_clear" in validation_result

    @pytest.mark.asyncio
    async def test_adversarial_testing_framework(self, self_modification_plugin):
        """Test adversarial testing framework."""
        test_proposal_id = "test_adversarial_" + str(int(datetime.now().timestamp()))

        adversarial_result = await self_modification_plugin.run_adversarial_testing(test_proposal_id)

        assert adversarial_result["success"] is True
        assert "test_suite" in adversarial_result
        assert "tests_run" in adversarial_result
        assert "status" in adversarial_result
        assert "test_scenarios" in adversarial_result

        # Verify test scenarios structure
        test_scenarios = adversarial_result["test_scenarios"]
        assert isinstance(test_scenarios, list)

        if test_scenarios:
            scenario = test_scenarios[0]
            assert "name" in scenario
            assert "result" in scenario
            assert scenario["result"] in ["passed", "failed", "error"]

    @pytest.mark.asyncio
    async def test_human_approval_gates(self, self_modification_plugin):
        """Test human approval gate system."""
        # Test approval request
        approval_request = {
            "modification_id": "test_mod_approval",
            "type": "code_change",
            "risk_level": "medium",
            "description": "Test modification for approval",
            "requested_by": "test_system"
        }

        approval_result = await self_modification_plugin.request_human_approval(approval_request)

        assert approval_result["success"] is True
        assert "request_id" in approval_result
        assert "status" in approval_result
        assert approval_result["status"] in ["pending", "approved", "rejected", "auto_approved"]

        # Test listing pending approvals
        pending_result = await self_modification_plugin.list_pending_approvals()

        assert pending_result["success"] is True
        assert "total_pending" in pending_result
        assert "pending_requests" in pending_result

    @pytest.mark.asyncio
    async def test_deployment_automation(self, deployment_plugin):
        """Test deployment automation system."""
        # Test staging deployment
        staging_config = {
            "environment": "staging",
            "changes": ["test_change_1", "test_change_2"],
            "rollback_enabled": True,
            "health_checks": True
        }

        deploy_result = await deployment_plugin.deploy_to_staging(staging_config)

        assert deploy_result["success"] is True
        assert "deployment_id" in deploy_result
        assert "status" in deploy_result
        assert deploy_result["status"] in ["deployed", "deploying", "failed"]

        # Test health monitoring
        deployment_id = deploy_result["deployment_id"]
        health_result = await deployment_plugin.monitor_deployment_health(deployment_id)

        assert health_result["success"] is True
        assert "overall_health" in health_result
        assert "checks_passing" in health_result

    @pytest.mark.asyncio
    async def test_backup_and_restore(self, deployment_plugin):
        """Test backup and restore functionality."""
        # Test backup creation
        backup_result = await deployment_plugin.create_backup()

        assert backup_result["success"] is True
        assert "backup_id" in backup_result
        assert "size_mb" in backup_result

        # Test listing backups
        list_result = await deployment_plugin.list_backups()

        assert list_result["success"] is True
        assert "backups" in list_result
        assert isinstance(list_result["backups"], list)

    def test_rollback_point_creation(self, rollback_manager):
        """Test rollback point creation and management."""
        # Create rollback point
        result = rollback_manager.create_rollback_point(
            "Test rollback point",
            "test"
        )

        assert result["success"] is True
        assert "rollback_id" in result
        assert "backup_location" in result
        assert "files_backed_up" in result

        # List rollback points
        list_result = rollback_manager.list_rollback_points()

        assert list_result["success"] is True
        assert "rollback_points" in list_result
        assert "total_count" in list_result

    def test_emergency_stop_system(self, rollback_manager):
        """Test emergency stop system."""
        # Create emergency stop
        stop_result = rollback_manager.create_emergency_stop("Testing emergency stop")

        assert stop_result["success"] is True
        assert "emergency_stop_file" in stop_result

        # Check system status with emergency stop
        status = rollback_manager.get_system_status()
        assert status["emergency_stop_active"] is True

        # Clear emergency stop
        clear_result = rollback_manager.clear_emergency_stop("CONFIRM_CLEAR_EMERGENCY_STOP")

        assert clear_result["success"] is True

        # Verify emergency stop is cleared
        status_after = rollback_manager.get_system_status()
        assert status_after["emergency_stop_active"] is False

    @pytest.mark.asyncio
    async def test_weekly_self_review(self, self_modification_plugin):
        """Test weekly self-review report generation."""
        review_result = await self_modification_plugin.generate_self_review_report()

        assert review_result["success"] is True
        assert "report_id" in review_result
        assert "period" in review_result
        assert "report_file" in review_result

        # Verify report file exists
        report_file = Path(review_result["report_file"])
        assert report_file.exists()

        # Check report content structure
        with open(report_file, 'r') as f:
            report_content = f.read()

        assert "Self-Review Report" in report_content
        assert "Analysis Period" in report_content
        assert "Metrics" in report_content

    @pytest.mark.asyncio
    async def test_safety_constraint_enforcement(self, self_modification_plugin):
        """Test that safety constraints are properly enforced."""
        # Test high-risk modification rejection
        dangerous_modification = {
            "type": "security_change",
            "target_file": "core/kernel.py",
            "description": "Disable all security checks",
            "changes": [
                {
                    "operation": "remove_security",
                    "function_name": "validate_security",
                    "modification": "Remove all security validations"
                }
            ],
            "rationale": "Remove security overhead"
        }

        proposal_result = await self_modification_plugin.propose_modification(dangerous_modification)

        # Should either be rejected or marked as high risk requiring approval
        if proposal_result["success"]:
            assert proposal_result["risk_assessment"]["level"] in ["high", "critical"]
            assert proposal_result["auto_approved"] is False
        else:
            assert "safety" in proposal_result["error"].lower() or "risk" in proposal_result["error"].lower()

    def test_plugin_function_availability(self, self_modification_plugin, deployment_plugin):
        """Test that all required functions are available."""
        # Self-modification functions
        self_mod_functions = self_modification_plugin.get_available_functions()
        required_self_mod_functions = [
            "propose_modification",
            "validate_proposal",
            "run_adversarial_testing",
            "request_human_approval",
            "list_pending_approvals",
            "generate_self_review_report"
        ]
        for func in required_self_mod_functions:
            assert func in self_mod_functions

        # Deployment functions
        deployment_functions = deployment_plugin.get_available_functions()
        required_deployment_functions = [
            "deploy_to_staging",
            "deploy_to_production",
            "rollback_deployment",
            "monitor_deployment_health",
            "create_backup",
            "restore_backup"
        ]
        for func in required_deployment_functions:
            assert func in deployment_functions

    @pytest.mark.asyncio
    async def test_end_to_end_pipeline_workflow(self, self_modification_plugin, deployment_plugin, rollback_manager):
        """Test complete end-to-end self-modification pipeline."""
        # Step 1: Create rollback point
        rollback_result = rollback_manager.create_rollback_point(
            "End-to-end pipeline test",
            "integration_test"
        )
        assert rollback_result["success"] is True

        # Step 2: Propose modification
        test_modification = {
            "type": "optimization",
            "target_file": "plugins/available/os_hello.py",
            "description": "Add performance logging",
            "changes": [
                {
                    "operation": "add_logging",
                    "location": "say_hello",
                    "modification": "Add execution time tracking"
                }
            ],
            "rationale": "Improve performance monitoring"
        }

        proposal_result = await self_modification_plugin.propose_modification(test_modification)
        assert proposal_result["success"] is True
        proposal_id = proposal_result["proposal_id"]

        # Step 3: Validate proposal
        validation_result = await self_modification_plugin.validate_proposal(proposal_id)
        assert validation_result["success"] is True

        # Step 4: Run adversarial testing
        adversarial_result = await self_modification_plugin.run_adversarial_testing(proposal_id)
        assert adversarial_result["success"] is True

        # Step 5: Request human approval
        approval_request = {
            "modification_id": proposal_id,
            "type": "optimization",
            "risk_level": "low",
            "description": test_modification["description"]
        }
        approval_result = await self_modification_plugin.request_human_approval(approval_request)
        assert approval_result["success"] is True

        # Step 6: Deploy to staging
        staging_config = {
            "environment": "staging",
            "changes": [proposal_id],
            "rollback_enabled": True
        }
        deploy_result = await deployment_plugin.deploy_to_staging(staging_config)
        assert deploy_result["success"] is True

        # Step 7: Monitor health
        health_result = await deployment_plugin.monitor_deployment_health(
            deploy_result["deployment_id"]
        )
        assert health_result["success"] is True

        # Pipeline completed successfully
        assert True

    @pytest.mark.asyncio
    async def test_plugin_cleanup(self, self_modification_plugin, deployment_plugin):
        """Test that plugins clean up properly."""
        # Test cleanup for both plugins
        await self_modification_plugin.cleanup()
        await deployment_plugin.cleanup()

        # Verify no exceptions were raised
        assert True

    def test_milestone_deliverables_validation(self, self_modification_plugin, deployment_plugin, rollback_manager):
        """Test that all milestone 6 deliverables are present and functional."""
        # Deliverable 1: AI self-modification capabilities
        self_mod_functions = self_modification_plugin.get_available_functions()
        assert "propose_modification" in self_mod_functions
        assert "validate_proposal" in self_mod_functions

        # Deliverable 2: Dev → sandbox → adversarial → human → staging → prod pipeline
        deployment_functions = deployment_plugin.get_available_functions()
        assert "deploy_to_staging" in deployment_functions
        assert "deploy_to_production" in deployment_functions

        # Deliverable 3: Adversarial testing framework
        assert "run_adversarial_testing" in self_mod_functions

        # Deliverable 4: Human approval gates
        assert "submit_for_human_review" in self_mod_functions
        assert "list_pending_modifications" in self_mod_functions

        # Deliverable 5: Rollback and safety mechanisms
        rollback_status = rollback_manager.get_system_status()
        assert rollback_status["success"] is True

        # Deliverable 6: Weekly self-review reporting
        assert "generate_self_review_report" in self_mod_functions

        # All deliverables validated
        assert True

    def test_safety_configuration_files(self, self_modification_plugin, rollback_manager):
        """Test safety configuration file creation and validation."""
        # Check that safety directories exist
        assert self_modification_plugin.self_mod_dir.exists()
        assert rollback_manager.safety_dir.exists()

        # Check for safety policy files
        safety_policy_file = self_modification_plugin.self_mod_dir / "safety_policy.json"
        assert safety_policy_file.exists()

        # Validate policy content
        with open(safety_policy_file, 'r') as f:
            policy = json.load(f)

        assert "modification_policies" in policy
        assert "approval_requirements" in policy
        assert policy["modification_policies"]["require_human_approval"] is True

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, self_modification_plugin, deployment_plugin):
        """Test error handling and recovery mechanisms."""
        # Test invalid modification proposal
        invalid_modification = {
            "type": "invalid_type",
            "target_file": "nonexistent_file.py",
            "description": "",  # Empty description
            "changes": [],  # Empty changes
            "rationale": ""
        }

        result = await self_modification_plugin.propose_modification(invalid_modification)
        assert result["success"] is False
        assert "error" in result

        # Test invalid deployment configuration
        invalid_config = {
            "environment": "invalid_env",
            "changes": None,  # Invalid changes
            "rollback_enabled": "not_boolean"  # Invalid type
        }

        deploy_result = await deployment_plugin.deploy_to_staging(invalid_config)
        assert deploy_result["success"] is False
        assert "error" in deploy_result

    @pytest.mark.asyncio
    async def test_concurrent_modifications_handling(self, self_modification_plugin):
        """Test handling of concurrent modification requests."""
        # Submit multiple modification proposals simultaneously
        modifications = [
            {
                "type": "enhancement",
                "target_file": f"test_file_{i}.py",
                "description": f"Test modification {i}",
                "changes": [{"operation": "add_function", "name": f"test_func_{i}"}],
                "rationale": f"Test concurrent modification {i}"
            }
            for i in range(3)
        ]

        # Submit all proposals concurrently
        tasks = [
            self_modification_plugin.propose_modification(mod)
            for mod in modifications
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all proposals were handled (either accepted or properly rejected)
        for result in results:
            assert isinstance(result, dict)
            assert "success" in result
            # At least some should succeed, or all should fail gracefully
            if not result["success"]:
                assert "error" in result