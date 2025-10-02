"""
CultureKings scraper using Playwright (the approach that was working)
"""

import asyncio
from typing import List
from datetime import datetime
import logging
from bs4 import BeautifulSoup

from playwright.async_api import async_playwright
from agents.state import ProductData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scrape_culturekings(query: str, max_products: int = 15) -> List[ProductData]:
    """
    Scrape CultureKings using Playwright with aggressive popup handling
    """
    search_url = f"https://culturekings.com.au/search?q={query.replace(' ', '+')}"
    logger.info(f"🎭 Playwright: {search_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        try:
            # Navigate
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # AGGRESSIVE popup closing - try EVERYTHING
            popup_attempts = [
                # Text-based buttons
                'button:has-text("No thanks")',
                'button:has-text("keep shopping")',
                'a:has-text("keep shopping")',
                # Close buttons
                '[aria-label="Close"]',
                'button.close',
                '.modal-close',
                '[data-close]',
                # Overlay clicks
                '.modal-overlay',
                '.popup-overlay',
                # ESC key
            ]
            
            for selector in popup_attempts:
                try:
                    await page.locator(selector).first.click(timeout=1000)
                    logger.info(f"   ✅ Closed popup: {selector}")
                    await asyncio.sleep(0.5)
                    break
                except:
                    continue
            
            # Try ESC key
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
            
            # Scroll to load products
            for i in range(3):
                await page.evaluate(f"window.scrollTo(0, {500 * (i + 1)})")
                await asyncio.sleep(0.5)
            
            # Get HTML
            html = await page.content()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            containers = soup.select('.ProductHit_root__2tJkv')[:max_products]
            
            logger.info(f"   📦 Found {len(containers)} containers")
            
            products = []
            for container in containers:
                try:
                    # Name from title
                    name_elem = container.select_one('a[title]')
                    name = name_elem.get('title', '').strip() if name_elem else None
                    
                    # Price
                    price_elem = container.select_one('.ProductHit_price__p0oAO')
                    price_text = price_elem.get_text(strip=True) if price_elem else None
                    
                    # URL
                    url_elem = container.select_one('a[href*="/products/"]')
                    url = url_elem.get('href', '') if url_elem else ''
                    if url and not url.startswith('http'):
                        url = f"https://culturekings.com.au{url}"
                    
                    if name and price_text:
                        # Clean price
                        import re
                        price_match = re.search(r'\$\d+(?:\.\d{2})?', price_text)
                        price = price_match.group() if price_match else price_text
                        
                        products.append(ProductData(
                            name=name,
                            price=price,
                            brand="CultureKings",
                            url=url,
                            image_url=None,
                            store_name="CultureKings",
                            is_on_sale=False,
                            extracted_at=datetime.now()
                        ))
                        
                except Exception as e:
                    continue
            
            logger.info(f"✅ CultureKings: {len(products)} products")
            return products
            
        except Exception as e:
            logger.error(f"❌ CultureKings error: {e}")
            return []
            
        finally:
            await browser.close()