"""
Core web scraping tools using Playwright.
Handles browser automation, page navigation, and data extraction.
"""

import asyncio
import random
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from datetime import datetime
import logging

from config.store_config import get_store_config, StoreConfig, get_all_store_names
from agents.state import ProductData

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaywrightScraper:
    """
    Core scraping engine using Playwright for browser automation.
    """
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def create_page(self) -> Page:
        """Create a new page with common settings"""
        if not self.browser:
            raise RuntimeError("Browser not initialized. Use async context manager.")
            
        page = await self.browser.new_page()
        
        # Set common headers to appear more like a real browser
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # Set viewport
        await page.set_viewport_size({'width': 1920, 'height': 1080})
        
        return page

class StoreProductScraper:
    """
    High-level product scraper for specific stores.
    """
    
    def __init__(self, store_name: str):
        self.store_name = store_name.lower()
        self.config = get_store_config(self.store_name)
        if not self.config:
            raise ValueError(f"Store '{store_name}' not configured")
    
    async def search_products(self, query: str, category: str = "mens", max_products: Optional[int] = None) -> List[ProductData]:
        """
        Search for products on the configured store.
        
        Args:
            query: Search term (e.g., "black hoodie")
            category: Product category (e.g., "mens", "womens")
            max_products: Maximum number of products to return
            
        Returns:
            List of ProductData objects
        """
        max_products = max_products or self.config.max_products_per_search
        
        try:
            async with PlaywrightScraper() as scraper:
                page = await scraper.create_page()
                
                # Build search URL
                search_url = self._build_search_url(query, category)
                logger.info(f"Searching {self.config.name}: {search_url}")
                
                # Navigate to search page
                await page.goto(search_url, timeout=30000)
                await self._wait_for_page_load(page)
                
                # Handle different loading strategies
                if self.config.loading_strategy == "infinite_scroll":
                    await self._handle_infinite_scroll(page, max_products)
                elif self.config.loading_strategy == "single_page_scroll":
                    await self._handle_single_page_scroll(page)
                
                # Extract products
                products = await self._extract_products(page, max_products)
                
                logger.info(f"Found {len(products)} products from {self.config.name}")
                return products
                
        except Exception as e:
            logger.error(f"Error scraping {self.config.name}: {e}")
            return []
    
    def _build_search_url(self, query: str, category: str) -> str:
        """Build search URL based on store configuration"""
        base_url = self.config.base_url
        
        if self.store_name == "culturekings":
            # CultureKings: Use homepage instead of search since selectors work there
            # The homepage shows featured/trending products which is good for discovery
            return f"{base_url}/"
            
        elif self.store_name == "universalstore":
            # Universal Store collection format
            category_path = "mens" if category == "mens" else "womens"
            search_query = query.replace(" ", "%20")
            return f"{base_url}/collections/{category_path}?q={search_query}"
            
        elif self.store_name == "cottonon":
            # Cotton On search format
            search_query = query.replace(" ", "%20")
            return f"{base_url}/AU/search?q={search_query}"
            
        else:
            # Fallback generic search
            return f"{base_url}/search?q={query.replace(' ', '+')}"
    
    async def _wait_for_page_load(self, page: Page):
        """Wait for page to fully load"""
        try:
            # Wait for DOM content
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            
            # Wait for network to be mostly idle
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Additional wait for JavaScript to render products
            await asyncio.sleep(self.config.scroll_pause_time)
            
        except PlaywrightTimeoutError:
            logger.warning(f"Page load timeout for {self.config.name}")
            # Continue anyway
    
    async def _handle_infinite_scroll(self, page: Page, max_products: int):
        """Handle infinite scroll to load more products"""
        previous_count = 0
        scroll_attempts = 0
        max_scrolls = 5
        
        while scroll_attempts < max_scrolls:
            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(self.config.scroll_pause_time)
            
            # Check if more products loaded
            current_count = await page.locator(self.config.selectors["product_container"]).count()
            
            if current_count >= max_products or current_count == previous_count:
                break
                
            previous_count = current_count
            scroll_attempts += 1
            
        logger.info(f"Loaded {current_count} products after {scroll_attempts} scrolls")
    
    async def _handle_single_page_scroll(self, page: Page):
        """Handle single page scroll to ensure all content is loaded"""
        # Scroll to middle and bottom to trigger any lazy loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await asyncio.sleep(1)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(self.config.scroll_pause_time)
        await page.evaluate("window.scrollTo(0, 0)")  # Back to top
    
    async def _extract_products(self, page: Page, max_products: int) -> List[ProductData]:
        """Extract product data from the page"""
        products = []
        
        try:
            # Get all product containers
            containers = page.locator(self.config.selectors["product_container"])
            count = min(await containers.count(), max_products)
            
            logger.info(f"Found {count} product containers")
            
            for i in range(count):
                try:
                    container = containers.nth(i)
                    product = await self._extract_single_product(container, page)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning(f"Error extracting product {i}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting products: {e}")
            
        return products
    
    async def _extract_single_product(self, container, page: Page) -> Optional[ProductData]:
        """Extract data from a single product container"""
        try:
            # Extract basic info using selectors
            name = await self._safe_extract_text(container, self.config.selectors.get("product_name"))
            price = await self._safe_extract_text(container, self.config.selectors.get("product_price"))
            brand = await self._safe_extract_text(container, self.config.selectors.get("product_brand"))
            
            # Extract URL
            url = await self._safe_extract_attribute(container, self.config.selectors.get("product_url"), "href")
            if url and not url.startswith("http"):
                url = urljoin(self.config.base_url, url)
            
            # Extract image URL
            image_url = await self._safe_extract_attribute(container, self.config.selectors.get("product_image"), "src")
            if image_url and not image_url.startswith("http"):
                image_url = urljoin(self.config.base_url, image_url)
            
            # Clean and validate data
            if not name or not price:
                return None
                
            # Clean price (remove currency symbols, sale text, etc.)
            clean_price = self._clean_price(price)
            
            # Check for sale badge
            is_on_sale = await self._check_sale_status(container)
            
            return ProductData(
                name=name.strip(),
                price=clean_price,
                brand=brand.strip() if brand else self.config.name,
                url=url,
                image_url=image_url,
                store_name=self.config.name,
                is_on_sale=is_on_sale,
                extracted_at=datetime.now()
            )
            
        except Exception as e:
            logger.warning(f"Error extracting single product: {e}")
            return None
    
    async def _safe_extract_text(self, container, selector: Optional[str]) -> Optional[str]:
        """Safely extract text from an element with fallback support"""
        if not selector:
            return None
            
        # Try primary selector first
        try:
            element = container.locator(selector).first
            if await element.count() > 0:
                # For CultureKings a[title] selector, extract title attribute
                if selector == "a[title]":
                    title = await element.get_attribute("title")
                    if title and title.strip():
                        return title.strip()
                
                # For other selectors, try text content
                text = await element.text_content()
                if text and text.strip():
                    return text.strip()
        except:
            pass
        
        # If primary failed, try fallback selectors for product_name
        if "product_name" in str(selector):
            fallback_name_selectors = self.config.fallback_selectors.get("product_name", "").split(", ")
            for fallback_selector in fallback_name_selectors:
                if fallback_selector.strip():
                    try:
                        element = container.locator(fallback_selector.strip()).first
                        if await element.count() > 0:
                            text = await element.text_content()
                            if text and text.strip() and '<' not in text:  # Avoid HTML content
                                return text.strip()
                    except:
                        continue
            
        return None
    
    async def _safe_extract_attribute(self, container, selector: Optional[str], attribute: str) -> Optional[str]:
        """Safely extract an attribute from an element with fallback support"""
        if not selector:
            return None
            
        # Try primary selector first
        try:
            element = container.locator(selector).first
            if await element.count() > 0:
                attr_value = await element.get_attribute(attribute)
                if attr_value:
                    return attr_value
        except:
            pass
        
        # Try fallback selectors if primary failed
        if "product_url" in str(selector):
            fallback_url_selectors = self.config.fallback_selectors.get("product_url", "").split(", ")
            for fallback_selector in fallback_url_selectors:
                if fallback_selector.strip():
                    try:
                        element = container.locator(fallback_selector.strip()).first
                        if await element.count() > 0:
                            attr_value = await element.get_attribute(attribute)
                            if attr_value:
                                return attr_value
                    except:
                        continue
        
        return None
    
    async def _check_sale_status(self, container) -> bool:
        """Check if product is on sale"""
        sale_selector = self.config.selectors.get("sale_badge")
        if not sale_selector:
            return False
            
        try:
            sale_element = container.locator(sale_selector).first
            return await sale_element.count() > 0
        except:
            return False
    
    def _clean_price(self, price_text: str) -> str:
        """Clean and normalize price text"""
        if not price_text:
            return ""
            
        # Remove extra whitespace
        price_text = re.sub(r'\s+', ' ', price_text.strip())
        
        # Extract price using regex (handles $XX.XX, $XX, etc.)
        price_match = re.search(r'\$(\d+(?:\.\d{2})?)', price_text)
        if price_match:
            return f"${price_match.group(1)}"
            
        return price_text

class MultiStoreScraper:
    """
    Scraper that searches across multiple stores simultaneously.
    """
    
    def __init__(self, store_names: Optional[List[str]] = None):
        self.store_names = store_names or get_all_store_names()
        self.scrapers = {name: StoreProductScraper(name) for name in self.store_names}
    
    async def search_all_stores(self, query: str, category: str = "mens", max_products_per_store: int = 10) -> Dict[str, List[ProductData]]:
        """
        Search for products across all configured stores.
        
        Returns:
            Dictionary mapping store names to their product results
        """
        tasks = []
        
        for store_name, scraper in self.scrapers.items():
            task = asyncio.create_task(
                scraper.search_products(query, category, max_products_per_store),
                name=f"search_{store_name}"
            )
            tasks.append((store_name, task))
        
        results = {}
        for store_name, task in tasks:
            try:
                products = await task
                results[store_name] = products
            except Exception as e:
                logger.error(f"Error searching {store_name}: {e}")
                results[store_name] = []
        
        return results
    
    async def search_and_combine(self, query: str, category: str = "mens", max_total_products: int = 30) -> List[ProductData]:
        """
        Search all stores and return combined, deduplicated results.
        """
        store_results = await self.search_all_stores(query, category)
        
        # Combine all results
        all_products = []
        for store_name, products in store_results.items():
            all_products.extend(products)
        
        # Simple deduplication based on product name similarity
        unique_products = self._deduplicate_products(all_products)
        
        # Sort by store priority and limit results
        sorted_products = self._sort_products(unique_products)
        
        return sorted_products[:max_total_products]
    
    def _deduplicate_products(self, products: List[ProductData]) -> List[ProductData]:
        """Remove duplicate products based on name similarity"""
        unique_products = []
        seen_names = set()
        
        for product in products:
            # Create a normalized name for comparison
            normalized_name = re.sub(r'[^\w\s]', '', product.name.lower())
            normalized_name = re.sub(r'\s+', ' ', normalized_name).strip()
            
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_products.append(product)
        
        return unique_products
    
    def _sort_products(self, products: List[ProductData]) -> List[ProductData]:
        """Sort products by store priority and other factors"""
        # Define store priority (CultureKings first, then others)
        store_priority = {"CultureKings": 1, "Universal Store": 2, "Cotton On": 3}
        
        return sorted(products, key=lambda p: (
            store_priority.get(p.store_name, 999),  # Store priority
            not p.is_on_sale,  # Sale items first
            p.name.lower()  # Alphabetical
        ))

# Convenience functions for easy usage
async def search_single_store(store_name: str, query: str, max_products: int = 20) -> List[ProductData]:
    """Quick search for a single store"""
    scraper = StoreProductScraper(store_name)
    return await scraper.search_products(query, max_products=max_products)

async def search_all_stores(query: str, max_products: int = 30) -> List[ProductData]:
    """Quick search across all stores"""
    scraper = MultiStoreScraper()
    return await scraper.search_and_combine(query, max_total_products=max_products)