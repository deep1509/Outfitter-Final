"""
Enhanced CultureKings scraper using Firecrawl with improved parsing and validation.
Handles markdown extraction with robust product identification and URL validation.
"""

import os
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from agents.state import ProductData
from config.culturekings_urls import get_culturekings_url

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_culturekings(query: str, max_products: int = 15) -> List[ProductData]:
    """
    Scrape CultureKings using Firecrawl with enhanced parsing and validation.
    
    Args:
        query: Search query to determine category
        max_products: Maximum number of products to return
        
    Returns:
        List of validated ProductData objects
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.error("❌ FIRECRAWL_API_KEY not found in environment")
        return []
    
    # Initialize Firecrawl
    app = FirecrawlApp(api_key=api_key)
    
    # Get appropriate category URL
    category_url = get_culturekings_url(query)
    logger.info(f"🔥 CultureKings Firecrawl: {category_url}")
    
    try:
        # Scrape with markdown format
        result = app.scrape(category_url, formats=['markdown'])
        markdown_content = getattr(result, 'markdown', '')
        
        if not markdown_content:
            logger.warning("⚠️ CultureKings: No markdown content returned")
            return []
        
        # Parse markdown into products
        products = parse_markdown_advanced(markdown_content, max_products)
        
        logger.info(f"✅ CultureKings Firecrawl: Found {len(products)} products")
        return products
        
    except Exception as e:
        logger.error(f"❌ CultureKings Firecrawl error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def parse_markdown_advanced(markdown: str, max_products: int) -> List[ProductData]:
    """
    Advanced markdown parser with improved product extraction and validation.
    
    Handles:
    - Product name extraction from various markdown formats
    - Price detection with multiple patterns
    - URL validation (rejects image/logo URLs)
    - Sale detection
    - Duplicate filtering
    """
    products = []
    seen_products = set()  # Track unique products
    
    lines = markdown.split('\n')
    i = 0
    
    while i < len(lines) and len(products) < max_products:
        line = lines[i].strip()
        
        # Try to extract a product from current position
        product = extract_product_from_context(lines, i)
        
        if product:
            # Validate the product
            if is_valid_product(product):
                # Create unique identifier to avoid duplicates
                product_id = f"{product['name']}_{product['price']}"
                
                if product_id not in seen_products:
                    seen_products.add(product_id)
                    
                    # Create ProductData object
                    products.append(ProductData(
                        name=product['name'],
                        price=product['price'],
                        brand=product.get('brand', 'CultureKings'),
                        url=product.get('url'),
                        image_url=product.get('image_url'),
                        store_name="CultureKings",
                        is_on_sale=product.get('is_on_sale', False),
                        extracted_at=datetime.now()
                    ))
                    
                    logger.debug(f"✓ Added: {product['name']} - {product['price']}")
        
        i += 1
    
    return products


def extract_product_from_context(lines: List[str], start_idx: int, context_size: int = 5) -> Optional[Dict]:
    """
    Extract product information from markdown lines with context.
    Looks at surrounding lines to gather complete product info.
    """
    product = {}
    
    # Get context window (current line + surrounding lines)
    end_idx = min(start_idx + context_size, len(lines))
    context_lines = lines[start_idx:end_idx]
    context = '\n'.join(context_lines)
    
    # Extract URL (must be valid product URL)
    url = extract_product_url(context)
    if url:
        product['url'] = url
    
    # Extract price
    price = extract_price(context)
    if price:
        product['price'] = price
    
    # Extract product name
    name = extract_product_name(context)
    if name:
        product['name'] = name
    
    # Detect if on sale
    product['is_on_sale'] = detect_sale(context)
    
    # Only return if we have at least name and price
    if product.get('name') and product.get('price'):
        return product
    
    return None


def extract_product_url(text: str) -> Optional[str]:
    """
    Extract and validate product URL from text.
    Rejects image URLs, logo URLs, and other non-product links.
    """
    # Find all URLs
    url_pattern = r'https://culturekings\.com\.au[^\s\)]*'
    urls = re.findall(url_pattern, text)
    
    for url in urls:
        # Must contain /products/ to be a product page
        if '/products/' not in url:
            continue
        
        # Reject invalid URL patterns
        invalid_patterns = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
            'imgix.net', 'cloudinary', '/images/', '/assets/',
            'logo', 'brand-', 'icon', '-logo', '/img/'
        ]
        
        if any(pattern in url.lower() for pattern in invalid_patterns):
            logger.debug(f"✗ Rejected invalid URL: {url}")
            continue
        
        # Valid product URL found
        return url.split('?')[0]  # Remove query parameters
    
    return None


def extract_price(text: str) -> Optional[str]:
    """
    Extract price from text with multiple pattern support.
    Handles various price formats: $XX.XX, $XX, etc.
    """
    # Try different price patterns
    patterns = [
        r'\$(\d+\.\d{2})',  # $XX.XX
        r'\$(\d+)',          # $XX
        r'(\d+\.\d{2})\s*AUD',  # XX.XX AUD
        r'(\d+)\s*AUD'          # XX AUD
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            price_value = match.group(1)
            # Format consistently
            if '.' not in price_value:
                return f"${price_value}.00"
            return f"${price_value}"
    
    return None


def extract_product_name(text: str) -> Optional[str]:
    """
    Extract product name from markdown text.
    Filters out navigation, headers, and generic text.
    """
    # Skip words that indicate non-product content
    skip_words = [
        'shop', 'view all', 'quick view', 'new arrivals', 'best sellers',
        'featured', 'trending', 'sale', 'categories', 'navigation',
        'menu', 'search', 'cart', 'wishlist', 'account', 'sign in',
        'newsletter', 'subscribe', 'follow us', 'social', 'footer',
        'header', 'mens', 'womens', 'kids', 'home', 'about', 'contact',
        'shipping', 'returns', 'help', 'faq', 'terms', 'privacy'
    ]
    
    # Try to extract from markdown links: [Product Name](url)
    link_pattern = r'\[([^\]]+)\]\(https://culturekings\.com\.au/products/[^\)]+\)'
    link_match = re.search(link_pattern, text)
    if link_match:
        name = link_match.group(1).strip()
        if is_valid_product_name(name, skip_words):
            return clean_product_name(name)
    
    # Try to extract from headers: ## Product Name or ### Product Name
    header_pattern = r'^#{2,4}\s+(.+)$'
    for line in text.split('\n'):
        header_match = re.match(header_pattern, line.strip())
        if header_match:
            name = header_match.group(1).strip()
            if is_valid_product_name(name, skip_words):
                return clean_product_name(name)
    
    # Try to extract from bold text: **Product Name**
    bold_pattern = r'\*\*([^\*]+)\*\*'
    bold_matches = re.findall(bold_pattern, text)
    for match in bold_matches:
        name = match.strip()
        if is_valid_product_name(name, skip_words):
            return clean_product_name(name)
    
    return None


def is_valid_product_name(name: str, skip_words: List[str]) -> bool:
    """Check if extracted text is a valid product name"""
    if not name or len(name) < 5:
        return False
    
    name_lower = name.lower()
    
    # Skip if contains any skip words
    if any(skip in name_lower for skip in skip_words):
        return False
    
    # Skip if too short or too long
    if len(name) < 5 or len(name) > 200:
        return False
    
    # Skip if it's just numbers or symbols
    if not any(c.isalpha() for c in name):
        return False
    
    return True


def clean_product_name(name: str) -> str:
    """Clean and normalize product name"""
    # Remove markdown syntax
    name = re.sub(r'\[|\]|\(http[^\)]+\)', '', name)
    name = re.sub(r'[#\*_]', '', name)
    
    # Remove extra whitespace
    name = ' '.join(name.split())
    
    # Remove leading/trailing punctuation
    name = name.strip('.,;:!?-')
    
    return name.strip()


def detect_sale(text: str) -> bool:
    """Detect if product is on sale"""
    sale_indicators = [
        'sale', 'discount', 'off', 'reduced', 'clearance',
        'was $', 'now $', 'save', '% off'
    ]
    
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in sale_indicators)


def is_valid_product(product: Dict) -> bool:
    """
    Validate that product data is complete and reasonable.
    """
    # Must have name and price
    if not product.get('name') or not product.get('price'):
        return False
    
    name = product['name']
    price = product['price']
    
    # Name validation
    if len(name) < 5 or len(name) > 200:
        return False
    
    # Price validation
    try:
        price_value = float(price.replace('$', ''))
        # Reasonable price range for clothing
        if price_value < 5 or price_value > 1000:
            return False
    except:
        return False
    
    # URL validation (if present)
    if product.get('url'):
        url = product['url']
        if not url.startswith('https://culturekings.com.au/products/'):
            return False
        
        # Final check for invalid URLs
        invalid_patterns = ['.jpg', '.png', 'logo', 'imgix']
        if any(pattern in url.lower() for pattern in invalid_patterns):
            return False
    
    return True


# Backward compatibility function
def parse_markdown(markdown: str, max_products: int) -> List[ProductData]:
    """
    Original parse_markdown function for backward compatibility.
    Routes to the enhanced parser.
    """
    return parse_markdown_advanced(markdown, max_products)