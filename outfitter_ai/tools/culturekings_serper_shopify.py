"""
CultureKings scraper using multiple strategies:
1. Serper API for Google Shopping results
2. Direct Shopify collection API
3. Category-based fallback
4. Individual product fetching

This is the main implementation file that provides all the functions
expected by the test files and hybrid scraper.
"""

import os
import re
import json
import logging
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from serpapi import GoogleSearch
from agents.state import ProductData

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scrape_culturekings_serper(query: str, max_products: int = 15) -> List[ProductData]:
    """
    Main CultureKings scraper using Serper API + Shopify fallback.
    
    Strategy:
    1. Try Serper API (Google Shopping) first
    2. Fall back to direct Shopify collection API
    3. Fall back to category-based scraping
    
    Args:
        query: Search query (e.g., "red hoodies", "black shoes")
        max_products: Maximum number of products to return
        
    Returns:
        List of ProductData objects
    """
    logger.info(f"🔍 CultureKings Serper: Searching for '{query}' (max: {max_products})")
    
    # Strategy 1: Try Serper API first
    products = try_serper_search(query, max_products)
    if products:
        logger.info(f"✅ Serper API: Found {len(products)} products")
        return products
    
    # Strategy 2: Try direct Shopify collection API
    logger.info("🔄 Serper failed, trying direct Shopify...")
    products = scrape_direct_shopify(query, max_products)
    if products:
        logger.info(f"✅ Direct Shopify: Found {len(products)} products")
        return products
    
    # Strategy 3: Try category-based fallback
    logger.info("🔄 Direct Shopify failed, trying category fallback...")
    products = scrape_by_category(query, max_products)
    if products:
        logger.info(f"✅ Category fallback: Found {len(products)} products")
        return products
    
    logger.warning("❌ All strategies failed for CultureKings")
    return []


def try_serper_search(query: str, max_products: int) -> List[ProductData]:
    """
    Try to scrape CultureKings using Serper API (Google Shopping).
    
    Args:
        query: Search query
        max_products: Maximum products to return
        
    Returns:
        List of ProductData objects or empty list if failed
    """
    api_key = os.getenv("SERPAPI_KEY")
    
    if not api_key:
        logger.warning("⚠️ SERPAPI_KEY not found, skipping Serper search")
        return []
    
    # Build search query targeting CultureKings
    search_query = f"{query} site:culturekings.com.au"
    
    try:
        # Configure SerpAPI parameters
        params = {
            "engine": "google_shopping",
            "q": search_query,
            "api_key": api_key,
            "num": min(max_products, 20),
            "hl": "en",
            "gl": "au",
        }
        
        # Execute search
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Check for API errors
        if "error" in results:
            logger.warning(f"⚠️ Serper API error: {results['error']}")
            return []
        
        # Parse shopping results
        products = parse_google_shopping_results(results, max_products)
        return products
        
    except Exception as e:
        logger.warning(f"⚠️ Serper search error: {e}")
        return []


def scrape_direct_shopify(category: str, max_products: int) -> List[ProductData]:
    """
    Scrape CultureKings using direct Shopify collection API.
    
    Args:
        category: Category to search (e.g., "hoodies", "shoes")
        max_products: Maximum products to return
        
    Returns:
        List of ProductData objects
    """
    # Map common categories to CultureKings collection handles
    category_mapping = {
        "hoodies": "mens-hoodies",
        "hoodie": "mens-hoodies",
        "shirts": "mens-tops",
        "shirt": "mens-tops",
        "shoes": "mens-shoes",
        "shoe": "mens-shoes",
        "pants": "mens-bottoms",
        "pant": "mens-bottoms",
        "jeans": "mens-bottoms",
        "jean": "mens-bottoms",
        "jackets": "mens-jackets",
        "jacket": "mens-jackets",
        "accessories": "mens-accessories",
        "accessory": "mens-accessories",
    }
    
    # Find best matching category
    category_lower = category.lower()
    collection_handle = None
    
    for key, handle in category_mapping.items():
        if key in category_lower:
            collection_handle = handle
            break
    
    if not collection_handle:
        # Default to general men's collection
        collection_handle = "mens"
    
    # Shopify collection API URL
    base_url = "https://culturekings.com.au"
    api_url = f"{base_url}/collections/{collection_handle}/products.json"
    
    logger.info(f"🛍️ Direct Shopify: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        products_data = data.get("products", [])
        
        if not products_data:
            logger.warning("⚠️ No products found in Shopify collection")
            return []
        
        # Parse products
        products = []
        for product_data in products_data[:max_products]:
            try:
                product = parse_shopify_product(product_data)
                if product:
                    products.append(product)
            except Exception as e:
                logger.debug(f"⚠️ Error parsing product: {e}")
                continue
        
        logger.info(f"✅ Direct Shopify: Found {len(products)} products")
        return products
        
    except Exception as e:
        logger.warning(f"⚠️ Direct Shopify error: {e}")
        return []


def scrape_by_category(category: str, max_products: int) -> List[ProductData]:
    """
    Scrape CultureKings by category using multiple collection endpoints.
    
    Args:
        category: Category to search
        max_products: Maximum products to return
        
    Returns:
        List of ProductData objects
    """
    # Try multiple collection endpoints
    collections = [
        "mens-hoodies",
        "mens-tops", 
        "mens-shoes",
        "mens-bottoms",
        "mens-jackets",
        "mens-accessories"
    ]
    
    all_products = []
    
    for collection in collections:
        if len(all_products) >= max_products:
            break
            
        try:
            products = scrape_direct_shopify(collection, max_products - len(all_products))
            all_products.extend(products)
        except Exception as e:
            logger.debug(f"⚠️ Category {collection} failed: {e}")
            continue
    
    return all_products[:max_products]


def fetch_shopify_product(product_url: str) -> Optional[ProductData]:
    """
    Fetch individual product data from CultureKings using Shopify API.
    
    Args:
        product_url: Full URL to the product page
        
    Returns:
        ProductData object or None if failed
    """
    if not product_url or "culturekings.com.au" not in product_url:
        logger.warning("⚠️ Invalid CultureKings URL")
        return None
    
    # Convert product URL to Shopify API URL
    # Example: /products/nike-air-force-1 -> /products/nike-air-force-1.json
    if not product_url.endswith('.json'):
        if product_url.endswith('/'):
            product_url = product_url[:-1]
        product_url += '.json'
    
    # Ensure it's a full URL
    if not product_url.startswith('http'):
        product_url = f"https://culturekings.com.au{product_url}"
    
    logger.info(f"🛍️ Fetching product: {product_url}")
    
    try:
        response = requests.get(product_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        product_data = data.get("product")
        
        if not product_data:
            logger.warning("⚠️ No product data found")
            return None
        
        product = parse_shopify_product(product_data)
        logger.info(f"✅ Fetched product: {product.name if product else 'Unknown'}")
        return product
        
    except Exception as e:
        logger.warning(f"⚠️ Product fetch error: {e}")
        return None


def parse_google_shopping_results(results: dict, max_products: int) -> List[ProductData]:
    """
    Parse Google Shopping API results into ProductData objects.
    """
    products = []
    seen_urls = set()
    
    shopping_results = results.get("shopping_results", [])
    
    if not shopping_results:
        logger.warning("⚠️ No shopping results found")
        return []
    
    for result in shopping_results[:max_products]:
        try:
            # Extract basic data
            name = result.get("title", "")
            price_raw = result.get("price", "")
            url = result.get("link", "")
            image_url = result.get("thumbnail", "")
            
            # Validate required fields
            if not name or not price_raw:
                continue
            
            # Validate URL is actually CultureKings
            if url and "culturekings.com.au" not in url.lower():
                continue
            
            # Check for duplicate URLs
            if url in seen_urls:
                continue
            
            # Validate URL is a product page
            if not is_valid_product_url(url):
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
            
        except Exception as e:
            logger.debug(f"⚠️ Error parsing shopping result: {e}")
            continue
    
    return products


def parse_shopify_product(product_data: dict) -> Optional[ProductData]:
    """
    Parse Shopify product data into ProductData object.
    
    Args:
        product_data: Raw product data from Shopify API
        
    Returns:
        ProductData object or None if invalid
    """
    try:
        # Extract basic info
        name = product_data.get("title", "")
        handle = product_data.get("handle", "")
        
        if not name:
            return None
        
        # Extract price from variants
        variants = product_data.get("variants", [])
        if not variants:
            return None
        
        # Get first variant for price
        first_variant = variants[0]
        price_raw = first_variant.get("price", "0")
        
        # Convert price to float and format
        try:
            price_float = float(price_raw)
            price = f"${price_float:.2f}"
        except ValueError:
            price = f"${price_raw}"
        
        # Build product URL
        base_url = "https://culturekings.com.au"
        product_url = f"{base_url}/products/{handle}"
        
        # Extract image
        images = product_data.get("images", [])
        image_url = images[0].get("src", "") if images else None
        
        # Check if on sale (compare price with compare_at_price)
        compare_at_price = first_variant.get("compare_at_price")
        is_on_sale = compare_at_price and float(compare_at_price) > float(price_raw)
        
        # Create ProductData
        product = ProductData(
            name=name,
            price=price,
            brand="CultureKings",
            url=product_url,
            image_url=image_url,
            store_name="CultureKings",
            is_on_sale=is_on_sale,
            extracted_at=datetime.now()
        )
        
        return product
        
    except Exception as e:
        logger.debug(f"⚠️ Error parsing Shopify product: {e}")
        return None


def is_valid_product_url(url: str) -> bool:
    """
    Validate that URL is a real product page.
    """
    if not url:
        return False
    
    url_lower = url.lower()
    
    # Must be CultureKings domain
    if "culturekings.com.au" not in url_lower:
        return False
    
    # Should contain /products/ for product pages
    if "/products/" not in url_lower:
        return False
    
    # Reject image and CDN URLs
    invalid_patterns = [
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
        'imgix.net', 'cloudinary.com', '/images/', '/assets/',
        'logo', 'brand-', 'icon', '-logo', '/img/', '/thumb/'
    ]
    
    if any(pattern in url_lower for pattern in invalid_patterns):
        return False
    
    return True


def clean_price_string(price_str: str) -> str:
    """
    Clean and normalize price string.
    """
    # Handle price ranges - take the lower price
    if '-' in price_str:
        price_str = price_str.split('-')[0].strip()
    
    # Extract numeric price
    price_match = re.search(r'[\d,]+\.?\d*', price_str)
    if not price_match:
        return price_str
    
    # Clean the price
    price_value = price_match.group().replace(',', '')
    
    try:
        price_float = float(price_value)
        return f"${price_float:.2f}"
    except ValueError:
        return f"${price_value}"


# Test function
if __name__ == "__main__":
    print("🧪 Testing CultureKings Serper + Shopify scraper...\n")
    
    test_queries = ["black hoodies", "red shoes", "white shirts"]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing: '{query}'")
        print(f"{'='*60}")
        
        products = scrape_culturekings_serper(query, max_products=5)
        
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