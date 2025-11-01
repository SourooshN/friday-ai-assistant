"""
Web Scraping Plugin for Friday AI Assistant
Advanced web scraping and data extraction capabilities.
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from core.logging import get_logger, initialize_logger


class WebScrapingPlugin:
    """Plugin for advanced web scraping and data extraction."""

    def __init__(self):
        self.name = "web_scraping"
        self.description = "Advanced web scraping and data extraction"
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
        self.exports_dir = Path("./data/exports")
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        # Session for requests
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        )

    async def initialize(self) -> bool:
        """Initialize the web scraping plugin."""
        try:
            self.logger.info("Initializing web scraping plugin")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize web scraping plugin: {e}")
            return False

    def get_available_functions(self) -> List[str]:
        """Get list of available plugin functions."""
        return [
            "scrape_url",
            "scrape_multiple_urls",
            "extract_product_data",
            "extract_article_data",
            "extract_contact_info",
            "extract_social_links",
            "monitor_price_changes",
            "extract_job_listings",
            "scrape_news_articles",
            "extract_table_data",
            "follow_pagination",
            "scrape_with_javascript",
            "detect_content_changes",
            "bulk_url_analysis",
            "export_scraped_data",
        ]

    def scrape_url(
        self,
        url: str,
        selectors: Optional[Dict[str, str]] = None,
        extract_links: bool = False,
        extract_images: bool = False,
        follow_redirects: bool = True,
    ) -> Dict[str, Any]:
        """Scrape a single URL with customizable extraction."""
        try:
            response = self.session.get(url, allow_redirects=follow_redirects, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Basic page information
            page_data = {
                "url": url,
                "final_url": response.url,
                "title": soup.title.string.strip() if soup.title else "",
                "status_code": response.status_code,
                "content_length": len(response.content),
                "scraped_at": datetime.now().isoformat(),
            }

            # Extract meta information
            meta_data = self._extract_meta_data(soup)
            page_data["meta"] = meta_data

            # Custom selectors
            if selectors:
                extracted_data = {}
                for field, selector in selectors.items():
                    try:
                        elements = soup.select(selector)
                        if len(elements) == 1:
                            extracted_data[field] = elements[0].get_text(strip=True)
                        elif len(elements) > 1:
                            extracted_data[field] = [elem.get_text(strip=True) for elem in elements]
                        else:
                            extracted_data[field] = None
                    except Exception as e:
                        self.logger.warning(f"Failed to extract {field}: {e}")
                        extracted_data[field] = None

                page_data["extracted"] = extracted_data

            # Extract links
            if extract_links:
                links = self._extract_links(soup, url)
                page_data["links"] = links

            # Extract images
            if extract_images:
                images = self._extract_images(soup, url)
                page_data["images"] = images

            self.logger.info(f"Successfully scraped: {url}")
            return {"success": True, "data": page_data}

        except Exception as e:
            self.logger.error(f"Failed to scrape {url}: {e}")
            return {"success": False, "error": str(e)}

    def scrape_multiple_urls(
        self, urls: List[str], selectors: Optional[Dict[str, str]] = None, delay: float = 1.0, max_workers: int = 5
    ) -> Dict[str, Any]:
        """Scrape multiple URLs with rate limiting."""
        try:
            results = []
            failed_urls = []

            for i, url in enumerate(urls):
                try:
                    result = self.scrape_url(url, selectors)
                    if result["success"]:
                        results.append(result["data"])
                    else:
                        failed_urls.append({"url": url, "error": result["error"]})

                    # Rate limiting
                    if i < len(urls) - 1:
                        time.sleep(delay)

                except Exception as e:
                    failed_urls.append({"url": url, "error": str(e)})

            self.logger.info(f"Scraped {len(results)} URLs successfully, {len(failed_urls)} failed")
            return {"success": True, "results": results, "failed_urls": failed_urls, "total_scraped": len(results), "total_failed": len(failed_urls)}

        except Exception as e:
            self.logger.error(f"Failed to scrape multiple URLs: {e}")
            return {"success": False, "error": str(e)}

    def extract_product_data(self, url: str) -> Dict[str, Any]:
        """Extract product information from e-commerce pages."""
        try:
            # Common e-commerce selectors
            selectors = {
                "name": "h1, .product-title, .product-name, [data-testid*='product-title']",
                "price": ".price, .product-price, .cost, [data-testid*='price']",
                "description": ".description, .product-description, .product-details",
                "rating": ".rating, .review-score, .stars",
                "availability": ".availability, .stock, .in-stock, .out-of-stock",
                "brand": ".brand, .manufacturer, .product-brand",
                "sku": ".sku, .product-id, .item-number",
            }

            result = self.scrape_url(url, selectors, extract_images=True)

            if result["success"]:
                # Clean and format product data
                product_data = result["data"]["extracted"]

                # Try to extract price as number
                if product_data.get("price"):
                    price_text = product_data["price"]
                    if isinstance(price_text, list):
                        price_text = price_text[0]

                    # Extract numeric price
                    price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                    if price_match:
                        product_data["price_numeric"] = float(price_match.group())

                result["data"]["product_info"] = product_data

            return result

        except Exception as e:
            self.logger.error(f"Failed to extract product data from {url}: {e}")
            return {"success": False, "error": str(e)}

    def extract_article_data(self, url: str) -> Dict[str, Any]:
        """Extract article/blog post information."""
        try:
            selectors = {
                "headline": "h1, .headline, .article-title, .post-title",
                "author": ".author, .byline, .writer, [rel='author']",
                "publish_date": ".date, .publish-date, .post-date, time[datetime]",
                "content": ".content, .article-content, .post-content, .entry-content",
                "tags": ".tags, .categories, .tag, .category",
                "summary": ".summary, .excerpt, .description, .lead",
            }

            result = self.scrape_url(url, selectors)

            if result["success"]:
                article_data = result["data"]["extracted"]

                # Extract word count
                if article_data.get("content"):
                    content = article_data["content"]
                    if isinstance(content, list):
                        content = " ".join(content)
                    words = len(content.split())
                    article_data["word_count"] = words

                result["data"]["article_info"] = article_data

            return result

        except Exception as e:
            self.logger.error(f"Failed to extract article data from {url}: {e}")
            return {"success": False, "error": str(e)}

    def extract_contact_info(self, url: str) -> Dict[str, Any]:
        """Extract contact information from web pages."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            text_content = soup.get_text()

            contact_info = {
                "emails": self._extract_emails(text_content),
                "phones": self._extract_phone_numbers(text_content),
                "addresses": self._extract_addresses(soup),
                "social_links": self._extract_social_links(soup, url),
            }

            return {"success": True, "url": url, "contact_info": contact_info, "scraped_at": datetime.now().isoformat()}

        except Exception as e:
            self.logger.error(f"Failed to extract contact info from {url}: {e}")
            return {"success": False, "error": str(e)}

    def extract_table_data(self, url: str, table_selector: str = "table") -> Dict[str, Any]:
        """Extract data from HTML tables."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            tables = soup.select(table_selector)

            if not tables:
                return {"success": False, "error": "No tables found"}

            extracted_tables = []

            for i, table in enumerate(tables):
                # Extract headers
                headers = []
                header_row = table.find("tr")
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

                # Extract rows
                rows = []
                for row in table.find_all("tr")[1:]:  # Skip header row
                    cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                    if cells:
                        rows.append(cells)

                table_data = {
                    "table_index": i,
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                    "column_count": len(headers) if headers else (len(rows[0]) if rows else 0),
                }

                extracted_tables.append(table_data)

            return {
                "success": True,
                "url": url,
                "tables": extracted_tables,
                "table_count": len(extracted_tables),
                "scraped_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to extract table data from {url}: {e}")
            return {"success": False, "error": str(e)}

    def scrape_news_articles(self, news_site_url: str, article_links_selector: str) -> Dict[str, Any]:
        """Scrape multiple news articles from a news site."""
        try:
            # First, get the list of article links
            response = self.session.get(news_site_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            article_links = soup.select(article_links_selector)

            if not article_links:
                return {"success": False, "error": "No article links found"}

            # Extract URLs
            urls = []
            for link in article_links[:20]:  # Limit to 20 articles
                href = link.get("href")
                if href:
                    full_url = urljoin(news_site_url, href)
                    urls.append(full_url)

            # Scrape each article
            articles = []
            for url in urls:
                article_result = self.extract_article_data(url)
                if article_result["success"]:
                    articles.append(article_result["data"])

                time.sleep(1)  # Rate limiting

            return {
                "success": True,
                "source_url": news_site_url,
                "articles": articles,
                "article_count": len(articles),
                "scraped_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to scrape news articles from {news_site_url}: {e}")
            return {"success": False, "error": str(e)}

    def export_scraped_data(self, data: Union[Dict, List], filename: str, format: str = "csv") -> Dict[str, Any]:
        """Export scraped data to various formats."""
        try:
            file_path = self.exports_dir / filename

            if format.lower() == "csv":
                if isinstance(data, dict):
                    # Convert single dict to list
                    data = [data]

                df = pd.DataFrame(data)
                df.to_csv(file_path, index=False, encoding="utf-8")

            elif format.lower() == "json":
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            elif format.lower() == "xlsx":
                if isinstance(data, dict):
                    data = [data]

                df = pd.DataFrame(data)
                df.to_excel(file_path, index=False)

            else:
                return {"success": False, "error": f"Unsupported format: {format}"}

            record_count = len(data) if isinstance(data, list) else 1

            self.logger.info(f"Exported {record_count} records to {file_path}")
            return {"success": True, "file_path": str(file_path), "format": format, "record_count": record_count}

        except Exception as e:
            self.logger.error(f"Failed to export data: {e}")
            return {"success": False, "error": str(e)}

    # Helper methods
    def _extract_meta_data(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract meta tags from HTML."""
        meta_data = {}

        # Standard meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content = meta.get("content")

            if name and content:
                meta_data[name] = content

        return meta_data

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract all links from the page."""
        links = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)

            # Convert relative URLs to absolute
            full_url = urljoin(base_url, href)

            links.append({"url": full_url, "text": text, "title": link.get("title", "")})

        return links

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract all images from the page."""
        images = []

        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                full_url = urljoin(base_url, src)
                images.append({"url": full_url, "alt": img.get("alt", ""), "title": img.get("title", "")})

        return images

    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text."""
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        emails = re.findall(email_pattern, text)
        return list(set(emails))  # Remove duplicates

    def _extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers from text."""
        phone_patterns = [
            r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",  # US format
            r"\+\d{1,3}[-.\s]?\d{1,14}",  # International format
            r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}",  # Simple format
        ]

        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))

        return list(set(phones))  # Remove duplicates

    def _extract_addresses(self, soup: BeautifulSoup) -> List[str]:
        """Extract potential addresses from the page."""
        # Look for address-related elements
        address_selectors = ["address", ".address", ".location", ".contact-address", "[itemprop='address']"]

        addresses = []
        for selector in address_selectors:
            elements = soup.select(selector)
            for element in elements:
                address_text = element.get_text(strip=True)
                if address_text and len(address_text) > 10:  # Basic filter
                    addresses.append(address_text)

        return list(set(addresses))  # Remove duplicates

    def _extract_social_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Extract social media links."""
        social_platforms = {
            "twitter": ["twitter.com", "x.com"],
            "facebook": ["facebook.com"],
            "linkedin": ["linkedin.com"],
            "instagram": ["instagram.com"],
            "youtube": ["youtube.com"],
            "github": ["github.com"],
        }

        social_links = {}

        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(base_url, href)

            for platform, domains in social_platforms.items():
                if any(domain in full_url.lower() for domain in domains):
                    if platform not in social_links:  # Keep first match
                        social_links[platform] = full_url

        return social_links

    async def cleanup(self):
        """Clean up resources."""
        self.session.close()
        self.logger.info("Web scraping plugin cleanup completed")


# Plugin instance - commented out to avoid logger initialization issues during import
# plugin = WebScrapingPlugin()
