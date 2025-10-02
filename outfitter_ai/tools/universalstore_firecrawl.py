"""
Universal Store scraper using Firecrawl (working perfectly)
"""

import os
import logging
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
    """Parse Universal Store markdown"""
    products = []
    lines = markdown.split('\n')
    
    current_product = {}
    for line in lines:
        if 'products/' in line and 'universalstore.com' in line:
            import re
            url_match = re.search(r'https://[^\s\)]+', line)
            if url_match:
                current_product['url'] = url_match.group()
        
        if '$' in line and any(char.isdigit() for char in line):
            import re
            price_match = re.search(r'\$\d+(?:\.\d{2})?', line)
            if price_match:
                current_product['price'] = price_match.group()
        
        if line.strip().startswith('#') or '](http' in line:
            import re
            text = re.sub(r'\[|\]|\(http[^\)]+\)|#+', '', line).strip()
            if text and len(text) > 5 and not any(skip in text.lower() for skip in ['shop', 'view', 'quick']):
                current_product['name'] = text
        
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
            
            if len(products) >= max_products:
                break
    
    return products