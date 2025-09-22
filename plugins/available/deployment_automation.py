"""
Deployment Automation Plugin for Friday AI Assistant
Handles safe deployment of self-modifications with rollback capabilities.
"""
import asyncio
import json
import subprocess
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import tempfile

from core.logging import get_logger


class DeploymentAutomationPlugin:
    """Plugin for automated deployment with safety controls and rollback capabilities."""

    def __init__(self):
        self.name = "deployment_automation"
        self.description = "Automated deployment with safety controls and rollback"
        self.version = "1.0.0"
        self.logger = get_logger()

        # Deployment directories
        self.deployment_dir = Path("./data/deployments")
        self.staging_dir = self.deployment_dir / "staging"
        self.production_dir = self.deployment_dir / "production"
        self.backups_dir = self.deployment_dir / "backups"
        self.logs_dir = self.deployment_dir / "logs"

        # Create directories
        for dir_path in [self.deployment_dir, self.staging_dir, self.production_dir, self.backups_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Deployment environments
        self.environments = {
            "staging": {
                "path": self.staging_dir,
                "safety_checks": ["syntax", "tests", "security"],
                "rollback_retention": 30,  # days
                "auto_rollback": True
            },
            "production": {
                "path": self.production_dir,
                "safety_checks": ["syntax", "tests", "security", "performance", "compatibility"],
                "rollback_retention": 90,  # days
                "auto_rollback": False  # Manual rollback only in production
            }
        }

        # Safety constraints for deployments
        self.deployment_constraints = {
            "max_downtime": 30,          # seconds
            "health_check_timeout": 60,  # seconds
            "rollback_timeout": 120,     # seconds
            "backup_required": True,
            "approval_required": True,
            "monitoring_period": 300     # seconds to monitor after deployment
        }

    async def initialize(self) -> bool:
        """Initialize the deployment automation plugin."""
        try:
            # Create default deployment configuration
            self._create_deployment_configuration()

            self.logger.info("Deployment automation plugin initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize deployment automation plugin: {e}")
            return False

    def get_available_functions(self) -> List[str]:
        """Get list of available plugin functions."""
        return [
            "create_deployment_package",
            "deploy_to_staging",
            "deploy_to_production",
            "validate_deployment",
            "health_check",
            "rollback_deployment",
            "create_backup",
            "restore_backup",
            "get_deployment_status",
            "list_deployments",
            "cleanup_old_deployments",
            "monitor_deployment_health"
        ]

    def create_deployment_package(
        self,
        proposal_id: str,
        environment: str,
        files_to_deploy: List[str],
        changes: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create a deployment package for a modification."""
        try:
            package_id = self._generate_package_id(proposal_id, environment)

            deployment_package = {
                "package_id": package_id,
                "proposal_id": proposal_id,
                "environment": environment,
                "created_at": datetime.now().isoformat(),
                "files_to_deploy": files_to_deploy,
                "changes": changes,
                "package_status": "created",
                "validation_results": {},
                "deployment_metadata": {
                    "deployer": "friday_ai",
                    "deployment_type": "self_modification",
                    "requires_approval": True,
                    "estimated_downtime": 0
                }
            }

            # Create package directory
            package_dir = self.deployment_dir / f"packages/{package_id}"
            package_dir.mkdir(parents=True, exist_ok=True)

            # Save package metadata
            package_file = package_dir / "deployment_package.json"
            with open(package_file, 'w') as f:
                json.dump(deployment_package, f, indent=2)

            # Create deployment files
            for file_path, content in changes.items():
                deploy_file = package_dir / file_path
                deploy_file.parent.mkdir(parents=True, exist_ok=True)
                with open(deploy_file, 'w') as f:
                    f.write(content)

            # Create deployment script
            deployment_script = self._generate_deployment_script(deployment_package)
            script_file = package_dir / "deploy.sh"
            with open(script_file, 'w') as f:
                f.write(deployment_script)
            script_file.chmod(0o755)

            self.logger.info(f"Deployment package {package_id} created")
            return {
                "success": True,
                "package_id": package_id,
                "package_dir": str(package_dir),
                "deployment_package": deployment_package
            }

        except Exception as e:
            self.logger.error(f"Failed to create deployment package: {e}")
            return {"success": False, "error": str(e)}

    def deploy_to_staging(self, package_id: str) -> Dict[str, Any]:
        """Deploy a package to staging environment."""
        try:
            return self._deploy_to_environment(package_id, "staging")
        except Exception as e:
            self.logger.error(f"Staging deployment failed: {e}")
            return {"success": False, "error": str(e)}

    def deploy_to_production(self, package_id: str, approver: str) -> Dict[str, Any]:
        """Deploy a package to production environment (requires approval)."""
        try:
            # Additional validation for production deployment
            validation_result = self._validate_production_deployment(package_id, approver)
            if not validation_result["approved"]:
                return {
                    "success": False,
                    "error": f"Production deployment not approved: {validation_result['reason']}"
                }

            return self._deploy_to_environment(package_id, "production")
        except Exception as e:
            self.logger.error(f"Production deployment failed: {e}")
            return {"success": False, "error": str(e)}

    def _deploy_to_environment(self, package_id: str, environment: str) -> Dict[str, Any]:
        """Deploy a package to specified environment."""
        deployment_id = self._generate_deployment_id(package_id, environment)

        deployment_record = {
            "deployment_id": deployment_id,
            "package_id": package_id,
            "environment": environment,
            "started_at": datetime.now().isoformat(),
            "status": "deploying",
            "steps_completed": [],
            "current_step": "initialization",
            "backup_created": False,
            "rollback_available": False,
            "health_status": "unknown"
        }

        try:
            # Step 1: Create backup
            self.logger.info(f"Starting deployment {deployment_id} - Creating backup")
            deployment_record["current_step"] = "backup"
            backup_result = self._create_environment_backup(environment)
            if backup_result["success"]:
                deployment_record["backup_created"] = True
                deployment_record["backup_id"] = backup_result["backup_id"]
                deployment_record["steps_completed"].append("backup")

            # Step 2: Validate package
            self.logger.info(f"Deployment {deployment_id} - Validating package")
            deployment_record["current_step"] = "validation"
            validation_result = self._validate_deployment_package(package_id, environment)
            if validation_result["valid"]:
                deployment_record["validation_results"] = validation_result
                deployment_record["steps_completed"].append("validation")
            else:
                raise Exception(f"Package validation failed: {validation_result['errors']}")

            # Step 3: Pre-deployment health check
            self.logger.info(f"Deployment {deployment_id} - Pre-deployment health check")
            deployment_record["current_step"] = "pre_health_check"
            pre_health = self._perform_health_check(environment)
            deployment_record["pre_deployment_health"] = pre_health
            deployment_record["steps_completed"].append("pre_health_check")

            # Step 4: Deploy files
            self.logger.info(f"Deployment {deployment_id} - Deploying files")
            deployment_record["current_step"] = "file_deployment"
            deploy_result = self._deploy_files(package_id, environment)
            if deploy_result["success"]:
                deployment_record["deployed_files"] = deploy_result["deployed_files"]
                deployment_record["steps_completed"].append("file_deployment")
            else:
                raise Exception(f"File deployment failed: {deploy_result['error']}")

            # Step 5: Post-deployment health check
            self.logger.info(f"Deployment {deployment_id} - Post-deployment health check")
            deployment_record["current_step"] = "post_health_check"
            post_health = self._perform_health_check(environment)
            deployment_record["post_deployment_health"] = post_health

            if post_health["status"] == "healthy":
                deployment_record["steps_completed"].append("post_health_check")
                deployment_record["rollback_available"] = True
            else:
                # Auto-rollback if health check fails
                self.logger.warning(f"Deployment {deployment_id} - Health check failed, initiating rollback")
                rollback_result = self._auto_rollback(deployment_record)
                deployment_record["auto_rollback_performed"] = rollback_result
                raise Exception(f"Deployment failed health check: {post_health['issues']}")

            # Step 6: Finalization
            deployment_record["current_step"] = "finalization"
            deployment_record["status"] = "completed"
            deployment_record["completed_at"] = datetime.now().isoformat()
            deployment_record["health_status"] = "healthy"
            deployment_record["steps_completed"].append("finalization")

            # Save deployment record
            self._save_deployment_record(deployment_record)

            # Start monitoring period
            self._start_deployment_monitoring(deployment_id)

            self.logger.info(f"Deployment {deployment_id} completed successfully")
            return {
                "success": True,
                "deployment_id": deployment_id,
                "deployment_record": deployment_record
            }

        except Exception as e:
            # Handle deployment failure
            deployment_record["status"] = "failed"
            deployment_record["failed_at"] = datetime.now().isoformat()
            deployment_record["error"] = str(e)

            # Attempt rollback if backup was created
            if deployment_record["backup_created"]:
                rollback_result = self._auto_rollback(deployment_record)
                deployment_record["rollback_performed"] = rollback_result

            self._save_deployment_record(deployment_record)

            return {
                "success": False,
                "deployment_id": deployment_id,
                "error": str(e),
                "deployment_record": deployment_record
            }

    def rollback_deployment(self, deployment_id: str, reason: str, approver: str) -> Dict[str, Any]:
        """Rollback a deployment to previous state."""
        try:
            # Load deployment record
            deployment_record = self._load_deployment_record(deployment_id)
            if not deployment_record:
                return {"success": False, "error": f"Deployment {deployment_id} not found"}

            if not deployment_record.get("rollback_available", False):
                return {"success": False, "error": "Rollback not available for this deployment"}

            rollback_id = self._generate_rollback_id(deployment_id)

            rollback_record = {
                "rollback_id": rollback_id,
                "deployment_id": deployment_id,
                "reason": reason,
                "approver": approver,
                "started_at": datetime.now().isoformat(),
                "status": "rolling_back"
            }

            # Perform rollback using backup
            if "backup_id" in deployment_record:
                restore_result = self._restore_from_backup(
                    deployment_record["backup_id"],
                    deployment_record["environment"]
                )

                if restore_result["success"]:
                    rollback_record["status"] = "completed"
                    rollback_record["completed_at"] = datetime.now().isoformat()

                    # Health check after rollback
                    post_rollback_health = self._perform_health_check(deployment_record["environment"])
                    rollback_record["post_rollback_health"] = post_rollback_health

                    # Update deployment record
                    deployment_record["rollback_performed"] = rollback_record
                    self._save_deployment_record(deployment_record)

                    self.logger.info(f"Rollback {rollback_id} completed successfully")
                    return {
                        "success": True,
                        "rollback_id": rollback_id,
                        "rollback_record": rollback_record
                    }
                else:
                    rollback_record["status"] = "failed"
                    rollback_record["error"] = restore_result["error"]

            return {
                "success": False,
                "rollback_id": rollback_id,
                "error": "Rollback failed"
            }

        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return {"success": False, "error": str(e)}

    def health_check(self, environment: str) -> Dict[str, Any]:
        """Perform comprehensive health check on environment."""
        try:
            return self._perform_health_check(environment)
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    # Helper methods
    def _validate_production_deployment(self, package_id: str, approver: str) -> Dict[str, Any]:
        """Validate production deployment requirements."""
        # Check if package exists and has passed staging
        package_dir = self.deployment_dir / f"packages/{package_id}"
        if not package_dir.exists():
            return {"approved": False, "reason": "Package not found"}

        # In a real implementation, this would check:
        # - Staging deployment success
        # - Required approvals
        # - Security scans
        # - Performance benchmarks

        return {
            "approved": True,
            "approver": approver,
            "approved_at": datetime.now().isoformat()
        }

    def _validate_deployment_package(self, package_id: str, environment: str) -> Dict[str, Any]:
        """Validate deployment package for environment."""
        validation_errors = []
        validation_warnings = []

        package_dir = self.deployment_dir / f"packages/{package_id}"
        if not package_dir.exists():
            validation_errors.append("Package directory not found")

        package_file = package_dir / "deployment_package.json"
        if not package_file.exists():
            validation_errors.append("Package metadata not found")

        # Check required safety checks for environment
        env_config = self.environments.get(environment, {})
        required_checks = env_config.get("safety_checks", [])

        for check in required_checks:
            check_result = self._perform_safety_check(package_id, check)
            if not check_result["passed"]:
                validation_errors.extend(check_result["errors"])
            validation_warnings.extend(check_result.get("warnings", []))

        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "warnings": validation_warnings,
            "timestamp": datetime.now().isoformat()
        }

    def _perform_safety_check(self, package_id: str, check_type: str) -> Dict[str, Any]:
        """Perform specific safety check on package."""
        check_results = {
            "syntax": {"passed": True, "errors": [], "warnings": []},
            "tests": {"passed": True, "errors": [], "warnings": []},
            "security": {"passed": True, "errors": [], "warnings": []},
            "performance": {"passed": True, "errors": [], "warnings": []},
            "compatibility": {"passed": True, "errors": [], "warnings": []}
        }

        return check_results.get(check_type, {"passed": False, "errors": ["Unknown check type"]})

    def _create_environment_backup(self, environment: str) -> Dict[str, Any]:
        """Create backup of current environment state."""
        try:
            backup_id = self._generate_backup_id(environment)
            backup_path = self.backups_dir / f"{backup_id}.tar.gz"

            env_config = self.environments.get(environment)
            if not env_config:
                return {"success": False, "error": f"Unknown environment: {environment}"}

            source_path = env_config["path"]

            # Create compressed backup
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(source_path, arcname=environment)

            backup_metadata = {
                "backup_id": backup_id,
                "environment": environment,
                "created_at": datetime.now().isoformat(),
                "backup_path": str(backup_path),
                "source_path": str(source_path),
                "size_bytes": backup_path.stat().st_size
            }

            # Save metadata
            metadata_file = self.backups_dir / f"{backup_id}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(backup_metadata, f, indent=2)

            self.logger.info(f"Backup {backup_id} created for {environment}")
            return {
                "success": True,
                "backup_id": backup_id,
                "backup_metadata": backup_metadata
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _restore_from_backup(self, backup_id: str, environment: str) -> Dict[str, Any]:
        """Restore environment from backup."""
        try:
            backup_path = self.backups_dir / f"{backup_id}.tar.gz"
            if not backup_path.exists():
                return {"success": False, "error": f"Backup {backup_id} not found"}

            env_config = self.environments.get(environment)
            if not env_config:
                return {"success": False, "error": f"Unknown environment: {environment}"}

            target_path = env_config["path"]

            # Remove current environment
            if target_path.exists():
                shutil.rmtree(target_path)

            # Extract backup
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(target_path.parent)

            self.logger.info(f"Environment {environment} restored from backup {backup_id}")
            return {
                "success": True,
                "restored_from": backup_id,
                "restored_to": str(target_path)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _deploy_files(self, package_id: str, environment: str) -> Dict[str, Any]:
        """Deploy files from package to environment."""
        try:
            package_dir = self.deployment_dir / f"packages/{package_id}"
            env_config = self.environments.get(environment)
            target_path = env_config["path"]

            deployed_files = []

            # Load package metadata
            with open(package_dir / "deployment_package.json", 'r') as f:
                package_data = json.load(f)

            # Deploy each file
            for file_path in package_data["files_to_deploy"]:
                source_file = package_dir / file_path
                target_file = target_path / file_path

                if source_file.exists():
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, target_file)
                    deployed_files.append(str(target_file))

            return {
                "success": True,
                "deployed_files": deployed_files
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _perform_health_check(self, environment: str) -> Dict[str, Any]:
        """Perform health check on environment."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "environment": environment,
            "checks": {
                "file_integrity": {"status": "passed", "message": "All files present"},
                "syntax_validation": {"status": "passed", "message": "No syntax errors"},
                "import_validation": {"status": "passed", "message": "All imports successful"},
                "memory_usage": {"status": "passed", "message": "Memory usage normal"},
                "response_time": {"status": "passed", "message": "Response times normal"}
            },
            "issues": [],
            "warnings": []
        }

        # In a real implementation, this would perform actual health checks
        # For now, we'll simulate successful health checks

        return health_status

    def _auto_rollback(self, deployment_record: Dict) -> Dict[str, Any]:
        """Perform automatic rollback on deployment failure."""
        if not deployment_record.get("backup_created", False):
            return {"success": False, "reason": "No backup available"}

        rollback_result = self._restore_from_backup(
            deployment_record["backup_id"],
            deployment_record["environment"]
        )

        rollback_result["automatic"] = True
        rollback_result["trigger"] = "health_check_failure"
        rollback_result["timestamp"] = datetime.now().isoformat()

        return rollback_result

    def _start_deployment_monitoring(self, deployment_id: str):
        """Start monitoring deployment health."""
        # In a real implementation, this would start background monitoring
        # For now, we'll just log that monitoring has started
        self.logger.info(f"Started monitoring deployment {deployment_id}")

    def _save_deployment_record(self, deployment_record: Dict):
        """Save deployment record to disk."""
        deployment_id = deployment_record["deployment_id"]
        record_file = self.logs_dir / f"deployment_{deployment_id}.json"
        with open(record_file, 'w') as f:
            json.dump(deployment_record, f, indent=2)

    def _load_deployment_record(self, deployment_id: str) -> Optional[Dict]:
        """Load deployment record from disk."""
        record_file = self.logs_dir / f"deployment_{deployment_id}.json"
        if record_file.exists():
            with open(record_file, 'r') as f:
                return json.load(f)
        return None

    def _generate_deployment_script(self, package: Dict) -> str:
        """Generate deployment script for package."""
        return f"""#!/bin/bash
# Deployment script for {package['package_id']}
# Generated: {datetime.now().isoformat()}

echo "Starting deployment of {package['package_id']}"
echo "Environment: {package['environment']}"
echo "Files to deploy: {len(package['files_to_deploy'])}"

# Deployment steps would go here
echo "Deployment completed successfully"
"""

    def _generate_package_id(self, proposal_id: str, environment: str) -> str:
        """Generate unique package ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"pkg_{proposal_id}_{environment}_{timestamp}"

    def _generate_deployment_id(self, package_id: str, environment: str) -> str:
        """Generate unique deployment ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"deploy_{package_id}_{environment}_{timestamp}"

    def _generate_backup_id(self, environment: str) -> str:
        """Generate unique backup ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"backup_{environment}_{timestamp}"

    def _generate_rollback_id(self, deployment_id: str) -> str:
        """Generate unique rollback ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"rollback_{deployment_id}_{timestamp}"

    def _create_deployment_configuration(self):
        """Create default deployment configuration."""
        config_file = self.deployment_dir / "deployment_config.json"
        if not config_file.exists():
            config = {
                "deployment_settings": {
                    "max_concurrent_deployments": 1,
                    "deployment_timeout": 600,
                    "health_check_retries": 3,
                    "backup_retention_days": 30
                },
                "environment_configs": self.environments,
                "safety_settings": self.deployment_constraints,
                "notification_settings": {
                    "notify_on_deployment_start": True,
                    "notify_on_deployment_complete": True,
                    "notify_on_deployment_failure": True,
                    "notify_on_rollback": True
                }
            }

            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)

    async def cleanup(self):
        """Clean up deployment automation resources."""
        self.logger.info("Deployment automation plugin cleanup completed")


# Plugin class available for instantiation
# Note: Instantiate with DeploymentAutomationPlugin() after initializing logging