"""
Content Scheduler Plugin for Friday AI Assistant
Manages content scheduling, automation pipeline, and approval workflows.
"""

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import schedule

from core.logging import get_logger, initialize_logger


class ContentSchedulerPlugin:
    """Plugin for content scheduling and automation pipeline."""

    def __init__(self):
        self.name = "content_scheduler"
        self.description = "Content scheduling and automation pipeline"
        self.version = "1.0.0"

        # Graceful logger initialization with fallback
        try:
            self.logger = get_logger()
        except RuntimeError:
            # Logger not initialized, use lazy initialization
            try:
                # Try to initialize with minimal config for testing
                initialize_logger(level="INFO", console=True, file=False)
                self.logger = get_logger()
            except Exception:
                # Ultimate fallback - create a basic logger
                import logging

                self.logger = logging.getLogger(self.name)
                self.logger.setLevel(logging.INFO)
                if not self.logger.handlers:
                    handler = logging.StreamHandler()
                    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                    handler.setFormatter(formatter)
                    self.logger.addHandler(handler)

        # Directory structure
        self.content_dir = Path("./data/content_pipeline")
        self.queue_dir = self.content_dir / "queue"
        self.approved_dir = self.content_dir / "approved"
        self.published_dir = self.content_dir / "published"
        self.rejected_dir = self.content_dir / "rejected"
        self.schedules_dir = self.content_dir / "schedules"

        # Create directories
        for dir_path in [self.content_dir, self.queue_dir, self.approved_dir, self.published_dir, self.rejected_dir, self.schedules_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Scheduler state
        self.scheduler_running = False
        self.scheduler_thread = None

        # Content approval workflow
        self.approval_workflow = {
            "draft": {"next": ["pending_approval"], "actions": ["submit_for_approval"]},
            "pending_approval": {"next": ["approved", "rejected"], "actions": ["approve", "reject"]},
            "approved": {"next": ["scheduled"], "actions": ["schedule"]},
            "scheduled": {"next": ["published"], "actions": ["publish"]},
            "published": {"next": [], "actions": ["archive"]},
            "rejected": {"next": ["draft"], "actions": ["revise"]},
        }

    async def initialize(self) -> bool:
        """Initialize the content scheduler plugin."""
        try:
            self.logger.info("Initializing content scheduler plugin")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize content scheduler plugin: {e}")
            return False

    def get_available_functions(self) -> List[str]:
        """Get list of available plugin functions."""
        return [
            "submit_content_for_approval",
            "approve_content",
            "reject_content",
            "schedule_content",
            "create_publishing_schedule",
            "start_scheduler",
            "stop_scheduler",
            "get_pending_approvals",
            "get_scheduled_content",
            "bulk_schedule_content",
            "create_content_workflow",
            "monitor_pipeline_status",
            "export_pipeline_report",
            "set_approval_rules",
            "create_automation_rule",
        ]

    def submit_content_for_approval(
        self, content_id: str, content_type: str, platform: str, content_data: Dict[str, Any], priority: str = "normal", requester: str = "system"
    ) -> Dict[str, Any]:
        """Submit content for human approval."""
        try:
            submission = {
                "id": content_id,
                "type": content_type,
                "platform": platform,
                "data": content_data,
                "priority": priority,
                "requester": requester,
                "status": "pending_approval",
                "submitted_at": datetime.now().isoformat(),
                "approval_deadline": (datetime.now() + timedelta(hours=24)).isoformat(),
                "requires_human_approval": True,
                "approval_notes": "",
                "reviewer": None,
                "reviewed_at": None,
            }

            # Save to queue
            queue_file = self.queue_dir / f"{content_id}_approval.json"
            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump(submission, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Content {content_id} submitted for approval")
            return {"success": True, "submission": submission, "queue_file": str(queue_file)}

        except Exception as e:
            self.logger.error(f"Failed to submit content for approval: {e}")
            return {"success": False, "error": str(e)}

    def approve_content(self, content_id: str, reviewer: str, notes: Optional[str] = None, schedule_immediately: bool = False) -> Dict[str, Any]:
        """Approve content for publishing."""
        try:
            queue_file = self.queue_dir / f"{content_id}_approval.json"

            if not queue_file.exists():
                return {"success": False, "error": f"Content {content_id} not found in approval queue"}

            # Load submission
            with open(queue_file, "r", encoding="utf-8") as f:
                submission = json.load(f)

            # Update approval status
            submission["status"] = "approved"
            submission["reviewer"] = reviewer
            submission["reviewed_at"] = datetime.now().isoformat()
            submission["approval_notes"] = notes or ""

            # Move to approved directory
            approved_file = self.approved_dir / f"{content_id}_approved.json"
            with open(approved_file, "w", encoding="utf-8") as f:
                json.dump(submission, f, indent=2, ensure_ascii=False)

            # Remove from queue
            queue_file.unlink()

            # Schedule immediately if requested
            if schedule_immediately:
                self.schedule_content(content_id, datetime.now() + timedelta(minutes=5), submission["platform"])  # 5 minutes from now

            self.logger.info(f"Content {content_id} approved by {reviewer}")
            return {
                "success": True,
                "content_id": content_id,
                "reviewer": reviewer,
                "approved_file": str(approved_file),
                "scheduled_immediately": schedule_immediately,
            }

        except Exception as e:
            self.logger.error(f"Failed to approve content {content_id}: {e}")
            return {"success": False, "error": str(e)}

    def reject_content(self, content_id: str, reviewer: str, reason: str, suggestions: Optional[str] = None) -> Dict[str, Any]:
        """Reject content with feedback."""
        try:
            queue_file = self.queue_dir / f"{content_id}_approval.json"

            if not queue_file.exists():
                return {"success": False, "error": f"Content {content_id} not found in approval queue"}

            # Load submission
            with open(queue_file, "r", encoding="utf-8") as f:
                submission = json.load(f)

            # Update rejection status
            submission["status"] = "rejected"
            submission["reviewer"] = reviewer
            submission["reviewed_at"] = datetime.now().isoformat()
            submission["rejection_reason"] = reason
            submission["suggestions"] = suggestions or ""

            # Move to rejected directory
            rejected_file = self.rejected_dir / f"{content_id}_rejected.json"
            with open(rejected_file, "w", encoding="utf-8") as f:
                json.dump(submission, f, indent=2, ensure_ascii=False)

            # Remove from queue
            queue_file.unlink()

            self.logger.info(f"Content {content_id} rejected by {reviewer}: {reason}")
            return {"success": True, "content_id": content_id, "reviewer": reviewer, "reason": reason, "rejected_file": str(rejected_file)}

        except Exception as e:
            self.logger.error(f"Failed to reject content {content_id}: {e}")
            return {"success": False, "error": str(e)}

    def schedule_content(self, content_id: str, publish_time: Union[str, datetime], platform: str, timezone: str = "UTC") -> Dict[str, Any]:
        """Schedule approved content for publishing."""
        try:
            # Find approved content
            approved_file = self.approved_dir / f"{content_id}_approved.json"

            if not approved_file.exists():
                return {"success": False, "error": f"Approved content {content_id} not found"}

            # Load approved content
            with open(approved_file, "r", encoding="utf-8") as f:
                content = json.load(f)

            # Parse publish time
            if isinstance(publish_time, str):
                publish_datetime = datetime.fromisoformat(publish_time.replace("Z", "+00:00"))
            else:
                publish_datetime = publish_time

            # Create schedule entry
            schedule_entry = {
                "content_id": content_id,
                "platform": platform,
                "publish_time": publish_datetime.isoformat(),
                "timezone": timezone,
                "status": "scheduled",
                "content": content,
                "scheduled_at": datetime.now().isoformat(),
                "published_at": None,
                "publish_attempts": 0,
                "last_attempt": None,
                "error_message": None,
            }

            # Save schedule
            schedule_file = self.schedules_dir / f"{content_id}_schedule.json"
            with open(schedule_file, "w", encoding="utf-8") as f:
                json.dump(schedule_entry, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Content {content_id} scheduled for {publish_datetime} on {platform}")
            return {
                "success": True,
                "content_id": content_id,
                "platform": platform,
                "publish_time": publish_datetime.isoformat(),
                "schedule_file": str(schedule_file),
            }

        except Exception as e:
            self.logger.error(f"Failed to schedule content {content_id}: {e}")
            return {"success": False, "error": str(e)}

    def create_publishing_schedule(
        self, content_items: List[Dict[str, Any]], start_time: Union[str, datetime], interval_hours: int = 4, platforms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a publishing schedule for multiple content items."""
        try:
            if platforms is None:
                platforms = ["twitter", "linkedin"]

            if isinstance(start_time, str):
                start_datetime = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            else:
                start_datetime = start_time

            scheduled_items = []
            current_time = start_datetime

            for i, content_item in enumerate(content_items):
                # Distribute across platforms
                platform = platforms[i % len(platforms)]

                schedule_result = self.schedule_content(content_item["id"], current_time, platform)

                if schedule_result["success"]:
                    scheduled_items.append(
                        {
                            "content_id": content_item["id"],
                            "platform": platform,
                            "publish_time": current_time.isoformat(),
                            "schedule_result": schedule_result,
                        }
                    )

                # Increment time for next item
                current_time += timedelta(hours=interval_hours)

            self.logger.info(f"Created publishing schedule for {len(scheduled_items)} items")
            return {
                "success": True,
                "scheduled_items": scheduled_items,
                "total_scheduled": len(scheduled_items),
                "schedule_span": f"{start_datetime.isoformat()} to {current_time.isoformat()}",
            }

        except Exception as e:
            self.logger.error(f"Failed to create publishing schedule: {e}")
            return {"success": False, "error": str(e)}

    def start_scheduler(self) -> Dict[str, Any]:
        """Start the automated content scheduler."""
        try:
            if self.scheduler_running:
                return {"success": False, "error": "Scheduler already running"}

            def scheduler_worker():
                """Background scheduler worker."""
                schedule.every(1).minutes.do(self._check_scheduled_content)
                schedule.every(10).minutes.do(self._cleanup_old_files)

                while self.scheduler_running:
                    schedule.run_pending()
                    time.sleep(30)  # Check every 30 seconds

            self.scheduler_running = True
            self.scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
            self.scheduler_thread.start()

            self.logger.info("Content scheduler started")
            return {"success": True, "message": "Content scheduler started", "thread_id": self.scheduler_thread.ident}

        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
            return {"success": False, "error": str(e)}

    def stop_scheduler(self) -> Dict[str, Any]:
        """Stop the automated content scheduler."""
        try:
            if not self.scheduler_running:
                return {"success": False, "error": "Scheduler not running"}

            self.scheduler_running = False
            schedule.clear()

            if self.scheduler_thread:
                self.scheduler_thread.join(timeout=5)

            self.logger.info("Content scheduler stopped")
            return {"success": True, "message": "Content scheduler stopped"}

        except Exception as e:
            self.logger.error(f"Failed to stop scheduler: {e}")
            return {"success": False, "error": str(e)}

    def get_pending_approvals(self) -> Dict[str, Any]:
        """Get list of content pending approval."""
        try:
            pending_files = list(self.queue_dir.glob("*_approval.json"))
            pending_items = []

            for file_path in pending_files:
                with open(file_path, "r", encoding="utf-8") as f:
                    item = json.load(f)
                    pending_items.append(item)

            # Sort by priority and submission time
            priority_order = {"high": 0, "normal": 1, "low": 2}
            pending_items.sort(key=lambda x: (priority_order.get(x.get("priority", "normal"), 1), x.get("submitted_at", "")))

            return {"success": True, "pending_items": pending_items, "count": len(pending_items)}

        except Exception as e:
            self.logger.error(f"Failed to get pending approvals: {e}")
            return {"success": False, "error": str(e)}

    def get_scheduled_content(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Get scheduled content for the next N days."""
        try:
            schedule_files = list(self.schedules_dir.glob("*_schedule.json"))
            scheduled_items = []

            cutoff_time = datetime.now() + timedelta(days=days_ahead)

            for file_path in schedule_files:
                with open(file_path, "r", encoding="utf-8") as f:
                    item = json.load(f)

                    # Only include items scheduled within the timeframe
                    publish_time = datetime.fromisoformat(item["publish_time"].replace("Z", "+00:00"))
                    if publish_time <= cutoff_time and item["status"] == "scheduled":
                        scheduled_items.append(item)

            # Sort by publish time
            scheduled_items.sort(key=lambda x: x["publish_time"])

            return {"success": True, "scheduled_items": scheduled_items, "count": len(scheduled_items), "timeframe_days": days_ahead}

        except Exception as e:
            self.logger.error(f"Failed to get scheduled content: {e}")
            return {"success": False, "error": str(e)}

    def _check_scheduled_content(self):
        """Check for content ready to be published."""
        try:
            now = datetime.now()
            schedule_files = list(self.schedules_dir.glob("*_schedule.json"))

            for file_path in schedule_files:
                with open(file_path, "r", encoding="utf-8") as f:
                    schedule_entry = json.load(f)

                if schedule_entry["status"] != "scheduled":
                    continue

                publish_time = datetime.fromisoformat(schedule_entry["publish_time"].replace("Z", "+00:00"))

                # Check if it's time to publish
                if now >= publish_time:
                    self._attempt_publish(schedule_entry, file_path)

        except Exception as e:
            self.logger.error(f"Error checking scheduled content: {e}")

    def _attempt_publish(self, schedule_entry: Dict[str, Any], file_path: Path):
        """Attempt to publish scheduled content."""
        try:
            # In a real implementation, this would integrate with social media APIs
            # For now, we'll simulate publishing

            content_id = schedule_entry["content_id"]
            platform = schedule_entry["platform"]

            # Simulate publishing (replace with actual API calls)
            publish_success = True  # Would be result of actual API call

            if publish_success:
                # Mark as published
                schedule_entry["status"] = "published"
                schedule_entry["published_at"] = datetime.now().isoformat()

                # Move to published directory
                published_file = self.published_dir / f"{content_id}_published.json"
                with open(published_file, "w", encoding="utf-8") as f:
                    json.dump(schedule_entry, f, indent=2, ensure_ascii=False)

                # Remove from schedules
                file_path.unlink()

                self.logger.info(f"Successfully published content {content_id} to {platform}")

            else:
                # Handle publish failure
                schedule_entry["publish_attempts"] += 1
                schedule_entry["last_attempt"] = datetime.now().isoformat()
                schedule_entry["error_message"] = "Publishing failed"

                # Reschedule for 1 hour later if under 3 attempts
                if schedule_entry["publish_attempts"] < 3:
                    retry_time = datetime.now() + timedelta(hours=1)
                    schedule_entry["publish_time"] = retry_time.isoformat()

                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(schedule_entry, f, indent=2, ensure_ascii=False)

                    self.logger.warning(f"Rescheduled content {content_id} for retry")
                else:
                    schedule_entry["status"] = "failed"
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(schedule_entry, f, indent=2, ensure_ascii=False)

                    self.logger.error(f"Content {content_id} failed to publish after 3 attempts")

        except Exception as e:
            self.logger.error(f"Error attempting to publish content: {e}")

    def _cleanup_old_files(self):
        """Clean up old published and rejected files."""
        try:
            cutoff_time = datetime.now() - timedelta(days=30)

            for directory in [self.published_dir, self.rejected_dir]:
                for file_path in directory.glob("*.json"):
                    # Check file modification time
                    if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_time:
                        file_path.unlink()

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    async def cleanup(self):
        """Clean up resources."""
        self.stop_scheduler()
        self.logger.info("Content scheduler plugin cleanup completed")


# Plugin instance - commented out to avoid logger initialization issues during import
# plugin = ContentSchedulerPlugin()
