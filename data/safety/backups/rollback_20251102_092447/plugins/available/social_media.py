"""
Social Media Plugin for Friday AI Assistant
Generates social media drafts and manages content calendar (human approval required for posting).
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from core.logging import get_logger, initialize_logger


class SocialMediaPlugin:
    """Plugin for social media draft generation and content management."""

    def __init__(self):
        self.name = "social_media"
        self.description = "Social media draft generation and content calendar management"
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
        self.content_dir = Path("./data/social_content")
        self.drafts_dir = self.content_dir / "drafts"
        self.calendar_dir = self.content_dir / "calendar"
        self.assets_dir = self.content_dir / "assets"

        # Create directories
        for dir_path in [self.content_dir, self.drafts_dir, self.calendar_dir, self.assets_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Platform configurations
        self.platforms = {
            "twitter": {
                "max_length": 280,
                "supports_images": True,
                "supports_videos": True,
                "hashtag_limit": 2,
                "optimal_length": 71,  # Tweets around 71-100 chars get highest engagement
            },
            "linkedin": {
                "max_length": 3000,
                "supports_images": True,
                "supports_videos": True,
                "hashtag_limit": 5,
                "optimal_length": 150,  # LinkedIn posts around 150 chars get good engagement
            },
            "facebook": {
                "max_length": 63206,
                "supports_images": True,
                "supports_videos": True,
                "hashtag_limit": 3,
                "optimal_length": 80,  # Facebook posts around 80 chars get good engagement
            },
            "instagram": {
                "max_length": 2200,
                "supports_images": True,
                "supports_videos": True,
                "hashtag_limit": 30,
                "optimal_length": 125,  # Instagram captions around 125 chars get good engagement
            },
        }

    async def initialize(self) -> bool:
        """Initialize the social media plugin."""
        try:
            self.logger.info("Initializing social media plugin")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize social media plugin: {e}")
            return False

    def get_available_functions(self) -> List[str]:
        """Get list of available plugin functions."""
        return [
            "generate_post_draft",
            "create_content_calendar",
            "generate_hashtags",
            "optimize_content",
            "schedule_content",
            "analyze_trending_topics",
            "generate_thread",
            "create_campaign",
            "export_content_calendar",
            "validate_content",
            "get_content_suggestions",
            "generate_weekly_plan",
        ]

    def generate_post_draft(
        self, topic: str, platform: str, tone: str = "professional", include_hashtags: bool = True, call_to_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a social media post draft."""
        try:
            if platform not in self.platforms:
                return {"success": False, "error": f"Unsupported platform: {platform}"}

            platform_config = self.platforms[platform]

            # Generate content based on topic and tone
            content = self._generate_content(topic, tone, platform_config["optimal_length"])

            # Add hashtags if requested
            hashtags = []
            if include_hashtags:
                hashtags = self._generate_hashtags(topic, platform_config["hashtag_limit"])

            # Add call to action if provided
            if call_to_action:
                content += f"\n\n{call_to_action}"

            # Add hashtags to content
            if hashtags:
                content += f"\n\n{' '.join(hashtags)}"

            # Validate length
            if len(content) > platform_config["max_length"]:
                content = self._truncate_content(content, platform_config["max_length"])

            # Create draft object
            draft = {
                "id": self._generate_draft_id(),
                "platform": platform,
                "topic": topic,
                "content": content,
                "hashtags": hashtags,
                "tone": tone,
                "call_to_action": call_to_action,
                "character_count": len(content),
                "created_at": datetime.now().isoformat(),
                "status": "draft",
                "requires_approval": True,
            }

            # Save draft
            draft_file = self.drafts_dir / f"{draft['id']}_{platform}.json"
            with open(draft_file, "w", encoding="utf-8") as f:
                json.dump(draft, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Generated {platform} post draft for topic: {topic}")
            return {"success": True, "draft": draft, "file_path": str(draft_file)}

        except Exception as e:
            self.logger.error(f"Failed to generate post draft: {e}")
            return {"success": False, "error": str(e)}

    def create_content_calendar(
        self, start_date: str, days: int = 7, posts_per_day: int = 2, platforms: Optional[List[str]] = None, topics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a content calendar for specified period."""
        try:
            if platforms is None:
                platforms = ["twitter", "linkedin"]

            if topics is None:
                topics = ["AI and Technology", "Productivity Tips", "Industry Insights", "Friday AI Updates", "Automation Benefits"]

            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            calendar_data = []

            for day in range(days):
                current_date = start_dt + timedelta(days=day)

                for post_num in range(posts_per_day):
                    # Distribute posts across platforms
                    platform = platforms[post_num % len(platforms)]
                    topic = topics[(day * posts_per_day + post_num) % len(topics)]

                    # Calculate posting time (spread throughout the day)
                    hour_offset = (post_num * 12) % 24  # Space posts 12 hours apart
                    posting_time = current_date.replace(hour=9 + hour_offset % 12, minute=0, second=0)

                    # Generate draft for this slot
                    draft_result = self.generate_post_draft(topic=topic, platform=platform, tone="professional", include_hashtags=True)

                    if draft_result["success"]:
                        calendar_entry = {
                            "date": current_date.date().isoformat(),
                            "time": posting_time.time().isoformat(),
                            "platform": platform,
                            "topic": topic,
                            "draft_id": draft_result["draft"]["id"],
                            "content_preview": draft_result["draft"]["content"][:100] + "...",
                            "status": "scheduled",
                            "requires_approval": True,
                        }
                        calendar_data.append(calendar_entry)

            # Save calendar
            calendar_id = self._generate_calendar_id()
            calendar_file = self.calendar_dir / f"calendar_{calendar_id}.json"

            calendar_obj = {
                "id": calendar_id,
                "name": f"Content Calendar {start_dt.strftime('%Y-%m-%d')}",
                "start_date": start_date,
                "days": days,
                "posts_per_day": posts_per_day,
                "platforms": platforms,
                "topics": topics,
                "entries": calendar_data,
                "created_at": datetime.now().isoformat(),
                "total_posts": len(calendar_data),
            }

            with open(calendar_file, "w", encoding="utf-8") as f:
                json.dump(calendar_obj, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Created content calendar with {len(calendar_data)} posts")
            return {"success": True, "calendar": calendar_obj, "file_path": str(calendar_file)}

        except Exception as e:
            self.logger.error(f"Failed to create content calendar: {e}")
            return {"success": False, "error": str(e)}

    def generate_hashtags(self, topic: str, platform: str, count: int = 5) -> Dict[str, Any]:
        """Generate relevant hashtags for a topic and platform."""
        try:
            if platform not in self.platforms:
                return {"success": False, "error": f"Unsupported platform: {platform}"}

            max_hashtags = min(count, self.platforms[platform]["hashtag_limit"])
            hashtags = self._generate_hashtags(topic, max_hashtags)

            return {"success": True, "topic": topic, "platform": platform, "hashtags": hashtags, "count": len(hashtags)}

        except Exception as e:
            self.logger.error(f"Failed to generate hashtags: {e}")
            return {"success": False, "error": str(e)}

    def generate_thread(self, topic: str, platform: str = "twitter", thread_length: int = 5) -> Dict[str, Any]:
        """Generate a thread of connected posts."""
        try:
            if platform not in self.platforms:
                return {"success": False, "error": f"Unsupported platform: {platform}"}

            platform_config = self.platforms[platform]
            thread_posts = []

            # Generate thread opener
            opener_content = self._generate_thread_opener(topic, platform_config["optimal_length"])
            thread_posts.append({"sequence": 1, "content": opener_content, "type": "opener"})

            # Generate middle posts
            for i in range(2, thread_length):
                middle_content = self._generate_thread_middle(topic, i, platform_config["optimal_length"])
                thread_posts.append({"sequence": i, "content": middle_content, "type": "middle"})

            # Generate thread closer
            closer_content = self._generate_thread_closer(topic, platform_config["optimal_length"])
            thread_posts.append({"sequence": thread_length, "content": closer_content, "type": "closer"})

            # Create thread object
            thread = {
                "id": self._generate_thread_id(),
                "topic": topic,
                "platform": platform,
                "posts": thread_posts,
                "total_posts": len(thread_posts),
                "created_at": datetime.now().isoformat(),
                "status": "draft",
                "requires_approval": True,
            }

            # Save thread
            thread_file = self.drafts_dir / f"thread_{thread['id']}_{platform}.json"
            with open(thread_file, "w", encoding="utf-8") as f:
                json.dump(thread, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Generated {platform} thread with {len(thread_posts)} posts")
            return {"success": True, "thread": thread, "file_path": str(thread_file)}

        except Exception as e:
            self.logger.error(f"Failed to generate thread: {e}")
            return {"success": False, "error": str(e)}

    def export_content_calendar(self, calendar_id: str, format: str = "csv") -> Dict[str, Any]:
        """Export content calendar to file."""
        try:
            calendar_file = self.calendar_dir / f"calendar_{calendar_id}.json"

            if not calendar_file.exists():
                return {"success": False, "error": f"Calendar not found: {calendar_id}"}

            with open(calendar_file, "r", encoding="utf-8") as f:
                calendar_data = json.load(f)

            export_path = self.content_dir / f"calendar_{calendar_id}.{format}"

            if format.lower() == "csv":
                df = pd.DataFrame(calendar_data["entries"])
                df.to_csv(export_path, index=False)
            elif format.lower() == "json":
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(calendar_data, f, indent=2, ensure_ascii=False)
            else:
                return {"success": False, "error": f"Unsupported format: {format}"}

            self.logger.info(f"Exported calendar to {export_path}")
            return {"success": True, "calendar_id": calendar_id, "export_path": str(export_path), "format": format}

        except Exception as e:
            self.logger.error(f"Failed to export calendar: {e}")
            return {"success": False, "error": str(e)}

    def generate_weekly_plan(self) -> Dict[str, Any]:
        """Generate a comprehensive weekly social media plan."""
        try:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # Create main content calendar
            calendar_result = self.create_content_calendar(
                start_date=start_date.isoformat(),
                days=7,
                posts_per_day=3,
                platforms=["twitter", "linkedin", "facebook"],
                topics=[
                    "Monday Motivation: AI Productivity",
                    "Tech Tuesday: Automation Tips",
                    "Wednesday Wisdom: Industry Insights",
                    "Thursday Thoughts: Friday AI Features",
                    "Friday Focus: Week Recap",
                    "Weekend Wrap: Future Planning",
                    "Sunday Special: Community Highlights",
                ],
            )

            if not calendar_result["success"]:
                return calendar_result

            # Generate some threads for variety
            thread_topics = ["The Future of AI Assistants", "Building Better Workflows", "Automation Best Practices"]

            threads = []
            for topic in thread_topics:
                thread_result = self.generate_thread(topic, "twitter", 4)
                if thread_result["success"]:
                    threads.append(thread_result["thread"])

            # Create comprehensive plan
            weekly_plan = {
                "id": self._generate_plan_id(),
                "week_start": start_date.isoformat(),
                "calendar": calendar_result["calendar"],
                "threads": threads,
                "total_posts": calendar_result["calendar"]["total_posts"],
                "total_threads": len(threads),
                "platforms_covered": ["twitter", "linkedin", "facebook"],
                "created_at": datetime.now().isoformat(),
                "status": "draft",
                "requires_approval": True,
            }

            # Save weekly plan
            plan_file = self.content_dir / f"weekly_plan_{weekly_plan['id']}.json"
            with open(plan_file, "w", encoding="utf-8") as f:
                json.dump(weekly_plan, f, indent=2, ensure_ascii=False)

            self.logger.info("Generated comprehensive weekly social media plan")
            return {"success": True, "plan": weekly_plan, "file_path": str(plan_file)}

        except Exception as e:
            self.logger.error(f"Failed to generate weekly plan: {e}")
            return {"success": False, "error": str(e)}

    # Helper methods
    def _generate_content(self, topic: str, tone: str, target_length: int) -> str:
        """Generate content for a social media post."""
        # This is a simplified content generation
        # In a real implementation, this would use an LLM or content generation API

        content_templates = {
            "professional": [
                f"Exploring {topic} and its impact on modern workflows. Key insights: innovation drives efficiency, and smart automation saves valuable time.",
                f"Today's focus: {topic}. The intersection of technology and productivity continues to reshape how we work and create value.",
                f"Diving deep into {topic}. When we leverage the right tools, we unlock potential that transforms both individual and team performance.",
            ],
            "casual": [
                f"Just discovered something cool about {topic}! 🚀 The possibilities are endless when you start thinking differently.",
                f"Mind blown by {topic} today! 🤯 It's amazing how much potential there is to improve our daily workflows.",
                f"Quick thought on {topic}: sometimes the best solutions are simpler than we think! ✨",
            ],
            "educational": [
                f"Let's break down {topic}: Understanding the fundamentals helps us make better decisions and implement more effective solutions.",
                f"Educational moment: {topic} explained. Knowledge sharing accelerates innovation and helps everyone level up their game.",
                f"Today's learning: {topic}. The more we understand these concepts, the better equipped we are for future challenges.",
            ],
        }

        templates = content_templates.get(tone, content_templates["professional"])
        content = templates[hash(topic) % len(templates)]

        # Adjust length to target
        if len(content) > target_length:
            content = content[: target_length - 3] + "..."

        return content

    def _generate_hashtags(self, topic: str, limit: int) -> List[str]:
        """Generate relevant hashtags for a topic."""
        # Simplified hashtag generation
        base_hashtags = ["#AI", "#Automation", "#Productivity", "#Tech", "#Innovation"]

        topic_words = re.findall(r"\b\w+\b", topic.lower())
        topic_hashtags = [f"#{word.capitalize()}" for word in topic_words if len(word) > 3]

        all_hashtags = base_hashtags + topic_hashtags
        return list(dict.fromkeys(all_hashtags))[:limit]  # Remove duplicates and limit

    def _generate_thread_opener(self, topic: str, target_length: int) -> str:
        """Generate the opening post of a thread."""
        opener = f"🧵 Thread: Let's explore {topic} and why it matters for the future of work. Here's what you need to know... (1/n)"
        return opener[:target_length] if len(opener) > target_length else opener

    def _generate_thread_middle(self, topic: str, sequence: int, target_length: int) -> str:
        """Generate a middle post in a thread."""
        middle = f"({sequence}/n) Key insight about {topic}: The intersection of human creativity and machine efficiency creates unprecedented opportunities for innovation."
        return middle[:target_length] if len(middle) > target_length else middle

    def _generate_thread_closer(self, topic: str, target_length: int) -> str:
        """Generate the closing post of a thread."""
        closer = f"That's a wrap on {topic}! What are your thoughts? How are you leveraging these concepts in your work? Let's discuss! 👇"
        return closer[:target_length] if len(closer) > target_length else closer

    def _truncate_content(self, content: str, max_length: int) -> str:
        """Truncate content to fit platform limits."""
        if len(content) <= max_length:
            return content
        return content[: max_length - 3] + "..."

    def _generate_draft_id(self) -> str:
        """Generate a unique draft ID."""
        return f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(datetime.now()) % 10000:04d}"

    def _generate_calendar_id(self) -> str:
        """Generate a unique calendar ID."""
        return f"cal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _generate_thread_id(self) -> str:
        """Generate a unique thread ID."""
        return f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(datetime.now()) % 1000:03d}"

    def _generate_plan_id(self) -> str:
        """Generate a unique plan ID."""
        return f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    async def cleanup(self):
        """Clean up resources."""
        self.logger.info("Social media plugin cleanup completed")


# Plugin instance - commented out to avoid logger initialization issues during import
# plugin = SocialMediaPlugin()
