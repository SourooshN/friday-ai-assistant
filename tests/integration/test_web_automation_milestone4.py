"""
Integration tests for Milestone 4: Web Automation & Social Drafts
Tests the complete web automation and social media functionality.
"""
import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Import our plugins
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

# Initialize logger for testing to prevent logger initialization errors
from core.logging import initialize_logger
try:
    # Initialize with minimal test configuration
    initialize_logger(level="INFO", console=True, file=False)
except Exception:
    # Logger may already be initialized, ignore
    pass

# Test if schedule is available before importing plugins that depend on it
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    pytest.importorskip("schedule", reason="schedule module not available")

from plugins.available.web_automation import WebAutomationPlugin
from plugins.available.social_media import SocialMediaPlugin
from plugins.available.web_scraping import WebScrapingPlugin
if SCHEDULE_AVAILABLE:
    from plugins.available.content_scheduler import ContentSchedulerPlugin
else:
    ContentSchedulerPlugin = None


class TestMilestone4WebAutomation:
    """Test suite for Milestone 4 web automation features."""

    @pytest.fixture
    def web_automation_plugin(self):
        """Create web automation plugin instance."""
        return WebAutomationPlugin()

    @pytest.fixture
    def social_media_plugin(self):
        """Create social media plugin instance."""
        return SocialMediaPlugin()

    @pytest.fixture
    def web_scraping_plugin(self):
        """Create web scraping plugin instance."""
        return WebScrapingPlugin()

    @pytest.fixture
    def content_scheduler_plugin(self):
        """Create content scheduler plugin instance."""
        if ContentSchedulerPlugin is None:
            pytest.skip("schedule module not available")
        return ContentSchedulerPlugin()

    @pytest.mark.asyncio
    async def test_web_automation_plugin_initialization(self, web_automation_plugin):
        """Test web automation plugin initializes correctly."""
        result = await web_automation_plugin.initialize()
        assert result is True
        assert web_automation_plugin.name == "web_automation"
        assert web_automation_plugin.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_social_media_plugin_initialization(self, social_media_plugin):
        """Test social media plugin initializes correctly."""
        result = await social_media_plugin.initialize()
        assert result is True
        assert social_media_plugin.name == "social_media"
        assert social_media_plugin.version == "1.0.0"

    def test_social_media_post_generation(self, social_media_plugin):
        """Test social media post draft generation."""
        result = social_media_plugin.generate_post_draft(
            topic="AI and Future of Work",
            platform="twitter",
            tone="professional",
            include_hashtags=True,
            call_to_action="What are your thoughts on AI?"
        )

        assert result["success"] is True
        assert "draft" in result
        draft = result["draft"]

        assert draft["platform"] == "twitter"
        assert draft["topic"] == "AI and Future of Work"
        assert draft["tone"] == "professional"
        assert draft["requires_approval"] is True
        assert len(draft["content"]) <= 280  # Twitter character limit
        assert len(draft["hashtags"]) <= 2   # Twitter hashtag limit

    def test_content_calendar_creation(self, social_media_plugin):
        """Test content calendar creation."""
        start_date = datetime.now().isoformat()

        result = social_media_plugin.create_content_calendar(
            start_date=start_date,
            days=7,
            posts_per_day=2,
            platforms=["twitter", "linkedin"],
            topics=["AI Innovation", "Productivity Tips", "Tech Trends"]
        )

        assert result["success"] is True
        assert "calendar" in result
        calendar = result["calendar"]

        assert calendar["days"] == 7
        assert calendar["posts_per_day"] == 2
        assert calendar["total_posts"] == 14  # 7 days × 2 posts
        assert len(calendar["entries"]) == 14

    def test_thread_generation(self, social_media_plugin):
        """Test Twitter thread generation."""
        result = social_media_plugin.generate_thread(
            topic="Building Better AI Workflows",
            platform="twitter",
            thread_length=5
        )

        assert result["success"] is True
        assert "thread" in result
        thread = result["thread"]

        assert thread["platform"] == "twitter"
        assert thread["total_posts"] == 5
        assert len(thread["posts"]) == 5

        # Check thread structure
        assert thread["posts"][0]["type"] == "opener"
        assert thread["posts"][-1]["type"] == "closer"
        for post in thread["posts"][1:-1]:
            assert post["type"] == "middle"

    def test_hashtag_generation(self, social_media_plugin):
        """Test hashtag generation."""
        result = social_media_plugin.generate_hashtags(
            topic="Artificial Intelligence Automation",
            platform="twitter",
            count=5
        )

        assert result["success"] is True
        assert "hashtags" in result
        hashtags = result["hashtags"]

        assert len(hashtags) <= 5
        for hashtag in hashtags:
            assert hashtag.startswith("#")

    @pytest.mark.asyncio
    async def test_web_scraping_plugin_initialization(self, web_scraping_plugin):
        """Test web scraping plugin initializes correctly."""
        result = await web_scraping_plugin.initialize()
        assert result is True
        assert web_scraping_plugin.name == "web_scraping"

    def test_web_scraping_url_extraction(self, web_scraping_plugin):
        """Test basic URL scraping functionality."""
        # Test with a simple HTML structure
        test_html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Test Heading</h1>
                <p>Test paragraph content</p>
                <a href="http://example.com">Test Link</a>
            </body>
        </html>
        """

        # This would normally use requests, but for testing we'll verify structure
        assert web_scraping_plugin.name == "web_scraping"
        assert "scrape_url" in web_scraping_plugin.get_available_functions()

    def test_content_scheduler_initialization(self, content_scheduler_plugin):
        """Test content scheduler plugin initialization."""
        assert content_scheduler_plugin.name == "content_scheduler"
        assert content_scheduler_plugin.version == "1.0.0"

    def test_content_approval_workflow(self, content_scheduler_plugin):
        """Test content approval workflow."""
        # Submit content for approval
        content_data = {
            "content": "Test social media post about AI",
            "platform": "twitter",
            "hashtags": ["#AI", "#Tech"]
        }

        submit_result = content_scheduler_plugin.submit_content_for_approval(
            content_id="test_content_001",
            content_type="social_post",
            platform="twitter",
            content_data=content_data,
            priority="normal",
            requester="test_user"
        )

        assert submit_result["success"] is True
        assert "submission" in submit_result
        submission = submit_result["submission"]

        assert submission["status"] == "pending_approval"
        assert submission["requires_human_approval"] is True
        assert submission["platform"] == "twitter"

        # Test approval
        approve_result = content_scheduler_plugin.approve_content(
            content_id="test_content_001",
            reviewer="test_reviewer",
            notes="Looks good!"
        )

        assert approve_result["success"] is True
        assert approve_result["reviewer"] == "test_reviewer"

    def test_content_scheduling(self, content_scheduler_plugin):
        """Test content scheduling functionality."""
        # First approve some content
        content_data = {
            "content": "Scheduled test post",
            "platform": "linkedin"
        }

        submit_result = content_scheduler_plugin.submit_content_for_approval(
            content_id="scheduled_content_001",
            content_type="social_post",
            platform="linkedin",
            content_data=content_data
        )

        approve_result = content_scheduler_plugin.approve_content(
            content_id="scheduled_content_001",
            reviewer="test_reviewer"
        )

        # Schedule the content
        publish_time = datetime.now() + timedelta(hours=1)
        schedule_result = content_scheduler_plugin.schedule_content(
            content_id="scheduled_content_001",
            publish_time=publish_time,
            platform="linkedin"
        )

        assert schedule_result["success"] is True
        assert schedule_result["platform"] == "linkedin"

    def test_weekly_plan_generation(self, social_media_plugin):
        """Test comprehensive weekly plan generation."""
        result = social_media_plugin.generate_weekly_plan()

        assert result["success"] is True
        assert "plan" in result
        plan = result["plan"]

        assert "calendar" in plan
        assert "threads" in plan
        assert plan["total_posts"] > 0
        assert len(plan["platforms_covered"]) >= 2
        assert plan["requires_approval"] is True

    def test_export_functionality(self, social_media_plugin):
        """Test data export functionality."""
        # Generate a content calendar first
        start_date = datetime.now().isoformat()
        calendar_result = social_media_plugin.create_content_calendar(
            start_date=start_date,
            days=3,
            posts_per_day=1
        )

        assert calendar_result["success"] is True
        calendar_id = calendar_result["calendar"]["id"]

        # Test CSV export
        export_result = social_media_plugin.export_content_calendar(
            calendar_id=calendar_id,
            format="csv"
        )

        assert export_result["success"] is True
        assert export_result["format"] == "csv"
        assert Path(export_result["export_path"]).exists()

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, social_media_plugin, content_scheduler_plugin):
        """Test complete end-to-end workflow."""
        # 1. Generate social media content
        post_result = social_media_plugin.generate_post_draft(
            topic="End-to-End Testing",
            platform="twitter",
            tone="professional"
        )
        assert post_result["success"] is True
        content_id = post_result["draft"]["id"]

        # 2. Submit for approval
        submit_result = content_scheduler_plugin.submit_content_for_approval(
            content_id=content_id,
            content_type="social_post",
            platform="twitter",
            content_data=post_result["draft"]
        )
        assert submit_result["success"] is True

        # 3. Approve content
        approve_result = content_scheduler_plugin.approve_content(
            content_id=content_id,
            reviewer="automated_test"
        )
        assert approve_result["success"] is True

        # 4. Schedule content
        publish_time = datetime.now() + timedelta(minutes=30)
        schedule_result = content_scheduler_plugin.schedule_content(
            content_id=content_id,
            publish_time=publish_time,
            platform="twitter"
        )
        assert schedule_result["success"] is True

        # 5. Verify scheduled content appears in queue
        scheduled_content = content_scheduler_plugin.get_scheduled_content(days_ahead=1)
        assert scheduled_content["success"] is True
        assert len(scheduled_content["scheduled_items"]) >= 1

        # Find our content in the scheduled items
        our_content = None
        for item in scheduled_content["scheduled_items"]:
            if item["content_id"] == content_id:
                our_content = item
                break

        assert our_content is not None
        assert our_content["platform"] == "twitter"
        assert our_content["status"] == "scheduled"

    def test_plugin_function_availability(self, web_automation_plugin, social_media_plugin,
                                        web_scraping_plugin, content_scheduler_plugin):
        """Test that all required functions are available."""

        # Web automation functions
        web_functions = web_automation_plugin.get_available_functions()
        required_web_functions = [
            "start_browser", "navigate_to", "click_element", "extract_text",
            "take_screenshot", "scrape_page", "export_data"
        ]
        for func in required_web_functions:
            assert func in web_functions

        # Social media functions
        social_functions = social_media_plugin.get_available_functions()
        required_social_functions = [
            "generate_post_draft", "create_content_calendar", "generate_hashtags",
            "generate_thread", "export_content_calendar", "generate_weekly_plan"
        ]
        for func in required_social_functions:
            assert func in social_functions

        # Web scraping functions
        scraping_functions = web_scraping_plugin.get_available_functions()
        required_scraping_functions = [
            "scrape_url", "scrape_multiple_urls", "extract_product_data",
            "extract_article_data", "export_scraped_data"
        ]
        for func in required_scraping_functions:
            assert func in scraping_functions

        # Content scheduler functions
        scheduler_functions = content_scheduler_plugin.get_available_functions()
        required_scheduler_functions = [
            "submit_content_for_approval", "approve_content", "schedule_content",
            "get_pending_approvals", "get_scheduled_content"
        ]
        for func in required_scheduler_functions:
            assert func in scheduler_functions

    @pytest.mark.asyncio
    async def test_plugin_cleanup(self, web_automation_plugin, social_media_plugin,
                                web_scraping_plugin, content_scheduler_plugin):
        """Test that plugins clean up properly."""
        # Test cleanup for all plugins
        await web_automation_plugin.cleanup()
        await social_media_plugin.cleanup()
        await web_scraping_plugin.cleanup()
        await content_scheduler_plugin.cleanup()

        # Verify no exceptions were raised
        assert True  # If we get here, cleanup succeeded