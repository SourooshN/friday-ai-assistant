#!/usr/bin/env python3
"""
Rollback Manager for Self-Modification Pipeline
Provides comprehensive rollback capabilities and safety mechanisms for AI self-modifications.
"""

import json
import os
import shutil
import subprocess
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import tempfile
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages rollback operations and safety mechanisms for self-modifications."""

    def __init__(self, base_dir: str = "/home/nazari/projects/friday-ai-assistant"):
        self.base_dir = Path(base_dir)
        self.safety_dir = self.base_dir / "data" / "safety"
        self.backups_dir = self.safety_dir / "backups"
        self.rollback_log = self.safety_dir / "rollback_log.json"
        self.system_state_file = self.safety_dir / "system_state.json"

        # Critical files that must be backed up before any modification
        self.critical_files = [
            "main.py",
            "core/kernel.py",
            "core/orchestrator.py",
            "plugins/plugin_loader.py",
            "pyproject.toml",
            "requirements.txt"
        ]

        # Safety constraints
        self.max_rollback_retention = 30  # Days
        self.max_backup_size_mb = 1000    # MB
        self.critical_system_checks = [
            "python_syntax_valid",
            "imports_available",
            "core_functions_intact",
            "config_files_valid"
        ]

        self._ensure_directories()
        self._initialize_safety_state()

    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def _initialize_safety_state(self) -> None:
        """Initialize system safety state tracking."""
        if not self.system_state_file.exists():
            initial_state = {
                "created": datetime.now().isoformat(),
                "last_backup": None,
                "system_hash": self._calculate_system_hash(),
                "rollback_points": [],
                "safety_checks_enabled": True,
                "emergency_stop_file": str(self.safety_dir / "EMERGENCY_STOP")
            }

            with open(self.system_state_file, 'w') as f:
                json.dump(initial_state, f, indent=2)

    def _calculate_system_hash(self) -> str:
        """Calculate hash of critical system files."""
        hasher = hashlib.sha256()

        for file_path in self.critical_files:
            full_path = self.base_dir / file_path
            if full_path.exists():
                with open(full_path, 'rb') as f:
                    hasher.update(f.read())

        return hasher.hexdigest()

    def create_rollback_point(self, description: str, modification_type: str = "unknown") -> Dict[str, Any]:
        """Create a complete rollback point before making modifications."""
        timestamp = datetime.now()
        rollback_id = f"rollback_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Creating rollback point: {rollback_id}")

        try:
            # Create backup directory for this rollback point
            rollback_dir = self.backups_dir / rollback_id
            rollback_dir.mkdir(exist_ok=True)

            # Backup critical files
            backup_manifest = self._backup_critical_files(rollback_dir)

            # Capture system state
            system_state = self._capture_system_state()

            # Create rollback metadata
            rollback_metadata = {
                "id": rollback_id,
                "timestamp": timestamp.isoformat(),
                "description": description,
                "modification_type": modification_type,
                "system_hash_before": self._calculate_system_hash(),
                "backup_location": str(rollback_dir),
                "backup_manifest": backup_manifest,
                "system_state": system_state,
                "rollback_tested": False,
                "size_mb": self._calculate_backup_size(rollback_dir)
            }

            # Save rollback metadata
            metadata_file = rollback_dir / "rollback_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(rollback_metadata, f, indent=2)

            # Update system state
            self._update_system_state_rollback(rollback_metadata)

            # Log rollback creation
            self._log_rollback_operation("create", rollback_metadata)

            logger.info(f"Rollback point created successfully: {rollback_id}")

            return {
                "success": True,
                "rollback_id": rollback_id,
                "backup_location": str(rollback_dir),
                "files_backed_up": len(backup_manifest),
                "size_mb": rollback_metadata["size_mb"]
            }

        except Exception as e:
            logger.error(f"Failed to create rollback point: {e}")
            return {
                "success": False,
                "error": str(e),
                "rollback_id": None
            }

    def _backup_critical_files(self, rollback_dir: Path) -> List[Dict[str, str]]:
        """Backup all critical files and return manifest."""
        manifest = []

        # Backup critical files
        for file_path in self.critical_files:
            source_path = self.base_dir / file_path
            if source_path.exists():
                dest_path = rollback_dir / file_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(source_path, dest_path)
                manifest.append({
                    "file": file_path,
                    "source": str(source_path),
                    "backup": str(dest_path),
                    "size": source_path.stat().st_size,
                    "modified": datetime.fromtimestamp(source_path.stat().st_mtime).isoformat()
                })

        # Backup entire plugins directory
        plugins_source = self.base_dir / "plugins"
        plugins_backup = rollback_dir / "plugins"
        if plugins_source.exists():
            shutil.copytree(plugins_source, plugins_backup, dirs_exist_ok=True)

            # Add plugins to manifest
            for plugin_file in plugins_source.rglob("*.py"):
                rel_path = plugin_file.relative_to(self.base_dir)
                manifest.append({
                    "file": str(rel_path),
                    "source": str(plugin_file),
                    "backup": str(rollback_dir / rel_path),
                    "size": plugin_file.stat().st_size,
                    "modified": datetime.fromtimestamp(plugin_file.stat().st_mtime).isoformat()
                })

        # Backup core directory
        core_source = self.base_dir / "core"
        core_backup = rollback_dir / "core"
        if core_source.exists():
            shutil.copytree(core_source, core_backup, dirs_exist_ok=True)

            # Add core files to manifest
            for core_file in core_source.rglob("*.py"):
                rel_path = core_file.relative_to(self.base_dir)
                manifest.append({
                    "file": str(rel_path),
                    "source": str(core_file),
                    "backup": str(rollback_dir / rel_path),
                    "size": core_file.stat().st_size,
                    "modified": datetime.fromtimestamp(core_file.stat().st_mtime).isoformat()
                })

        return manifest

    def _capture_system_state(self) -> Dict[str, Any]:
        """Capture current system state for rollback validation."""
        try:
            state = {
                "timestamp": datetime.now().isoformat(),
                "python_version": self._get_python_version(),
                "installed_packages": self._get_installed_packages(),
                "git_status": self._get_git_status(),
                "system_checks": self._run_system_checks(),
                "config_status": self._check_config_files(),
                "process_status": self._check_running_processes()
            }

            return state

        except Exception as e:
            logger.warning(f"Failed to capture complete system state: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def _get_python_version(self) -> str:
        """Get current Python version."""
        try:
            result = subprocess.run(['python3', '--version'],
                                  capture_output=True, text=True, timeout=10)
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _get_installed_packages(self) -> List[str]:
        """Get list of installed Python packages."""
        try:
            result = subprocess.run(['pip', 'freeze'],
                                  capture_output=True, text=True, timeout=30)
            return result.stdout.strip().split('\n')
        except Exception:
            return []

    def _get_git_status(self) -> Dict[str, str]:
        """Get current Git status."""
        try:
            # Get current branch
            branch_result = subprocess.run(['git', 'branch', '--show-current'],
                                         capture_output=True, text=True, timeout=10,
                                         cwd=self.base_dir)

            # Get commit hash
            commit_result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                                         capture_output=True, text=True, timeout=10,
                                         cwd=self.base_dir)

            # Get status
            status_result = subprocess.run(['git', 'status', '--porcelain'],
                                         capture_output=True, text=True, timeout=10,
                                         cwd=self.base_dir)

            return {
                "branch": branch_result.stdout.strip(),
                "commit": commit_result.stdout.strip(),
                "status": status_result.stdout.strip(),
                "dirty": bool(status_result.stdout.strip())
            }

        except Exception as e:
            return {"error": str(e)}

    def _run_system_checks(self) -> Dict[str, bool]:
        """Run critical system checks."""
        checks = {}

        # Check Python syntax of critical files
        checks["python_syntax_valid"] = self._check_python_syntax()

        # Check import availability
        checks["imports_available"] = self._check_critical_imports()

        # Check core functions
        checks["core_functions_intact"] = self._check_core_functions()

        # Check config files
        checks["config_files_valid"] = self._check_config_validity()

        return checks

    def _check_python_syntax(self) -> bool:
        """Check Python syntax of critical files."""
        try:
            for file_path in self.critical_files:
                full_path = self.base_dir / file_path
                if full_path.exists() and full_path.suffix == '.py':
                    result = subprocess.run(['python3', '-m', 'py_compile', str(full_path)],
                                          capture_output=True, timeout=30)
                    if result.returncode != 0:
                        return False
            return True
        except Exception:
            return False

    def _check_critical_imports(self) -> bool:
        """Check that critical imports are available."""
        try:
            critical_imports = ['asyncio', 'pathlib', 'json', 'logging', 'typing']
            for module in critical_imports:
                result = subprocess.run(['python3', '-c', f'import {module}'],
                                      capture_output=True, timeout=10)
                if result.returncode != 0:
                    return False
            return True
        except Exception:
            return False

    def _check_core_functions(self) -> bool:
        """Check that core functions are intact."""
        try:
            # Check if main.py can be imported
            main_file = self.base_dir / "main.py"
            if main_file.exists():
                result = subprocess.run(['python3', '-c', 'import sys; sys.path.append("."); import main'],
                                      capture_output=True, timeout=15, cwd=self.base_dir)
                return result.returncode == 0
            return False
        except Exception:
            return False

    def _check_config_validity(self) -> bool:
        """Check that configuration files are valid."""
        try:
            config_files = ['pyproject.toml']
            for config_file in config_files:
                config_path = self.base_dir / config_file
                if config_path.exists():
                    if config_file.endswith('.toml'):
                        # Basic TOML validation
                        try:
                            import tomli
                            with open(config_path, 'rb') as f:
                                tomli.load(f)
                        except ImportError:
                            # Fallback to basic syntax check
                            with open(config_path, 'r') as f:
                                content = f.read()
                                if '[' not in content or '=' not in content:
                                    return False
            return True
        except Exception:
            return False

    def _check_config_files(self) -> Dict[str, bool]:
        """Check status of configuration files."""
        config_status = {}

        config_files = {
            'pyproject.toml': self.base_dir / 'pyproject.toml',
            'requirements.txt': self.base_dir / 'requirements.txt'
        }

        for name, path in config_files.items():
            config_status[name] = path.exists()

        return config_status

    def _check_running_processes(self) -> Dict[str, Any]:
        """Check for running processes that might be affected."""
        try:
            # Check if any Friday processes are running
            result = subprocess.run(['pgrep', '-f', 'friday'],
                                  capture_output=True, text=True, timeout=10)

            return {
                "friday_processes": result.stdout.strip().split('\n') if result.stdout.strip() else [],
                "process_count": len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            }

        except Exception as e:
            return {"error": str(e)}

    def _calculate_backup_size(self, backup_dir: Path) -> float:
        """Calculate size of backup in MB."""
        try:
            total_size = 0
            for file_path in backup_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return round(total_size / (1024 * 1024), 2)  # Convert to MB
        except Exception:
            return 0.0

    def execute_rollback(self, rollback_id: str, force: bool = False) -> Dict[str, Any]:
        """Execute rollback to a specific point."""
        logger.info(f"Executing rollback to: {rollback_id}")

        try:
            # Load rollback metadata
            rollback_dir = self.backups_dir / rollback_id
            metadata_file = rollback_dir / "rollback_metadata.json"

            if not metadata_file.exists():
                return {
                    "success": False,
                    "error": f"Rollback point {rollback_id} not found"
                }

            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            # Safety checks (unless forced)
            if not force:
                safety_check = self._pre_rollback_safety_check(metadata)
                if not safety_check["safe"]:
                    return {
                        "success": False,
                        "error": f"Safety check failed: {safety_check['reasons']}",
                        "force_required": True
                    }

            # Create emergency backup of current state
            emergency_backup = self.create_rollback_point(
                f"Emergency backup before rollback to {rollback_id}",
                "emergency_pre_rollback"
            )

            if not emergency_backup["success"]:
                return {
                    "success": False,
                    "error": "Failed to create emergency backup before rollback"
                }

            # Execute rollback
            rollback_results = self._restore_from_backup(rollback_dir, metadata)

            if rollback_results["success"]:
                # Post-rollback validation
                validation_results = self._post_rollback_validation(metadata)

                # Log rollback operation
                self._log_rollback_operation("execute", {
                    **metadata,
                    "emergency_backup_id": emergency_backup["rollback_id"],
                    "validation_results": validation_results
                })

                return {
                    "success": True,
                    "rollback_id": rollback_id,
                    "emergency_backup_id": emergency_backup["rollback_id"],
                    "files_restored": rollback_results["files_restored"],
                    "validation_results": validation_results
                }
            else:
                return {
                    "success": False,
                    "error": rollback_results["error"],
                    "emergency_backup_id": emergency_backup["rollback_id"]
                }

        except Exception as e:
            logger.error(f"Rollback execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _pre_rollback_safety_check(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Perform safety checks before rollback."""
        reasons = []

        # Check age of rollback point
        rollback_time = datetime.fromisoformat(metadata["timestamp"])
        age_days = (datetime.now() - rollback_time).days

        if age_days > 7:
            reasons.append(f"Rollback point is {age_days} days old")

        # Check if current system is significantly different
        current_hash = self._calculate_system_hash()
        if current_hash == metadata["system_hash_before"]:
            reasons.append("No system changes detected since rollback point")

        # Check for emergency stop file
        emergency_stop_file = self.safety_dir / "EMERGENCY_STOP"
        if emergency_stop_file.exists():
            reasons.append("Emergency stop file detected")

        # Check system health
        current_checks = self._run_system_checks()
        if not all(current_checks.values()):
            reasons.append("Current system failing health checks")

        return {
            "safe": len(reasons) == 0,
            "reasons": reasons,
            "age_days": age_days,
            "current_hash": current_hash
        }

    def _restore_from_backup(self, rollback_dir: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Restore files from backup."""
        try:
            files_restored = []

            # Restore files according to backup manifest
            for file_info in metadata["backup_manifest"]:
                source_backup = Path(file_info["backup"])
                dest_file = Path(file_info["source"])

                if source_backup.exists():
                    # Ensure destination directory exists
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    # Restore file
                    shutil.copy2(source_backup, dest_file)
                    files_restored.append(file_info["file"])

            return {
                "success": True,
                "files_restored": files_restored
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _post_rollback_validation(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate system after rollback."""
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "system_checks": self._run_system_checks(),
            "hash_verification": self._calculate_system_hash() == metadata["system_hash_before"],
            "import_test": self._test_critical_imports(),
            "syntax_validation": self._check_python_syntax()
        }

        validation_results["overall_success"] = all([
            all(validation_results["system_checks"].values()),
            validation_results["hash_verification"],
            validation_results["import_test"],
            validation_results["syntax_validation"]
        ])

        return validation_results

    def _test_critical_imports(self) -> bool:
        """Test that critical modules can be imported after rollback."""
        try:
            import sys
            original_path = sys.path.copy()
            sys.path.insert(0, str(self.base_dir))

            # Test core imports
            test_modules = ['core.kernel', 'plugins.plugin_loader']
            for module in test_modules:
                try:
                    __import__(module)
                except ImportError:
                    return False

            sys.path = original_path
            return True

        except Exception:
            return False

    def list_rollback_points(self) -> Dict[str, Any]:
        """List all available rollback points."""
        try:
            rollback_points = []

            for rollback_dir in self.backups_dir.iterdir():
                if rollback_dir.is_dir():
                    metadata_file = rollback_dir / "rollback_metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)

                        rollback_points.append({
                            "id": metadata["id"],
                            "timestamp": metadata["timestamp"],
                            "description": metadata["description"],
                            "modification_type": metadata["modification_type"],
                            "size_mb": metadata["size_mb"],
                            "age_days": (datetime.now() - datetime.fromisoformat(metadata["timestamp"])).days
                        })

            # Sort by timestamp (newest first)
            rollback_points.sort(key=lambda x: x["timestamp"], reverse=True)

            return {
                "success": True,
                "rollback_points": rollback_points,
                "total_count": len(rollback_points)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def cleanup_old_rollbacks(self, days_to_keep: int = None) -> Dict[str, Any]:
        """Clean up old rollback points."""
        if days_to_keep is None:
            days_to_keep = self.max_rollback_retention

        try:
            cleanup_before = datetime.now() - timedelta(days=days_to_keep)
            removed_rollbacks = []
            total_space_freed = 0.0

            for rollback_dir in self.backups_dir.iterdir():
                if rollback_dir.is_dir():
                    metadata_file = rollback_dir / "rollback_metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)

                        rollback_time = datetime.fromisoformat(metadata["timestamp"])
                        if rollback_time < cleanup_before:
                            # Calculate space before removal
                            space_freed = self._calculate_backup_size(rollback_dir)

                            # Remove rollback directory
                            shutil.rmtree(rollback_dir)

                            removed_rollbacks.append({
                                "id": metadata["id"],
                                "timestamp": metadata["timestamp"],
                                "size_mb": space_freed
                            })
                            total_space_freed += space_freed

            return {
                "success": True,
                "removed_rollbacks": removed_rollbacks,
                "total_removed": len(removed_rollbacks),
                "space_freed_mb": total_space_freed
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def create_emergency_stop(self, reason: str) -> Dict[str, Any]:
        """Create emergency stop file to prevent further modifications."""
        try:
            emergency_stop_file = self.safety_dir / "EMERGENCY_STOP"

            emergency_data = {
                "timestamp": datetime.now().isoformat(),
                "reason": reason,
                "system_hash": self._calculate_system_hash(),
                "created_by": "rollback_manager"
            }

            with open(emergency_stop_file, 'w') as f:
                json.dump(emergency_data, f, indent=2)

            logger.warning(f"Emergency stop activated: {reason}")

            return {
                "success": True,
                "emergency_stop_file": str(emergency_stop_file),
                "reason": reason
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def clear_emergency_stop(self, confirmation: str = None) -> Dict[str, Any]:
        """Clear emergency stop file (requires confirmation)."""
        if confirmation != "CONFIRM_CLEAR_EMERGENCY_STOP":
            return {
                "success": False,
                "error": "Emergency stop clear requires confirmation string: 'CONFIRM_CLEAR_EMERGENCY_STOP'"
            }

        try:
            emergency_stop_file = self.safety_dir / "EMERGENCY_STOP"

            if emergency_stop_file.exists():
                emergency_stop_file.unlink()
                logger.info("Emergency stop cleared")

                return {
                    "success": True,
                    "message": "Emergency stop cleared"
                }
            else:
                return {
                    "success": True,
                    "message": "No emergency stop file found"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _update_system_state_rollback(self, rollback_metadata: Dict[str, Any]) -> None:
        """Update system state with new rollback point."""
        try:
            with open(self.system_state_file, 'r') as f:
                state = json.load(f)

            # Add to rollback points
            state["rollback_points"].append({
                "id": rollback_metadata["id"],
                "timestamp": rollback_metadata["timestamp"],
                "description": rollback_metadata["description"]
            })

            # Update last backup time
            state["last_backup"] = rollback_metadata["timestamp"]
            state["system_hash"] = rollback_metadata["system_hash_before"]

            with open(self.system_state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to update system state: {e}")

    def _log_rollback_operation(self, operation: str, metadata: Dict[str, Any]) -> None:
        """Log rollback operations for audit trail."""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "rollback_id": metadata.get("id"),
                "description": metadata.get("description"),
                "metadata": metadata
            }

            # Load existing log
            rollback_log = []
            if self.rollback_log.exists():
                with open(self.rollback_log, 'r') as f:
                    rollback_log = json.load(f)

            # Add new entry
            rollback_log.append(log_entry)

            # Keep only last 1000 entries
            if len(rollback_log) > 1000:
                rollback_log = rollback_log[-1000:]

            # Save log
            with open(self.rollback_log, 'w') as f:
                json.dump(rollback_log, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to log rollback operation: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status for safety monitoring."""
        try:
            # Load system state
            with open(self.system_state_file, 'r') as f:
                system_state = json.load(f)

            # Check emergency stop
            emergency_stop_file = self.safety_dir / "EMERGENCY_STOP"
            emergency_stop_active = emergency_stop_file.exists()

            # Get rollback points summary
            rollback_summary = self.list_rollback_points()

            # Current system health
            current_checks = self._run_system_checks()
            current_hash = self._calculate_system_hash()

            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "emergency_stop_active": emergency_stop_active,
                "system_hash": current_hash,
                "system_hash_changed": current_hash != system_state.get("system_hash"),
                "last_backup": system_state.get("last_backup"),
                "total_rollback_points": rollback_summary.get("total_count", 0),
                "system_checks": current_checks,
                "system_healthy": all(current_checks.values()),
                "safety_checks_enabled": system_state.get("safety_checks_enabled", True),
                "backups_dir_size_mb": self._calculate_backup_size(self.backups_dir)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


def main():
    """CLI interface for rollback manager."""
    import argparse

    parser = argparse.ArgumentParser(description="Friday AI Assistant Rollback Manager")
    parser.add_argument("command", choices=[
        "create", "list", "rollback", "cleanup", "status", "emergency-stop", "clear-stop"
    ], help="Command to execute")
    parser.add_argument("--description", help="Description for rollback point")
    parser.add_argument("--rollback-id", help="Rollback ID for rollback operation")
    parser.add_argument("--force", action="store_true", help="Force operation without safety checks")
    parser.add_argument("--days", type=int, help="Number of days for cleanup")
    parser.add_argument("--reason", help="Reason for emergency stop")
    parser.add_argument("--confirm", help="Confirmation string for dangerous operations")

    args = parser.parse_args()

    manager = RollbackManager()

    if args.command == "create":
        if not args.description:
            print("Error: --description required for create command")
            return 1

        result = manager.create_rollback_point(args.description)
        print(json.dumps(result, indent=2))

    elif args.command == "list":
        result = manager.list_rollback_points()
        print(json.dumps(result, indent=2))

    elif args.command == "rollback":
        if not args.rollback_id:
            print("Error: --rollback-id required for rollback command")
            return 1

        result = manager.execute_rollback(args.rollback_id, force=args.force)
        print(json.dumps(result, indent=2))

    elif args.command == "cleanup":
        result = manager.cleanup_old_rollbacks(args.days)
        print(json.dumps(result, indent=2))

    elif args.command == "status":
        result = manager.get_system_status()
        print(json.dumps(result, indent=2))

    elif args.command == "emergency-stop":
        if not args.reason:
            print("Error: --reason required for emergency-stop command")
            return 1

        result = manager.create_emergency_stop(args.reason)
        print(json.dumps(result, indent=2))

    elif args.command == "clear-stop":
        result = manager.clear_emergency_stop(args.confirm)
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    exit(main())