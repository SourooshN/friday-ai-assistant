"""
Web Automation Plugin for Friday AI Assistant
Provides browser control, web scraping, and automated web interactions.
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import csv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import requests
from bs4 import BeautifulSoup
import pandas as pd

from core.logging import get_logger, initialize_logger


class WebAutomationPlugin:
    """Plugin for web automation, scraping, and browser control."""

    def __init__(self):
        self.name = "web_automation"
        self.description = "Web automation, scraping, and browser control"
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
                    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                    handler.setFormatter(formatter)
                    self.logger.addHandler(handler)
        self.driver = None
        self.exports_dir = Path("./data/exports")
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """Initialize the web automation plugin."""
        try:
            self.logger.info("Initializing web automation plugin")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize web automation plugin: {e}")
            return False

    def get_available_functions(self) -> List[str]:
        """Get list of available plugin functions."""
        return [
            "start_browser",
            "close_browser",
            "navigate_to",
            "click_element",
            "type_text",
            "scroll_page",
            "take_screenshot",
            "extract_text",
            "extract_links",
            "scrape_page",
            "download_file",
            "fill_form",
            "wait_for_element",
            "execute_script",
            "export_data",
            "get_page_info",
            "search_google",
            "monitor_element_changes"
        ]

    def start_browser(self, headless: bool = False, user_data_dir: Optional[str] = None) -> Dict[str, Any]:
        """Start a browser instance."""
        try:
            if self.driver:
                return {"success": False, "error": "Browser already running"}

            chrome_options = Options()

            if headless:
                chrome_options.add_argument("--headless")

            if user_data_dir:
                chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

            # Security and performance options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)

            self.logger.info("Browser started successfully")
            return {
                "success": True,
                "message": "Browser started",
                "headless": headless,
                "session_id": self.driver.session_id
            }

        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            return {"success": False, "error": str(e)}

    def close_browser(self) -> Dict[str, Any]:
        """Close the browser instance."""
        try:
            if not self.driver:
                return {"success": False, "error": "No browser running"}

            self.driver.quit()
            self.driver = None

            self.logger.info("Browser closed successfully")
            return {"success": True, "message": "Browser closed"}

        except Exception as e:
            self.logger.error(f"Failed to close browser: {e}")
            return {"success": False, "error": str(e)}

    def navigate_to(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL."""
        try:
            if not self.driver:
                return {"success": False, "error": "No browser running"}

            self.driver.get(url)

            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )

            current_url = self.driver.current_url
            title = self.driver.title

            self.logger.info(f"Navigated to: {current_url}")
            return {
                "success": True,
                "url": current_url,
                "title": title,
                "message": f"Navigated to {url}"
            }

        except Exception as e:
            self.logger.error(f"Failed to navigate to {url}: {e}")
            return {"success": False, "error": str(e)}

    def click_element(self, selector: str, by: str = "css") -> Dict[str, Any]:
        """Click an element on the page."""
        try:
            if not self.driver:
                return {"success": False, "error": "No browser running"}

            by_mapping = {
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "id": By.ID,
                "class": By.CLASS_NAME,
                "tag": By.TAG_NAME,
                "link_text": By.LINK_TEXT
            }

            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((by_mapping.get(by, By.CSS_SELECTOR), selector))
            )

            element.click()

            self.logger.info(f"Clicked element: {selector}")
            return {"success": True, "message": f"Clicked element: {selector}"}

        except TimeoutException:
            return {"success": False, "error": f"Element not clickable: {selector}"}
        except Exception as e:
            self.logger.error(f"Failed to click element {selector}: {e}")
            return {"success": False, "error": str(e)}

    def type_text(self, selector: str, text: str, by: str = "css", clear_first: bool = True) -> Dict[str, Any]:
        """Type text into an input element."""
        try:
            if not self.driver:
                return {"success": False, "error": "No browser running"}

            by_mapping = {
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "id": By.ID,
                "class": By.CLASS_NAME,
                "tag": By.TAG_NAME
            }

            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((by_mapping.get(by, By.CSS_SELECTOR), selector))
            )

            if clear_first:
                element.clear()

            element.send_keys(text)

            self.logger.info(f"Typed text into element: {selector}")
            return {"success": True, "message": f"Typed text into: {selector}"}

        except Exception as e:
            self.logger.error(f"Failed to type text into {selector}: {e}")
            return {"success": False, "error": str(e)}

    def take_screenshot(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot of the current page."""
        try:
            if not self.driver:
                return {"success": False, "error": "No browser running"}

            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"

            screenshot_path = self.exports_dir / filename
            self.driver.save_screenshot(str(screenshot_path))

            self.logger.info(f"Screenshot saved: {screenshot_path}")
            return {
                "success": True,
                "path": str(screenshot_path),
                "message": f"Screenshot saved as {filename}"
            }

        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            return {"success": False, "error": str(e)}

    def extract_text(self, selector: str = "body", by: str = "css") -> Dict[str, Any]:
        """Extract text from elements."""
        try:
            if not self.driver:
                return {"success": False, "error": "No browser running"}

            by_mapping = {
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "id": By.ID,
                "class": By.CLASS_NAME,
                "tag": By.TAG_NAME
            }

            elements = self.driver.find_elements(by_mapping.get(by, By.CSS_SELECTOR), selector)

            if not elements:
                return {"success": False, "error": f"No elements found: {selector}"}

            extracted_text = [element.text.strip() for element in elements if element.text.strip()]

            self.logger.info(f"Extracted text from {len(elements)} elements")
            return {
                "success": True,
                "text": extracted_text,
                "count": len(extracted_text)
            }

        except Exception as e:
            self.logger.error(f"Failed to extract text from {selector}: {e}")
            return {"success": False, "error": str(e)}

    def extract_links(self, base_url: Optional[str] = None) -> Dict[str, Any]:
        """Extract all links from the current page."""
        try:
            if not self.driver:
                return {"success": False, "error": "No browser running"}

            links = []
            link_elements = self.driver.find_elements(By.TAG_NAME, "a")

            for link in link_elements:
                href = link.get_attribute("href")
                text = link.text.strip()

                if href:
                    if base_url and href.startswith("/"):
                        href = base_url.rstrip("/") + href

                    links.append({
                        "url": href,
                        "text": text,
                        "title": link.get_attribute("title") or ""
                    })

            self.logger.info(f"Extracted {len(links)} links")
            return {
                "success": True,
                "links": links,
                "count": len(links)
            }

        except Exception as e:
            self.logger.error(f"Failed to extract links: {e}")
            return {"success": False, "error": str(e)}

    def scrape_page(self, url: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Scrape specific data from a page using selectors."""
        try:
            # Navigate to page
            nav_result = self.navigate_to(url)
            if not nav_result["success"]:
                return nav_result

            scraped_data = {}

            for field, selector in selectors.items():
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    if len(elements) == 1:
                        scraped_data[field] = elements[0].text.strip()
                    elif len(elements) > 1:
                        scraped_data[field] = [elem.text.strip() for elem in elements]
                    else:
                        scraped_data[field] = None

                except Exception as e:
                    self.logger.warning(f"Failed to scrape field {field}: {e}")
                    scraped_data[field] = None

            self.logger.info(f"Scraped {len(scraped_data)} fields from {url}")
            return {
                "success": True,
                "url": url,
                "data": scraped_data,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Failed to scrape page {url}: {e}")
            return {"success": False, "error": str(e)}

    def search_google(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Perform a Google search and extract results."""
        try:
            search_url = f"https://www.google.com/search?q={query}&num={num_results}"

            nav_result = self.navigate_to(search_url)
            if not nav_result["success"]:
                return nav_result

            # Wait for search results
            time.sleep(2)

            results = []
            result_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.g")

            for element in result_elements:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, "h3")
                    link_elem = element.find_element(By.CSS_SELECTOR, "a")
                    snippet_elem = element.find_element(By.CSS_SELECTOR, "span[style*='color'], .VwiC3b")

                    results.append({
                        "title": title_elem.text,
                        "url": link_elem.get_attribute("href"),
                        "snippet": snippet_elem.text
                    })

                except NoSuchElementException:
                    continue

                if len(results) >= num_results:
                    break

            self.logger.info(f"Found {len(results)} search results for: {query}")
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results)
            }

        except Exception as e:
            self.logger.error(f"Failed to search Google for {query}: {e}")
            return {"success": False, "error": str(e)}

    def export_data(self, data: List[Dict], filename: str, format: str = "csv") -> Dict[str, Any]:
        """Export scraped data to file."""
        try:
            if not data:
                return {"success": False, "error": "No data to export"}

            file_path = self.exports_dir / filename

            if format.lower() == "csv":
                df = pd.DataFrame(data)
                df.to_csv(file_path, index=False)
            elif format.lower() == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                return {"success": False, "error": f"Unsupported format: {format}"}

            self.logger.info(f"Exported {len(data)} records to {file_path}")
            return {
                "success": True,
                "path": str(file_path),
                "format": format,
                "records": len(data)
            }

        except Exception as e:
            self.logger.error(f"Failed to export data: {e}")
            return {"success": False, "error": str(e)}

    def get_page_info(self) -> Dict[str, Any]:
        """Get information about the current page."""
        try:
            if not self.driver:
                return {"success": False, "error": "No browser running"}

            info = {
                "url": self.driver.current_url,
                "title": self.driver.title,
                "page_source_length": len(self.driver.page_source),
                "window_size": self.driver.get_window_size(),
                "user_agent": self.driver.execute_script("return navigator.userAgent;")
            }

            return {"success": True, "info": info}

        except Exception as e:
            self.logger.error(f"Failed to get page info: {e}")
            return {"success": False, "error": str(e)}

    async def cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")


# Plugin instance - commented out to avoid logger initialization issues during import
# plugin = WebAutomationPlugin()