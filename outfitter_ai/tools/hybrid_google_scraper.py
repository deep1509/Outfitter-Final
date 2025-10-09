"""
Hybrid Scraper that combines Google Custom Search with existing store scrapers.
This provides the best of both worlds: specific store results + broader Google search results.
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

# Import existing scrapers
from .culturekings_serper_shopify import CultureKingsSerperShopify
from .universalstore_firecrawl import UniversalStoreFirecrawl
from .google_search_scraper import GoogleSearchScraper

load_dotenv()

class HybridGoogleScraper:
    """
    Hybrid scraper that combines:
    1. Store-specific scrapers (CultureKings, Universal Store)
    2. Google Custom Search for broader results
    """
    
    def __init__(self):
        self.culturekings_scraper = CultureKingsSerperShopify()
        self.universalstore_scraper = UniversalStoreFirecrawl()
        self.google_scraper = GoogleSearchScraper()
        
        print("🔧 Initialized Hybrid Google Scraper")
        print("   ✅ CultureKings Serper Shopify")
        print("   ✅ Universal Store Firecrawl") 
        print("   ✅ Google Custom Search")
    
    def search_products(self, query: str, include_google: bool = True, 
                       include_culturekings: bool = True, include_universalstore: bool = True,
                       max_results_per_source: int = 5) -> List[Dict[str, Any]]:
        """
        Search for products using all available scrapers.
        
        Args:
            query: Search query
            include_google: Whether to include Google Custom Search results
            include_culturekings: Whether to include CultureKings results
            include_universalstore: Whether to include Universal Store results
            max_results_per_source: Maximum results per source
            
        Returns:
            Combined list of products from all sources
        """
        all_products = []
        
        # 1. CultureKings (if enabled)
        if include_culturekings:
            try:
                print(f"🔍 Searching CultureKings for: '{query}'")
                ck_results = self.culturekings_scraper.search_products(query, max_results_per_source)
                if ck_results:
                    all_products.extend(ck_results)
                    print(f"   ✅ Found {len(ck_results)} products from CultureKings")
                else:
                    print(f"   ❌ No results from CultureKings")
            except Exception as e:
                print(f"   ❌ CultureKings error: {e}")
        
        # 2. Universal Store (if enabled)
        if include_universalstore:
            try:
                print(f"🔍 Searching Universal Store for: '{query}'")
                us_results = self.universalstore_scraper.search_products(query, max_results_per_source)
                if us_results:
                    all_products.extend(us_results)
                    print(f"   ✅ Found {len(us_results)} products from Universal Store")
                else:
                    print(f"   ❌ No results from Universal Store")
            except Exception as e:
                print(f"   ❌ Universal Store error: {e}")
        
        # 3. Google Custom Search (if enabled)
        if include_google:
            try:
                print(f"🔍 Searching Google for: '{query}'")
                google_results = self.google_scraper.search_products(query, max_results_per_source)
                if google_results:
                    all_products.extend(google_results)
                    print(f"   ✅ Found {len(google_results)} products from Google Search")
                else:
                    print(f"   ❌ No results from Google Search")
            except Exception as e:
                print(f"   ❌ Google Search error: {e}")
        
        # Remove duplicates based on URL
        unique_products = self._remove_duplicates(all_products)
        
        print(f"🎯 Total unique products found: {len(unique_products)}")
        return unique_products
    
    def search_by_criteria(self, criteria: Dict[str, Any], 
                          include_google: bool = True,
                          include_culturekings: bool = True, 
                          include_universalstore: bool = True) -> List[Dict[str, Any]]:
        """
        Search products based on criteria using all available scrapers.
        
        Args:
            criteria: Search criteria dictionary
            include_google: Whether to include Google Custom Search results
            include_culturekings: Whether to include CultureKings results
            include_universalstore: Whether to include Universal Store results
            
        Returns:
            Combined list of products from all sources
        """
        # Build query from criteria
        query_parts = []
        
        if criteria.get("color"):
            query_parts.append(criteria["color"])
        
        if criteria.get("item_type"):
            query_parts.append(criteria["item_type"])
        
        if criteria.get("brand"):
            query_parts.append(criteria["brand"])
        
        if criteria.get("gender"):
            query_parts.append(criteria["gender"])
        
        if criteria.get("style"):
            query_parts.append(criteria["style"])
        
        if criteria.get("additional_terms"):
            query_parts.extend(criteria["additional_terms"])
        
        query = " ".join(query_parts)
        
        return self.search_products(
            query=query,
            include_google=include_google,
            include_culturekings=include_culturekings,
            include_universalstore=include_universalstore,
            max_results_per_source=criteria.get("num_results", 5)
        )
    
    def _remove_duplicates(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate products based on URL"""
        seen_urls = set()
        unique_products = []
        
        for product in products:
            url = product.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_products.append(product)
        
        return unique_products
    
    def get_source_breakdown(self, products: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of products by source"""
        breakdown = {}
        for product in products:
            store = product.get("store_name", "Unknown")
            breakdown[store] = breakdown.get(store, 0) + 1
        return breakdown

# =========================
# Integration with main system
# =========================
def create_hybrid_scraper():
    """Create a hybrid scraper instance"""
    return HybridGoogleScraper()

# =========================
# Test function
# =========================
def test_hybrid_scraper():
    """Test the hybrid scraper"""
    try:
        scraper = HybridGoogleScraper()
        
        # Test 1: Search with all sources
        print("🧪 Test 1: Search with all sources")
        results = scraper.search_products("blue hoodies men", max_results_per_source=3)
        
        print(f"\n📊 Results breakdown:")
        breakdown = scraper.get_source_breakdown(results)
        for store, count in breakdown.items():
            print(f"   {store}: {count} products")
        
        print(f"\n🎯 Top 5 products:")
        for i, product in enumerate(results[:5], 1):
            print(f"  {i}. {product['name']} - {product['price']} ({product['store_name']})")
        
        print("\n" + "="*60 + "\n")
        
        # Test 2: Search with only Google
        print("🧪 Test 2: Search with only Google Custom Search")
        results = scraper.search_products(
            "black jeans women", 
            include_google=True,
            include_culturekings=False,
            include_universalstore=False,
            max_results_per_source=5
        )
        
        print(f"Found {len(results)} products from Google only")
        for i, product in enumerate(results[:3], 1):
            print(f"  {i}. {product['name']} - {product['price']} ({product['store_name']})")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_hybrid_scraper()
