"""
Comprehensive Product Database Builder for Upsell Agent

Scrapes maximum products from all stores across all categories and
organizes them into a structured database for intelligent upselling.

Usage:
    python build_product_database.py --full-rebuild
    python build_product_database.py --update-category tops
    python build_product_database.py --stats
"""

import os
import json
import asyncio
import argparse
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

# Import our existing scrapers
from tools.universalstore_firecrawl import scrape_universalstore
from tools.culturekings_serper_shopify import scrape_culturekings_serper
from agents.state import ProductData


# ============================================================================
# CONFIGURATION
# ============================================================================

DATABASE_DIR = Path("product_database")
METADATA_FILE = DATABASE_DIR / "metadata.json"

# Category definitions with their search queries
CATEGORIES = {
    "tops": {
        "subcategories": ["hoodies", "tshirts", "shirts", "sweaters", "tank tops"],
        "queries": [
            "hoodies", "t-shirts", "shirts", "sweaters", "tank tops",
            "long sleeve shirts", "polo shirts", "button up shirts"
        ]
    },
    "bottoms": {
        "subcategories": ["jeans", "pants", "shorts", "joggers"],
        "queries": [
            "jeans", "pants", "shorts", "joggers", "chinos",
            "cargo pants", "sweatpants", "denim jeans"
        ]
    },
    "shoes": {
        "subcategories": ["sneakers", "boots", "sandals", "slides"],
        "queries": [
            "sneakers", "shoes", "boots", "sandals", "slides",
            "running shoes", "basketball shoes", "casual shoes"
        ]
    },
    "accessories": {
        "subcategories": ["hats", "bags", "belts", "watches", "sunglasses"],
        "queries": [
            "hats", "caps", "bags", "backpacks", "belts",
            "watches", "sunglasses", "wallets"
        ]
    },
    "outerwear": {
        "subcategories": ["jackets", "coats", "windbreakers"],
        "queries": [
            "jackets", "coats", "windbreakers", "bombers",
            "puffer jackets", "denim jackets"
        ]
    }
}

# Stores to scrape
STORES = {
    "culturekings": {
        "scraper": scrape_culturekings_serper,
        "name": "CultureKings"
    },
    "universalstore": {
        "scraper": scrape_universalstore,
        "name": "Universal Store"
    }
}


# ============================================================================
# DATABASE BUILDER
# ============================================================================

class ProductDatabaseBuilder:
    """Builds and manages the comprehensive product database"""
    
    def __init__(self):
        self.db_dir = DATABASE_DIR
        self.ensure_directories()
        
    def ensure_directories(self):
        """Create directory structure"""
        self.db_dir.mkdir(exist_ok=True)
        for store in STORES.keys():
            (self.db_dir / store).mkdir(exist_ok=True)
    
    async def build_full_database(self, products_per_query: int = 50):
        """
        Build complete database by scraping all categories from all stores.
        
        Args:
            products_per_query: Maximum products to get per search query
        """
        print("🔨 BUILDING COMPREHENSIVE PRODUCT DATABASE")
        print("=" * 70)
        
        start_time = datetime.now()
        total_products = 0
        
        # Scrape each store
        for store_key, store_config in STORES.items():
            print(f"\n📦 Scraping {store_config['name']}...")
            store_products = await self.scrape_store_categories(
                store_key, 
                store_config, 
                products_per_query
            )
            total_products += store_products
            
        # Update metadata
        self.save_metadata({
            "last_full_rebuild": datetime.now().isoformat(),
            "total_products": total_products,
            "categories": list(CATEGORIES.keys()),
            "stores": list(STORES.keys())
        })
        
        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n{'=' * 70}")
        print(f"✅ DATABASE BUILD COMPLETE")
        print(f"   Total products: {total_products}")
        print(f"   Time taken: {duration:.1f}s")
        print(f"   Location: {self.db_dir}")
    
    async def scrape_store_categories(self, store_key: str, store_config: Dict, 
                                     products_per_query: int) -> int:
        """Scrape all categories for a single store"""
        scraper = store_config["scraper"]
        store_total = 0
        
        for category, category_info in CATEGORIES.items():
            print(f"\n  📁 Category: {category}")
            
            all_products = []
            seen_urls = set()  # Deduplicate by URL
            
            # Scrape each query in the category
            for query in category_info["queries"]:
                print(f"    🔍 Query: '{query}'", end=" ")
                
                try:
                    # Run scraper synchronously (they're not async)
                    products = await asyncio.get_event_loop().run_in_executor(
                        None, scraper, query, products_per_query
                    )
                    
                    # Deduplicate and add
                    new_count = 0
                    for product in products:
                        product_url = product.url if hasattr(product, 'url') else None
                        
                        if product_url and product_url not in seen_urls:
                            seen_urls.add(product_url)
                            all_products.append(self.product_to_dict(product))
                            new_count += 1
                    
                    print(f"→ {new_count} new products")
                    
                    # Small delay between queries
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"→ Error: {e}")
                    continue
            
            # Save category to file
            if all_products:
                self.save_category(store_key, category, all_products)
                store_total += len(all_products)
                print(f"  ✅ Saved {len(all_products)} products to {category}.json")
            else:
                print(f"  ⚠️  No products found for {category}")
        
        return store_total
    
    def product_to_dict(self, product: ProductData) -> Dict[str, Any]:
        """Convert ProductData to enriched dictionary"""
        return {
            "name": product.name,
            "price": product.price,
            "brand": product.brand or "Unknown",
            "url": product.url,
            "image_url": product.image_url,
            "store_name": product.store_name,
            "is_on_sale": product.is_on_sale,
            "extracted_at": product.extracted_at.isoformat() if product.extracted_at else None,
            
            # Add derived fields for upselling
            "colors": self.extract_colors(product.name),
            "style": self.infer_style(product.name),
            "price_tier": self.categorize_price(product.price)
        }
    
    def extract_colors(self, name: str) -> List[str]:
        """Extract color mentions from product name"""
        colors = [
            "black", "white", "red", "blue", "green", "navy",
            "grey", "gray", "brown", "tan", "beige", "cream",
            "pink", "purple", "yellow", "orange", "burgundy"
        ]
        
        name_lower = name.lower()
        found_colors = [color for color in colors if color in name_lower]
        return found_colors if found_colors else ["unknown"]
    
    def infer_style(self, name: str) -> str:
        """Infer style from product name"""
        name_lower = name.lower()
        
        if any(word in name_lower for word in ["oversized", "baggy", "loose"]):
            return "streetwear"
        elif any(word in name_lower for word in ["slim", "fitted", "tailored"]):
            return "fitted"
        elif any(word in name_lower for word in ["vintage", "retro", "classic"]):
            return "vintage"
        elif any(word in name_lower for word in ["sport", "athletic", "performance"]):
            return "athletic"
        else:
            return "casual"
    
    def categorize_price(self, price_str: str) -> str:
        """Categorize price into tiers for matching"""
        import re
        
        price_match = re.search(r'\d+\.?\d*', price_str.replace(',', ''))
        if not price_match:
            return "unknown"
        
        price = float(price_match.group())
        
        if price < 30:
            return "budget"
        elif price < 80:
            return "mid"
        elif price < 150:
            return "premium"
        else:
            return "luxury"
    
    def save_category(self, store_key: str, category: str, products: List[Dict]):
        """Save category products to JSON file"""
        file_path = self.db_dir / store_key / f"{category}.json"
        
        data = {
            "category": category,
            "store": store_key,
            "last_updated": datetime.now().isoformat(),
            "total_products": len(products),
            "products": products
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def save_metadata(self, metadata: Dict):
        """Save database metadata"""
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {
            "total_products": 0,
            "by_store": {},
            "by_category": {},
            "last_updated": None
        }
        
        # Check metadata
        if METADATA_FILE.exists():
            with open(METADATA_FILE, 'r') as f:
                metadata = json.load(f)
                stats["last_updated"] = metadata.get("last_full_rebuild")
        
        # Count products
        for store in STORES.keys():
            store_dir = self.db_dir / store
            if not store_dir.exists():
                continue
                
            store_total = 0
            for category_file in store_dir.glob("*.json"):
                with open(category_file, 'r') as f:
                    data = json.load(f)
                    count = data.get("total_products", 0)
                    store_total += count
                    
                    category = category_file.stem
                    stats["by_category"][category] = stats["by_category"].get(category, 0) + count
            
            stats["by_store"][store] = store_total
            stats["total_products"] += store_total
        
        return stats


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Build product database for upsell agent")
    parser.add_argument("--full-rebuild", action="store_true", 
                       help="Rebuild entire database from scratch")
    parser.add_argument("--update-category", type=str,
                       help="Update specific category only")
    parser.add_argument("--stats", action="store_true",
                       help="Show database statistics")
    parser.add_argument("--products-per-query", type=int, default=50,
                       help="Max products per search query (default: 50)")
    
    args = parser.parse_args()
    
    builder = ProductDatabaseBuilder()
    
    if args.stats:
        # Show statistics
        stats = builder.get_stats()
        print("\n📊 PRODUCT DATABASE STATISTICS")
        print("=" * 70)
        print(f"Total Products: {stats['total_products']}")
        print(f"Last Updated: {stats['last_updated'] or 'Never'}")
        
        print("\n📦 By Store:")
        for store, count in stats['by_store'].items():
            print(f"  {store}: {count} products")
        
        print("\n📁 By Category:")
        for category, count in stats['by_category'].items():
            print(f"  {category}: {count} products")
        
    elif args.full_rebuild:
        # Full database rebuild
        await builder.build_full_database(args.products_per_query)
        
    elif args.update_category:
        # Update specific category
        if args.update_category not in CATEGORIES:
            print(f"❌ Unknown category: {args.update_category}")
            print(f"Available: {', '.join(CATEGORIES.keys())}")
            return
        
        print(f"🔄 Updating category: {args.update_category}")
        # TODO: Implement category-specific update
        
    else:
        print("Please specify an action:")
        print("  --full-rebuild    : Build complete database")
        print("  --update-category : Update specific category")
        print("  --stats          : Show statistics")


if __name__ == "__main__":
    asyncio.run(main())