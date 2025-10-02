"""
Firecrawl-powered scraping with URL mapping for Universal Store
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from dotenv import load_dotenv

from firecrawl import FirecrawlApp
from agents.state import ProductData
from config.universal_store_urls import get_category_url

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirecrawlScraper:
    """Scraper using Firecrawl API"""
    
    def __init__(self):
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY not found in environment")
        self.app = FirecrawlApp(api_key=api_key)
            
    def scrape_culturekings(self, query: str, max_products: int = 15) -> List[ProductData]:
        """Scrape CultureKings using HTML format"""
        search_url = f"https://culturekings.com.au/search?q={query.replace(' ', '+')}"
        logger.info(f"Scraping CultureKings AU (HTML): {search_url}")
        
        try:
            # Use HTML format instead of markdown
            result = self.app.scrape(
                search_url, 
                formats=['html'],
                wait_for=5000
            )
            
            html_content = getattr(result, 'html', '')
            
            print(f"\n{'='*60}")
            print(f"CULTUREKINGS HTML DEBUG:")
            print(f"HTML length: {len(html_content)}")
            
            # Parse with BeautifulSoup
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Use our known working selector
            products_found = soup.select('.ProductHit_root__2tJkv')
            print(f"Products found with selector: {len(products_found)}")
            
            if products_found:
                print("First product HTML sample:")
                print(str(products_found[0])[:500])
            print(f"{'='*60}\n")
            
            products = self._parse_culturekings_html(soup, max_products)
            
            logger.info(f"Found {len(products)} products from CultureKings AU")
            return products
            
        except Exception as e:
            logger.error(f"CultureKings AU scraping error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_culturekings_html(self, soup, max_products: int) -> List[ProductData]:
        """Parse CultureKings from HTML using known selectors"""
        from bs4 import BeautifulSoup
        import re
        
        products = []
        containers = soup.select('.ProductHit_root__2tJkv')[:max_products]
        
        for container in containers:
            try:
                # Name from title attribute
                name_elem = container.select_one('a[title]')
                name = name_elem.get('title', '').strip() if name_elem else None
                
                # Price
                price_elem = container.select_one('.ProductHit_price__p0oAO')
                price = price_elem.get_text(strip=True) if price_elem else None
                
                # URL
                url_elem = container.select_one('a[href*="/products/"]')
                url = url_elem.get('href', '') if url_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://culturekings.com.au{url}"
                
                if name and price:
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
        
        return products

    def scrape_universalstore(self, query: str, max_products: int = 50) -> List[ProductData]:
        """Scrape Universal Store using category browsing"""
        category_url = get_category_url(query)
        logger.info(f"Scraping Universal Store: {category_url}")
        
        try:
            result = self.app.scrape(category_url, formats=['markdown'])
            
            # FIXED: Access as attribute, not dict
            markdown_content = getattr(result, 'markdown', '')
            
            print(f"\n{'='*60}")
            print(f"UNIVERSAL STORE DEBUG:")
            print(f"Markdown length: {len(markdown_content)}")
            print(f"First 500 chars:")
            print(markdown_content[:500])
            print(f"{'='*60}\n")
            
            products = self._parse_universalstore_markdown(markdown_content)
            
            logger.info(f"Found {len(products)} products from Universal Store")
            return products[:max_products]
            
        except Exception as e:
            logger.error(f"Universal Store scraping error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_culturekings_markdown(self, markdown: str) -> List[ProductData]:
        """Parse CultureKings product data from markdown"""
        products = []
        lines = markdown.split('\n')
        
        current_product = {}
        for line in lines:
            # Look for product patterns in markdown
            if 'products/' in line and 'http' in line:
                # Extract URL
                import re
                url_match = re.search(r'https://[^\s\)]+', line)
                if url_match:
                    current_product['url'] = url_match.group()
            
            # Look for price patterns
            if '$' in line and any(char.isdigit() for char in line):
                import re
                price_match = re.search(r'\$\d+(?:\.\d{2})?', line)
                if price_match:
                    current_product['price'] = price_match.group()
            
            # Look for product names (usually in headers or links)
            if line.strip().startswith('#') or '](http' in line:
                # Extract text from markdown link or header
                import re
                text = re.sub(r'\[|\]|\(http[^\)]+\)|#+', '', line).strip()
                if text and len(text) > 5:
                    current_product['name'] = text
            
            # When we have complete product, save it
            if current_product.get('name') and current_product.get('price'):
                products.append(ProductData(
                    name=current_product['name'],
                    price=current_product['price'],
                    brand="CultureKings",
                    url=current_product.get('url'),
                    image_url=None,
                    store_name="CultureKings",
                    is_on_sale=False,
                    extracted_at=datetime.now()
                ))
                current_product = {}
        
        return products
    
    def _parse_universalstore_markdown(self, markdown: str) -> List[ProductData]:
        """Parse Universal Store product data from markdown"""
        products = []
        lines = markdown.split('\n')
        
        current_product = {}
        for line in lines:
            # Look for product URLs
            if 'products/' in line and 'universalstore.com' in line:
                import re
                url_match = re.search(r'https://[^\s\)]+', line)
                if url_match:
                    current_product['url'] = url_match.group()
            
            # Look for prices
            if '$' in line and any(char.isdigit() for char in line):
                import re
                price_match = re.search(r'\$\d+(?:\.\d{2})?', line)
                if price_match:
                    current_product['price'] = price_match.group()
            
            # Look for product names
            if line.strip().startswith('#') or '](http' in line:
                import re
                text = re.sub(r'\[|\]|\(http[^\)]+\)|#+', '', line).strip()
                if text and len(text) > 5 and not any(skip in text.lower() for skip in ['shop', 'view', 'quick']):
                    current_product['name'] = text
            
            # Save complete product
            if current_product.get('name') and current_product.get('price'):
                products.append(ProductData(
                    name=current_product['name'],
                    price=current_product['price'],
                    brand="Universal Store",
                    url=current_product.get('url'),
                    image_url=None,
                    store_name="Universal Store",
                    is_on_sale=False,
                    extracted_at=datetime.now()
                ))
                current_product = {}
        
        return products

async def search_all_stores(query: str, max_products: int = 30) -> List[ProductData]:
    """Search both stores using Firecrawl"""
    scraper = FirecrawlScraper()
    
    # Scrape both stores (not async since Firecrawl is sync)
    culturekings_products = scraper.scrape_culturekings(query, max_products=15)
    universalstore_products = scraper.scrape_universalstore(query, max_products=15)
    
    # Combine results
    all_products = culturekings_products + universalstore_products
    
    return all_products[:max_products]