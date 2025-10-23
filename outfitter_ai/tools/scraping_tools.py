"""
Firecrawl-powered scraping with URL mapping for Universal Store
Now includes Google Custom Search integration
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from dotenv import load_dotenv

# Make firecrawl optional since we're not using it
try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    FirecrawlApp = None

from agents.state import ProductData
from config.universal_store_urls import get_category_url

# Import Google search functionality
try:
    from .google_search_scraper import GoogleSearchScraper
    GOOGLE_SEARCH_AVAILABLE = True
    print("✅ Google Custom Search available")
except ImportError as e:
    GOOGLE_SEARCH_AVAILABLE = False
    print(f"⚠️ Google Custom Search not available - {e}")

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirecrawlScraper:
    """Scraper using Firecrawl API (DEPRECATED - not in use)"""
    
    def __init__(self):
        if not FIRECRAWL_AVAILABLE:
            raise ImportError("Firecrawl is not installed. This scraper is deprecated and not needed.")
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
    """
    DEPRECATED: Old store-specific search method.
    Now redirects to Google Custom Search for better results.
    """
    logger.warning("🔧 DEPRECATED: search_all_stores() called - redirecting to Google Custom Search")
    return search_products_google_only(query, max_products)

# =========================
# Google Custom Search Integration
# =========================

def search_with_google(query: str, max_products: int = 10) -> List[ProductData]:
    """
    Search for products using Google Custom Search.
    This provides broader results from any Australian store.
    """
    if not GOOGLE_SEARCH_AVAILABLE:
        logger.warning("Google Custom Search not available")
        return []
    
    try:
        scraper = GoogleSearchScraper()
        results = scraper.search_products(query, num_results=max_products)
        
        # Convert to ProductData objects
        products = []
        for result in results:
            products.append(ProductData(
                name=result.get('name', 'Unknown Product'),
                price=result.get('price', 'Price not available'),
                brand=result.get('brand', 'Unknown Brand'),
                url=result.get('url', ''),
                image_url=result.get('image_url', ''),
                store_name=result.get('store_name', 'Unknown Store'),
                is_on_sale=result.get('is_on_sale', False),
                extracted_at=datetime.now()
            ))
        
        logger.info(f"Google Search found {len(products)} products")
        return products
        
    except Exception as e:
        logger.error(f"Google Search error: {e}")
        return []

async def search_hybrid(query: str, max_products: int = 20, include_google: bool = True) -> List[ProductData]:
    """
    Hybrid search combining store-specific scrapers with Google Custom Search.
    
    Args:
        query: Search query
        max_products: Maximum total products to return
        include_google: Whether to include Google Custom Search results
    
    Returns:
        Combined list of products from all sources
    """
    if not GOOGLE_SEARCH_AVAILABLE:
        logger.warning("Google Custom Search not available, using store scrapers only")
        return await search_all_stores(query, max_products)
    
    try:
        scraper = HybridGoogleScraper()
        
        # Calculate max results per source
        max_per_source = max_products // 3 if include_google else max_products // 2
        
        results = scraper.search_products(
            query=query,
            include_google=include_google,
            include_culturekings=True,
            include_universalstore=True,
            max_results_per_source=max_per_source
        )
        
        # Convert to ProductData objects
        products = []
        for result in results:
            products.append(ProductData(
                name=result.get('name', 'Unknown Product'),
                price=result.get('price', 'Price not available'),
                brand=result.get('brand', 'Unknown Brand'),
                url=result.get('url', ''),
                image_url=result.get('image_url', ''),
                store_name=result.get('store_name', 'Unknown Store'),
                is_on_sale=result.get('is_on_sale', False),
                extracted_at=datetime.now()
            ))
        
        logger.info(f"Hybrid search found {len(products)} products")
        return products
        
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        # Fallback to store scrapers only
        return await search_all_stores(query, max_products)

# =========================
# Enhanced search function with Google integration
# =========================

async def search_products_enhanced(query: str, max_products: int = 30, 
                                 use_google: bool = True) -> List[ProductData]:
    """
    DEPRECATED: Use search_products_google_only() instead.
    This function now redirects to Google-only search.
    """
    logger.warning("🔧 DEPRECATED: search_products_enhanced() called - redirecting to Google-only search")
    return search_products_google_only(query, max_products)

# =========================
# Google-Only Search Functions
# =========================

def search_products_google_only(query: str, max_products: int = 30) -> List[ProductData]:
    """
    Search products using ONLY Google Custom Search.
    This is the new primary search method.
    
    Args:
        query: Search query (will automatically add "australia" if not present)
        max_products: Maximum products to return
    
    Returns:
        List of products from Google Custom Search
    """
    if not GOOGLE_SEARCH_AVAILABLE:
        logger.error("Google Custom Search not available")
        return []
    
    try:
        logger.info(f"🔍 Google Custom Search: '{query}'")
        return search_with_google(query, max_products)
    except Exception as e:
        logger.error(f"Google Custom Search error: {e}")
        return []

async def search_products_google_only_async(query: str, max_products: int = 30) -> List[ProductData]:
    """
    Async wrapper for Google-only search.
    """
    return search_products_google_only(query, max_products)