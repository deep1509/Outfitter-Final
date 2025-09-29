"""
Simplified store configuration that focuses on what actually works.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class StoreConfig:
    """Configuration for a single store's scraping parameters"""
    name: str
    base_url: str
    collections_path: str
    selectors: Dict[str, str]
    fallback_selectors: Dict[str, str]
    loading_strategy: str
    max_products_per_search: int
    scroll_pause_time: float
    request_delay: float

# Simplified configs - focus on working basics first
STORE_CONFIGS = {
    "universalstore": StoreConfig(
        name="Universal Store",
        base_url="https://www.universalstore.com",
        collections_path="/collections",
        selectors={
            "product_container": ".product-card",
            "product_name": ".product-card-title",  # From debug: works perfectly
            "product_price": ".amount",  # From debug: clean price format
            "product_image": "img",
            "product_url": "a[href*='/products/']",  # From debug: gets product links
            "sale_badge": ".badge"
        },
        fallback_selectors={
            "product_container": ".grid__item",
            "product_name": ".price, .product-title",  # Fallback options
            "product_price": ".price",
            "product_image": "img",
            "product_url": "a"
        },
        loading_strategy="infinite_scroll",
        max_products_per_search=25,
        scroll_pause_time=3.0,
        request_delay=2.0
    ),
    
    "culturekings": StoreConfig(
        name="CultureKings",
        base_url="https://culturekings.com.au",
        collections_path="/collections",
        selectors={
            "product_container": ".ProductHit_root__2tJkv",
            "product_name": "a[title]",  # From debug: full descriptive names
            "product_price": ".ProductHit_price__p0oAO",
            "product_brand": ".ProductHit_brand__7yw1-",
            "product_image": ".ProductHit_root__2tJkv img",
            "product_url": "a[href*='/products/']",  # From debug: working URLs
            "sale_badge": ".InTileFooterSash_topSash__1wUtj"
        },
        fallback_selectors={
            "product_container": "[data-product]",
            "product_name": ".product-title",
            "product_price": ".price",
            "product_image": "img",
            "product_url": "a"
        },
        loading_strategy="single_page_scroll",
        max_products_per_search=20,
        scroll_pause_time=2.0,
        request_delay=1.5
    )
}


def get_store_config(store_name: str) -> Optional[StoreConfig]:
    """Get configuration for a specific store"""
    return STORE_CONFIGS.get(store_name.lower())

def get_all_store_names() -> List[str]:
    """Get list of all configured store names"""
    return list(STORE_CONFIGS.keys())

def get_all_store_configs() -> Dict[str, StoreConfig]:
    """Get all store configurations"""
    return STORE_CONFIGS