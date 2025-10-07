"""
CultureKings scraper using Google Shopping API via SerpAPI.
Gets accurate product data directly from Google's indexed results.

Setup:
1. pip install google-search-results
2. Get API key from https://serpapi.com/ (100 free searches/month)
3. Add SERPAPI_KEY to .env
"""

import os
import re
import logging
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv
from serpapi import GoogleSearch
from agents.state import ProductData

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scrape_culturekings_google_shopping(query: str, max_products: int = 15) -> List[ProductData]:
    """
    Scrape CultureKings products using Google Shopping via SerpAPI.
    
    This is the PRIMARY method for CultureKings - more reliable than direct scraping.
    
    Args:
        query: Search query (e.g., "red hoodies", "black shoes")
        max_products: Maximum number of products to return
        
    Returns:
        List of ProductData with accurate names, prices, URLs, and images
    """
    api_key = os.getenv("SERPAPI_KEY")
    
    if not api_key:
        logger.error("❌ SERPAPI_KEY not found in .env file")
        logger.error("   Get API key at: https://serpapi.com/")
        logger.error("   Add to .env: SERPAPI_KEY=your_key_here")
        return []
    
    # Build search query targeting CultureKings
    # Format: "query site:culturekings.com.au" tells Google to only show CultureKings results
    search_query = f"{query} site:culturekings.com.au"
    
    logger.info(f"🔍 Google Shopping: '{search_query}'")
    
    try:
        # Configure SerpAPI parameters
        params = {
            "engine": "google_shopping",  # Use Shopping results (has prices!)
            "q": search_query,
            "api_key": api_key,
            "num": min(max_products, 20),  # Google Shopping returns max 20 per request
            "hl": "en",  # Language: English
            "gl": "au",  # Country: Australia
        }
        
        # Execute search
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Check for API errors
        if "error" in results:
            logger.error(f"❌ SerpAPI error: {results['error']}")
            return []
        
        # Parse shopping results
        products = parse_google_shopping_results(results, max_products)
        
        logger.info(f"✅ Google Shopping: Found {len(products)} CultureKings products")
        
        # Log sample for debugging
        if products:
            logger.debug(f"   Sample: {products[0].name} - {products[0].price}")
        
        return products
        
    except Exception as e:
        logger.error(f"❌ Google Shopping error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def parse_google_shopping_results(results: dict, max_products: int) -> List[ProductData]:
    """
    Parse Google Shopping API results into ProductData objects.
    
    Google Shopping result structure:
    {
        "shopping_results": [
            {
                "position": 1,
                "title": "Nike Air Force 1 Black",
                "price": "$190.00",
                "link": "https://culturekings.com.au/products/...",
                "source": "CultureKings",
                "thumbnail": "https://...",
                "extensions": ["Free shipping", "In stock"],
                "rating": 4.5,
                "reviews": 120
            }
        ]
    }
    """
    products = []
    seen_urls = set()  # Track unique products
    
    shopping_results = results.get("shopping_results", [])
    
    if not shopping_results:
        logger.warning("⚠️ No shopping results found. Query might be too specific or no results available.")
        return []
    
    for result in shopping_results[:max_products]:
        try:
            # Extract basic data
            name = result.get("title", "")
            price_raw = result.get("price", "")
            url = result.get("link", "")
            image_url = result.get("thumbnail", "")
            source = result.get("source", "CultureKings")
            
            # Validate required fields
            if not name or not price_raw:
                logger.debug(f"⚠️ Skipping incomplete product: {result.get('title', 'Unknown')}")
                continue
            
            # Validate URL is actually CultureKings
            if url and "culturekings.com.au" not in url.lower():
                logger.debug(f"⚠️ Skipping non-CultureKings URL: {url}")
                continue
            
            # Check for duplicate URLs
            if url in seen_urls:
                logger.debug(f"⚠️ Skipping duplicate product: {name}")
                continue
            
            # Validate URL is a product page (not image/logo)
            if not is_valid_product_url(url):
                logger.debug(f"✗ Rejected invalid URL: {url}")
                continue
            
            seen_urls.add(url)
            
            # Clean price
            clean_price = clean_price_string(price_raw)
            
            # Detect if on sale
            extensions = result.get("extensions", [])
            is_on_sale = any(
                keyword in str(extensions).lower() 
                for keyword in ["sale", "discount", "off", "clearance"]
            )
            
            # Extract rating if available
            rating = result.get("rating")
            reviews = result.get("reviews")
            
            # Create ProductData
            product = ProductData(
                name=name.strip(),
                price=clean_price,
                brand="CultureKings",
                url=url,
                image_url=image_url if image_url else None,
                store_name="CultureKings",
                is_on_sale=is_on_sale,
                extracted_at=datetime.now()
            )
            
            products.append(product)
            logger.debug(f"✓ Added: {name} - {clean_price}")
            
        except Exception as e:
            logger.warning(f"⚠️ Error parsing product: {e}")
            continue
    
    return products


def is_valid_product_url(url: str) -> bool:
    """
    Validate that URL is a real product page.
    
    Rejects:
    - Image URLs (.jpg, .png, etc.)
    - Logo/brand URLs
    - CDN URLs
    """
    if not url:
        return False
    
    url_lower = url.lower()
    
    # Must be CultureKings domain
    if "culturekings.com.au" not in url_lower:
        return False
    
    # Should contain /products/ for product pages
    if "/products/" not in url_lower:
        logger.debug(f"URL missing /products/: {url}")
        return False
    
    # Reject image and CDN URLs
    invalid_patterns = [
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
        'imgix.net', 'cloudinary.com', '/images/', '/assets/',
        'logo', 'brand-', 'icon', '-logo', '/img/', '/thumb/'
    ]
    
    if any(pattern in url_lower for pattern in invalid_patterns):
        logger.debug(f"URL contains invalid pattern: {url}")
        return False
    
    return True


def clean_price_string(price_str: str) -> str:
    """
    Clean and normalize price string from Google Shopping.
    
    Examples:
    - "$190.00" -> "$190.00"
    - "$190" -> "$190.00"
    - "190.00 AUD" -> "$190.00"
    - "$169.95 - $189.95" -> "$169.95" (takes lower price)
    """
    import re
    
    # Handle price ranges - take the lower price
    if '-' in price_str:
        price_str = price_str.split('-')[0].strip()
    
    # Extract numeric price
    price_match = re.search(r'[\d,]+\.?\d*', price_str)
    if not price_match:
        return price_str  # Return original if can't parse
    
    # Clean the price
    price_value = price_match.group().replace(',', '')
    
    try:
        price_float = float(price_value)
        
        # Validate reasonable price range
        if price_float < 5 or price_float > 2000:
            logger.warning(f"⚠️ Unusual price detected: ${price_float}")
        
        # Format consistently with 2 decimal places
        return f"${price_float:.2f}"
    except ValueError:
        return f"${price_value}"


# Test function
if __name__ == "__main__":
    print("🧪 Testing CultureKings Google Shopping scraper...\n")
    
    test_queries = ["black hoodies", "red shoes", "white shirts"]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing: '{query}'")
        print(f"{'='*60}")
        
        products = scrape_culturekings_google_shopping(query, max_products=5)
        
        if products:
            print(f"\n✅ Found {len(products)} products:\n")
            for i, product in enumerate(products, 1):
                print(f"{i}. {product.name}")
                print(f"   💰 {product.price}")
                print(f"   🔗 {product.url}")
                print()
        else:
            print("❌ No products found\n")
        
        # Small delay between tests
        import time
        time.sleep(1)