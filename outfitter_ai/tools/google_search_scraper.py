"""
Google Search Scraper Tool for Outfitter.ai
Integrates Google Custom Search with the existing scraping system.
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

# Import the Google Custom Search functions
from .google_custom_search import scrape_products_from_google_images, format_for_outfitter

load_dotenv()

class GoogleSearchScraper:
    """
    Google Custom Search scraper that finds products from any Australian store.
    """
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.cx = os.getenv("GOOGLE_CSE_CX")
        
        if not self.api_key or not self.cx:
            raise ValueError("Missing GOOGLE_API_KEY or GOOGLE_CSE_CX in environment variables")
    
    def search_products(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for products using Google Custom Search.
        
        Args:
            query: Search query (will automatically add "australia" if not present)
            num_results: Number of results to return (max 10)
            
        Returns:
            List of product dictionaries formatted for Outfitter.ai
        """
        try:
            print(f"🔍 Google Search: Searching for '{query}'")
            
            # Scrape products using Google Custom Search
            raw_products = scrape_products_from_google_images(query, num=num_results)
            
            # Format for Outfitter.ai
            formatted_products = format_for_outfitter(raw_products)
            
            print(f"✅ Found {len(formatted_products)} products from Google Search")
            return formatted_products
            
        except Exception as e:
            print(f"❌ Google Search error: {e}")
            return []
    
    def search_by_criteria(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search products based on search criteria.
        
        Args:
            criteria: Dictionary containing search parameters like:
                - item_type: "hoodie", "jeans", "shoes", etc.
                - color: "blue", "black", "red", etc.
                - brand: "Nike", "Adidas", etc.
                - gender: "men", "women", "unisex"
                - style: "casual", "formal", "sport", etc.
        
        Returns:
            List of product dictionaries
        """
        # Build search query from criteria
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
        
        # Add additional descriptive terms
        if criteria.get("additional_terms"):
            query_parts.extend(criteria["additional_terms"])
        
        # Join query parts
        query = " ".join(query_parts)
        
        # Ensure Australia is included for geo-targeting
        if "australia" not in query.lower():
            query += " australia"
        
        return self.search_products(query, num_results=criteria.get("num_results", 5))
    
    def search_clothing_items(self, item_type: str, color: Optional[str] = None, 
                            brand: Optional[str] = None, gender: str = "unisex") -> List[Dict[str, Any]]:
        """
        Convenience method for searching clothing items.
        
        Args:
            item_type: Type of clothing (e.g., "hoodie", "jeans", "t-shirt", "shoes")
            color: Color preference (optional)
            brand: Brand preference (optional)
            gender: Target gender ("men", "women", "unisex")
        
        Returns:
            List of product dictionaries
        """
        criteria = {
            "item_type": item_type,
            "color": color,
            "brand": brand,
            "gender": gender,
            "num_results": 5
        }
        
        return self.search_by_criteria(criteria)

# =========================
# Integration with existing system
# =========================
def create_google_search_tool():
    """
    Create a Google Search scraper tool that can be used by the main system.
    """
    return GoogleSearchScraper()

# =========================
# Test function
# =========================
def test_google_search():
    """Test the Google Search scraper"""
    try:
        scraper = GoogleSearchScraper()
        
        # Test 1: Simple search
        print("🧪 Test 1: Simple search")
        results = scraper.search_products("blue hoodies men australia")
        print(f"Found {len(results)} products")
        for i, product in enumerate(results[:3], 1):
            print(f"  {i}. {product['name']} - {product['price']} ({product['store_name']})")
        
        print("\n" + "="*50 + "\n")
        
        # Test 2: Criteria-based search
        print("🧪 Test 2: Criteria-based search")
        criteria = {
            "item_type": "jeans",
            "color": "black",
            "gender": "men",
            "brand": "Levi's"
        }
        results = scraper.search_by_criteria(criteria)
        print(f"Found {len(results)} products")
        for i, product in enumerate(results[:3], 1):
            print(f"  {i}. {product['name']} - {product['price']} ({product['store_name']})")
        
        print("\n" + "="*50 + "\n")
        
        # Test 3: Clothing items search
        print("🧪 Test 3: Clothing items search")
        results = scraper.search_clothing_items("t-shirt", color="white", gender="women")
        print(f"Found {len(results)} products")
        for i, product in enumerate(results[:3], 1):
            print(f"  {i}. {product['name']} - {product['price']} ({product['store_name']})")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_google_search()
