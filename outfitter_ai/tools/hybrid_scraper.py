"""
Hybrid scraper combining multiple approaches:
- Universal Store: Firecrawl scraping
- CultureKings: Serper API + Shopify JSON API
- Extensible for more stores

This is a drop-in replacement for your existing search_all_stores function.
"""

import os
import logging
import asyncio
from typing import List
from datetime import datetime
from dotenv import load_dotenv

from agents.state import ProductData

# Import individual store scrapers
from tools.universalstore_firecrawl import scrape_universalstore
from tools.culturekings_serper_shopify import scrape_culturekings_serper

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def search_all_stores(query: str, max_products: int = 30) -> List[ProductData]:
    """
    Search all configured stores and combine results.
    
    Store Configuration:
    - Universal Store: Firecrawl scraping
    - CultureKings: Serper API + Shopify JSON API
    
    Args:
        query: Search query (e.g., "red hoodies", "black shoes")
        max_products: Maximum total products to return
        
    Returns:
        Combined list of ProductData from all stores
    """
    logger.info(f"🔍 Searching all stores for: '{query}'")
    
    # Split max_products between stores
    products_per_store = max_products // 2
    
    # Create tasks for parallel execution
    tasks = [
        search_universalstore_async(query, products_per_store),
        search_culturekings_async(query, products_per_store)
    ]
    
    # Run all searches in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Combine results
    all_products = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"❌ Store search failed: {result}")
            continue
        
        if isinstance(result, list):
            all_products.extend(result)
            logger.info(f"✅ Store {i+1}: Found {len(result)} products")
    
    # Sort by store priority (CultureKings first, then Universal Store)
    all_products = sort_products_by_priority(all_products)
    
    # Limit to max_products
    all_products = all_products[:max_products]
    
    logger.info(f"✅ Total products found: {len(all_products)}")
    return all_products


async def search_universalstore_async(query: str, max_products: int) -> List[ProductData]:
    """
    Async wrapper for Universal Store Firecrawl scraping.
    """
    try:
        logger.info(f"🔍 Universal Store: Searching for '{query}'")
        
        # Run sync scraper in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        products = await loop.run_in_executor(
            None, 
            scrape_universalstore, 
            query, 
            max_products
        )
        
        logger.info(f"✅ Universal Store: Found {len(products)} products")
        return products
        
    except Exception as e:
        logger.error(f"❌ Universal Store error: {e}")
        return []


async def search_culturekings_async(query: str, max_products: int) -> List[ProductData]:
    """
    Async wrapper for CultureKings Serper + Shopify scraping.
    Uses Serper API to find product URLs, then fetches data from Shopify's JSON API.
    """
    try:
        logger.info(f"🔍 CultureKings: Searching via Serper + Shopify for '{query}'")
        
        # Run sync scraper in thread pool
        loop = asyncio.get_event_loop()
        products = await loop.run_in_executor(
            None,
            scrape_culturekings_serper,
            query,
            max_products
        )
        
        logger.info(f"✅ CultureKings: Found {len(products)} products")
        return products
        
    except Exception as e:
        logger.error(f"❌ CultureKings error: {e}")
        return []


def sort_products_by_priority(products: List[ProductData]) -> List[ProductData]:
    """
    Sort products by store priority and other factors.
    
    Priority order:
    1. CultureKings (primary store)
    2. Universal Store (secondary)
    3. Sale items first within each store
    4. Alphabetical by name
    """
    store_priority = {
        "CultureKings": 1,
        "Universal Store": 2
    }
    
    return sorted(products, key=lambda p: (
        store_priority.get(p.store_name, 999),  # Store priority
        not p.is_on_sale,  # Sale items first (False < True)
        p.name.lower()  # Alphabetical
    ))


# Convenience function for backward compatibility
async def search_stores_parallel(query: str, max_products: int = 30) -> List[ProductData]:
    """
    Alias for search_all_stores for backward compatibility.
    """
    return await search_all_stores(query, max_products)