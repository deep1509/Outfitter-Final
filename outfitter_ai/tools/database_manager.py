"""
Product Database Manager for Upsell Agent

Provides efficient querying and filtering of the product database
to enable intelligent upselling and outfit completion.

Key Features:
- Fast product lookup by category
- Smart filtering (color, style, price matching)
- Complementary item suggestions (outfit completion)
- Similar product recommendations
"""

import json
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime


DATABASE_DIR = Path("product_database")


@dataclass
class ProductQuery:
    """Query parameters for product search"""
    category: Optional[str] = None
    colors: Optional[List[str]] = None
    style: Optional[str] = None
    price_tier: Optional[str] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    store: Optional[str] = None
    exclude_urls: Optional[Set[str]] = None  # Exclude already selected items
    limit: int = 10


class ProductDatabaseManager:
    """
    Manages product database queries for intelligent upselling.
    
    Usage:
        db = ProductDatabaseManager()
        
        # Get complementary bottoms for a top
        bottoms = db.get_complementary_items(
            selected_item={"name": "Red Hoodie", "price": "$50"},
            complement_category="bottoms"
        )
        
        # Get similar items
        similar = db.get_similar_items(
            reference_item={"name": "Black Nike Shoes", "price": "$120"},
            same_category=True
        )
    """
    
    def __init__(self, db_path: Path = DATABASE_DIR):
        self.db_path = db_path
        self._cache = {}  # Cache loaded categories
        
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Product database not found at {db_path}. "
                f"Run 'python build_product_database.py --full-rebuild' first."
            )
    
    # ========================================================================
    # CORE QUERY METHODS
    # ========================================================================
    
    def get_products(self, query: ProductQuery) -> List[Dict[str, Any]]:
        """
        Get products matching query parameters.
        
        Args:
            query: ProductQuery with filtering criteria
            
        Returns:
            List of matching products sorted by relevance
        """
        # Load category products
        products = self._load_category_products(query.category, query.store)
        
        # Apply filters
        filtered = self._apply_filters(products, query)
        
        # Sort by relevance
        sorted_products = self._sort_by_relevance(filtered, query)
        
        return sorted_products[:query.limit]
    
    def get_complementary_items(self, selected_item: Dict[str, Any],
                               complement_category: str,
                               limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get items that complement a selected product for outfit completion.
        
        Example:
            User selected: Red Hoodie ($50)
            Returns: Black jeans, grey pants that match style and price tier
        
        Args:
            selected_item: The item user already selected/bought
            complement_category: Category to search (e.g., "bottoms", "shoes")
            limit: Maximum items to return
            
        Returns:
            List of complementary products
        """
        # Extract characteristics from selected item
        selected_colors = selected_item.get("colors", [])
        selected_style = selected_item.get("style", "casual")
        selected_price_tier = selected_item.get("price_tier", "mid")
        
        # Build complementary query
        query = ProductQuery(
            category=complement_category,
            # For colors: suggest neutral or matching colors
            colors=self._get_complementary_colors(selected_colors),
            style=selected_style,  # Match style
            price_tier=selected_price_tier,  # Match price tier
            exclude_urls={selected_item.get("url")},  # Don't suggest same item
            limit=limit
        )
        
        return self.get_products(query)
    
    def get_similar_items(self, reference_item: Dict[str, Any],
                         same_category: bool = True,
                         limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get items similar to a reference product.
        
        Example:
            Reference: Black Nike Hoodie
            Returns: Other black hoodies or similar Nike products
        
        Args:
            reference_item: Item to find similar products to
            same_category: Limit to same category
            limit: Maximum items to return
            
        Returns:
            List of similar products
        """
        category = self._infer_category(reference_item["name"]) if same_category else None
        
        query = ProductQuery(
            category=category,
            colors=reference_item.get("colors", []),
            style=reference_item.get("style"),
            price_tier=reference_item.get("price_tier"),
            exclude_urls={reference_item.get("url")},
            limit=limit
        )
        
        return self.get_products(query)
    
    def get_outfit_suggestions(self, selected_items: List[Dict[str, Any]],
                              budget: Optional[float] = None) -> Dict[str, List[Dict]]:
        """
        Suggest items to complete an outfit based on what user selected.
        
        Example:
            User selected: [Red Hoodie]
            Returns: {
                "bottoms": [Black jeans, Grey pants],
                "shoes": [White sneakers, Black boots],
                "accessories": [Black cap, Grey beanie]
            }
        
        Args:
            selected_items: Items user has already selected
            budget: Optional remaining budget constraint
            
        Returns:
            Dictionary of category -> suggested products
        """
        # Determine which categories are missing
        selected_categories = {self._infer_category(item["name"]) for item in selected_items}
        all_categories = {"tops", "bottoms", "shoes"}
        missing_categories = all_categories - selected_categories
        
        suggestions = {}
        
        for category in missing_categories:
            # Get complementary items for each selected item
            for selected_item in selected_items:
                items = self.get_complementary_items(
                    selected_item,
                    category,
                    limit=3
                )
                
                if category not in suggestions:
                    suggestions[category] = []
                suggestions[category].extend(items)
        
        # Deduplicate and filter by budget
        for category in suggestions:
            suggestions[category] = self._deduplicate_by_url(suggestions[category])
            
            if budget:
                suggestions[category] = self._filter_by_budget(suggestions[category], budget)
            
            # Limit to top 5 per category
            suggestions[category] = suggestions[category][:5]
        
        return suggestions
    
    # ========================================================================
    # INTERNAL HELPER METHODS
    # ========================================================================
    
    def _load_category_products(self, category: Optional[str],
                               store: Optional[str]) -> List[Dict[str, Any]]:
        """Load products from category files"""
        all_products = []
        
        # Determine which stores to search
        stores_to_search = [store] if store else ["culturekings", "universalstore"]
        
        # Determine which categories to search
        categories_to_search = [category] if category else [
            "tops", "bottoms", "shoes", "accessories", "outerwear"
        ]
        
        for store_name in stores_to_search:
            store_dir = self.db_path / store_name
            
            if not store_dir.exists():
                continue
            
            for cat in categories_to_search:
                cache_key = f"{store_name}_{cat}"
                
                # Check cache first
                if cache_key in self._cache:
                    all_products.extend(self._cache[cache_key])
                    continue
                
                # Load from file
                file_path = store_dir / f"{cat}.json"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        products = data.get("products", [])
                        
                        # Add category metadata
                        for product in products:
                            product["_category"] = cat
                        
                        self._cache[cache_key] = products
                        all_products.extend(products)
        
        return all_products
    
    def _apply_filters(self, products: List[Dict], query: ProductQuery) -> List[Dict]:
        """Apply query filters to products"""
        filtered = products
        
        # Filter by colors
        if query.colors:
            filtered = [
                p for p in filtered
                if any(color in p.get("colors", []) for color in query.colors)
            ]
        
        # Filter by style
        if query.style:
            filtered = [
                p for p in filtered
                if p.get("style") == query.style
            ]
        
        # Filter by price tier
        if query.price_tier:
            filtered = [
                p for p in filtered
                if p.get("price_tier") == query.price_tier
            ]
        
        # Filter by price range
        if query.min_price or query.max_price:
            filtered = [
                p for p in filtered
                if self._is_in_price_range(p.get("price"), query.min_price, query.max_price)
            ]
        
        # Exclude URLs
        if query.exclude_urls:
            filtered = [
                p for p in filtered
                if p.get("url") not in query.exclude_urls
            ]
        
        return filtered
    
    def _sort_by_relevance(self, products: List[Dict], query: ProductQuery) -> List[Dict]:
        """Sort products by relevance to query"""
        # Simple scoring system
        def score(product):
            score_val = 0
            
            # Prefer items on sale
            if product.get("is_on_sale"):
                score_val += 10
            
            # Prefer matching colors
            if query.colors and any(c in product.get("colors", []) for c in query.colors):
                score_val += 5
            
            # Prefer matching style
            if query.style and product.get("style") == query.style:
                score_val += 3
            
            return score_val
        
        return sorted(products, key=score, reverse=True)
    
    def _get_complementary_colors(self, selected_colors: List[str]) -> List[str]:
        """Get colors that complement selected colors"""
        # Color matching rules
        complementary_map = {
            "black": ["white", "grey", "navy"],
            "white": ["black", "navy", "blue"],
            "red": ["black", "white", "navy"],
            "blue": ["white", "black", "grey"],
            "navy": ["white", "grey", "tan"],
            "grey": ["black", "white", "navy"],
            "brown": ["cream", "tan", "white"],
            "green": ["black", "brown", "tan"]
        }
        
        complementary = []
        for color in selected_colors:
            if color in complementary_map:
                complementary.extend(complementary_map[color])
        
        # Always include neutrals as safe choices
        neutrals = ["black", "white", "grey", "navy"]
        complementary.extend(neutrals)
        
        return list(set(complementary))  # Deduplicate
    
    def _infer_category(self, product_name: str) -> str:
        """Infer category from product name"""
        name_lower = product_name.lower()
        
        tops_keywords = ["hoodie", "shirt", "tee", "sweater", "jacket", "top"]
        bottoms_keywords = ["jean", "pant", "short", "jogger", "trouser"]
        shoes_keywords = ["shoe", "sneaker", "boot", "sandal"]
        
        if any(k in name_lower for k in tops_keywords):
            return "tops"
        elif any(k in name_lower for k in bottoms_keywords):
            return "bottoms"
        elif any(k in name_lower for k in shoes_keywords):
            return "shoes"
        else:
            return "accessories"
    
    def _is_in_price_range(self, price_str: str, min_price: Optional[float],
                          max_price: Optional[float]) -> bool:
        """Check if price is in range"""
        import re
        
        price_match = re.search(r'\d+\.?\d*', price_str.replace(',', ''))
        if not price_match:
            return False
        
        price = float(price_match.group())
        
        if min_price and price < min_price:
            return False
        if max_price and price > max_price:
            return False
        
        return True
    
    def _deduplicate_by_url(self, products: List[Dict]) -> List[Dict]:
        """Remove duplicate products by URL"""
        seen_urls = set()
        unique_products = []
        
        for product in products:
            url = product.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_products.append(product)
        
        return unique_products
    
    def _filter_by_budget(self, products: List[Dict], budget: float) -> List[Dict]:
        """Filter products under budget"""
        import re
        
        affordable = []
        for product in products:
            price_str = product.get("price", "")
            price_match = re.search(r'\d+\.?\d*', price_str.replace(',', ''))
            
            if price_match:
                price = float(price_match.group())
                if price <= budget:
                    affordable.append(product)
        
        return affordable
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_random_products(self, category: str, count: int = 5) -> List[Dict]:
        """Get random products from category (for testing/browsing)"""
        import random
        
        products = self._load_category_products(category, None)
        
        if len(products) <= count:
            return products
        
        return random.sample(products, count)
    
    def search_by_name(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search products by name"""
        all_products = self._load_category_products(None, None)
        
        search_lower = search_term.lower()
        matches = [
            p for p in all_products
            if search_lower in p.get("name", "").lower()
        ]
        
        return matches[:limit]


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Initialize database manager
    db = ProductDatabaseManager()
    
    print("🗄️ PRODUCT DATABASE MANAGER - EXAMPLES\n")
    
    # Example 1: Get complementary items
    print("=" * 70)
    print("EXAMPLE 1: Get bottoms to match a red hoodie")
    print("=" * 70)
    
    selected_hoodie = {
        "name": "Red Hoodie",
        "price": "$50",
        "colors": ["red"],
        "style": "streetwear",
        "price_tier": "mid"
    }
    
    complementary_bottoms = db.get_complementary_items(
        selected_hoodie,
        "bottoms",
        limit=5
    )
    
    for i, item in enumerate(complementary_bottoms, 1):
        print(f"{i}. {item['name']} - {item['price']}")
    
    # Example 2: Complete outfit
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Complete outfit for selected items")
    print("=" * 70)
    
    selected_items = [
        {"name": "Black Hoodie", "price": "$60", "colors": ["black"], "style": "casual", "price_tier": "mid"}
    ]
    
    outfit = db.get_outfit_suggestions(selected_items, budget=150)
    
    for category, items in outfit.items():
        print(f"\n{category.upper()}:")
        for item in items:
            print(f"  • {item['name']} - {item['price']}")
    
    # Example 3: Search
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Search for 'nike'")
    print("=" * 70)
    
    nike_products = db.search_by_name("nike", limit=5)
    for item in nike_products:
        print(f"  • {item['name']} - {item['price']}")