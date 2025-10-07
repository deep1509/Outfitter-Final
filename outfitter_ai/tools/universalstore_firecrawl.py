"""
Universal Store scraper using Firecrawl (working perfectly)
"""

import os
import logging
import re
from typing import List
from datetime import datetime
from dotenv import load_dotenv

from firecrawl import FirecrawlApp
from agents.state import ProductData
from config.universal_store_urls import get_category_url

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_universalstore(query: str, max_products: int = 15) -> List[ProductData]:
    """
    Scrape Universal Store using Firecrawl
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.error("FIRECRAWL_API_KEY not found")
        return []
    
    app = FirecrawlApp(api_key=api_key)
    category_url = get_category_url(query)
    
    logger.info(f"🔥 Firecrawl: {category_url}")
    
    try:
        result = app.scrape(category_url, formats=['markdown'])
        markdown_content = getattr(result, 'markdown', '')
        
        products = _parse_markdown(markdown_content, max_products)
        logger.info(f"✅ Universal Store: {len(products)} products")
        return products
        
    except Exception as e:
        logger.error(f"❌ Universal Store error: {e}")
        return []

def _parse_markdown(markdown: str, max_products: int) -> List[ProductData]:
    """Parse Universal Store markdown for products"""
    products = []
    lines = markdown.split('\n')
    
    current_product = {}
    for line in lines:
        # Look for product URLs
        if 'products/' in line and 'universalstore.com' in line:
            url_match = re.search(r'https://[^\s\)]+', line)
            if url_match:
                current_product['url'] = url_match.group()
        
        # Extract image URLs (look for markdown image syntax or direct image URLs)
        if '![' in line and '](' in line:
            # Markdown image syntax: ![alt](url)
            img_match = re.search(r'!\[.*?\]\(([^)]+)\)', line)
            if img_match:
                current_product['image_url'] = img_match.group(1)
        elif any(ext in line.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) and 'http' in line:
            # Direct image URL
            img_match = re.search(r'https://[^\s\)]+\.(jpg|jpeg|png|webp)', line, re.IGNORECASE)
            if img_match:
                current_product['image_url'] = img_match.group(0)
        
        # Extract price information
        if '$' in line and any(char.isdigit() for char in line):
            price = extract_price_from_text(line)
            if price != "Price not available":
                current_product['price'] = price
                current_product['is_on_sale'] = '~~' in line
        
        # Extract product name
        if line.strip().startswith('#') or '](http' in line:
            text = re.sub(r'\[|\]|\(http[^\)]+\)|#+', '', line).strip()
            if text and len(text) > 5 and not any(skip in text.lower() for skip in ['shop', 'view', 'quick']):
                # Clean the product name
                clean_name = clean_product_name(text)
                if clean_name:
                    current_product['name'] = clean_name
        
        # Create product when we have both name and price
        if current_product.get('name') and current_product.get('price'):
            # Clean up image URL if it exists and optimize for high resolution
            image_url = current_product.get('image_url')
            if image_url and not image_url.startswith('http'):
                # Convert relative URLs to absolute
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url.startswith('/'):
                    image_url = 'https://www.universalstore.com' + image_url
            
            # Optimize Universal Store image URL for higher resolution
            if image_url and 'universalstore.com' in image_url:
                # Universal Store uses Shopify, so we can optimize the image size
                # Remove existing size parameters and add high-res parameters
                # Original: .../file_20x_crop_center.jpg?v=123456
                # Optimized: .../file.jpg?width=1200&height=1200&v=123456
                
                # Remove size parameters from filename (like _20x_crop_center)
                image_url = re.sub(r'_\d+x[^/]*\.', '.', image_url)
                
                if '?' in image_url:
                    base_url, params = image_url.split('?', 1)
                    # Keep the version parameter but add high-res size parameters
                    if 'v=' in params:
                        version = params.split('v=')[1].split('&')[0]
                        image_url = f"{base_url}?width=1200&height=1200&v={version}"
                    else:
                        image_url = f"{base_url}?width=1200&height=1200"
                else:
                    image_url = f"{image_url}?width=1200&height=1200"
            
            products.append(ProductData(
                name=current_product['name'],
                price=current_product['price'],
                brand="Universal Store",
                url=current_product.get('url'),
                image_url=image_url,
                store_name="Universal Store",
                is_on_sale=current_product.get('is_on_sale', False),
                extracted_at=datetime.now()
            ))
            current_product = {}
            
            if len(products) >= max_products:
                break
    
    return products

def clean_product_name(raw_name: str) -> str:
    """
    Clean product name by removing price and currency information.
    
    Examples:
    "Boxy Hoodie Black$68.00 USD/" → "Boxy Hoodie Black"
    "Cities Hoodie~~$68.00~~ $41.00 USD/" → "Cities Hoodie"
    """
    # Remove strikethrough prices (markdown: ~~price~~)
    name = re.sub(r'~~[^~]+~~', '', raw_name)
    
    # Remove prices ($XX.XX) and currency codes (USD, AUD, etc.)
    name = re.sub(r'\$\d+\.?\d*', '', name)
    name = re.sub(r'\s+(USD|AUD|EUR|GBP)\s*/?', '', name)
    
    # Remove trailing slashes and extra whitespace
    name = name.rstrip('/')
    name = ' '.join(name.split())  # Normalize whitespace
    
    return name.strip()

def extract_price_from_text(text: str) -> str:
    """
    Extract the actual selling price (not strikethrough) from text.
    
    Examples:
    "~~$68.00~~ $41.00 USD/" → "$41.00"
    "$68.00 USD/" → "$68.00"
    """
    # Find all prices (including those in strikethrough)
    all_prices = re.findall(r'\$\d+\.?\d*', text)
    
    if not all_prices:
        return "Price not available"
    
    # If there are strikethrough prices, the last price is usually the sale price
    # ~~$68.00~~ $41.00 → we want $41.00
    if '~~' in text and len(all_prices) >= 2:
        return all_prices[-1]  # Last price is the actual price
    
    # Otherwise, return the first/only price
    return all_prices[0]