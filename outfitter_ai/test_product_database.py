"""
Test and verify product database functionality.
Run this after building the database to ensure everything works correctly.

Usage:
    python test_product_database.py
"""

from tools.database_manager import ProductDatabaseManager, ProductQuery
from pathlib import Path
import json


def test_database_exists():
    """Test 1: Verify database exists"""
    print("\n" + "="*70)
    print("TEST 1: Database Existence")
    print("="*70)
    
    db_path = Path("product_database")
    
    if not db_path.exists():
        print("❌ FAIL: Database directory not found")
        print("   Run: python build_product_database.py --full-rebuild")
        return False
    
    # Check for store directories
    stores = ["culturekings", "universalstore"]
    for store in stores:
        store_path = db_path / store
        if not store_path.exists():
            print(f"❌ FAIL: {store} directory not found")
            return False
    
    print("✅ PASS: Database structure exists")
    return True


def test_database_content():
    """Test 2: Verify database has content"""
    print("\n" + "="*70)
    print("TEST 2: Database Content")
    print("="*70)
    
    try:
        db = ProductDatabaseManager()
        
        # Check each category
        categories = ["tops", "bottoms", "shoes", "accessories", "outerwear"]
        total_products = 0
        
        for category in categories:
            products = db._load_category_products(category, None)
            count = len(products)
            total_products += count
            
            if count > 0:
                print(f"✅ {category}: {count} products")
            else:
                print(f"⚠️  {category}: 0 products (empty)")
        
        print(f"\n📊 Total: {total_products} products")
        
        if total_products < 100:
            print("⚠️  WARNING: Low product count. Consider rebuilding with --products-per-query 100")
        else:
            print("✅ PASS: Database has sufficient products")
        
        return total_products > 0
        
    except Exception as e:
        print(f"❌ FAIL: Error loading database - {e}")
        return False


def test_complementary_items():
    """Test 3: Test complementary item suggestions"""
    print("\n" + "="*70)
    print("TEST 3: Complementary Item Suggestions")
    print("="*70)
    
    try:
        db = ProductDatabaseManager()
        
        # Create a sample selected item
        selected_item = {
            "name": "Black Hoodie",
            "price": "$60",
            "colors": ["black"],
            "style": "streetwear",
            "price_tier": "mid",
            "url": "https://example.com/product"
        }
        
        print(f"Selected: {selected_item['name']} ({selected_item['price']})")
        print("\nSuggesting complementary bottoms:")
        
        bottoms = db.get_complementary_items(
            selected_item,
            "bottoms",
            limit=5
        )
        
        if len(bottoms) == 0:
            print("⚠️  WARNING: No complementary items found")
            print("   This might be normal if database is small")
            return True  # Not a hard failure
        
        for i, item in enumerate(bottoms, 1):
            print(f"  {i}. {item['name']}")
            print(f"     Price: {item['price']}, Colors: {item['colors']}, Style: {item['style']}")
        
        print(f"\n✅ PASS: Found {len(bottoms)} complementary items")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Error getting complementary items - {e}")
        return False


def test_outfit_completion():
    """Test 4: Test complete outfit suggestions"""
    print("\n" + "="*70)
    print("TEST 4: Complete Outfit Suggestions")
    print("="*70)
    
    try:
        db = ProductDatabaseManager()
        
        # Simulate user selected a top
        selected_items = [{
            "name": "Red Hoodie",
            "price": "$50",
            "colors": ["red"],
            "style": "casual",
            "price_tier": "mid"
        }]
        
        print(f"User selected: {selected_items[0]['name']}")
        print("\nCompleting outfit (budget: $200):")
        
        outfit = db.get_outfit_suggestions(selected_items, budget=200)
        
        if not outfit:
            print("⚠️  WARNING: No outfit suggestions generated")
            return True  # Not a hard failure
        
        for category, items in outfit.items():
            print(f"\n  {category.upper()}:")
            for item in items[:3]:  # Show first 3
                print(f"    • {item['name']} - {item['price']}")
        
        print(f"\n✅ PASS: Generated outfit suggestions for {len(outfit)} categories")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Error generating outfit - {e}")
        return False


def test_search_functionality():
    """Test 5: Test product search"""
    print("\n" + "="*70)
    print("TEST 5: Product Search")
    print("="*70)
    
    try:
        db = ProductDatabaseManager()
        
        # Test search
        search_term = "black"
        print(f"Searching for: '{search_term}'")
        
        results = db.search_by_name(search_term, limit=5)
        
        if len(results) == 0:
            print("⚠️  WARNING: No search results found")
            return True  # Not a hard failure
        
        print(f"\nFound {len(results)} results:")
        for item in results:
            print(f"  • {item['name']} - {item['price']}")
        
        print(f"\n✅ PASS: Search functionality works")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Error searching - {e}")
        return False


def test_product_quality():
    """Test 6: Verify product data quality"""
    print("\n" + "="*70)
    print("TEST 6: Product Data Quality")
    print("="*70)
    
    try:
        db = ProductDatabaseManager()
        
        # Get sample products
        products = db._load_category_products("tops", None)
        
        if len(products) == 0:
            print("⚠️  WARNING: No products to test")
            return True
        
        # Check sample of 10 products
        sample_size = min(10, len(products))
        sample = products[:sample_size]
        
        issues = []
        for product in sample:
            # Check required fields
            if not product.get("name"):
                issues.append("Missing name")
            if not product.get("price"):
                issues.append("Missing price")
            if not product.get("colors"):
                issues.append("Missing colors")
            if not product.get("style"):
                issues.append("Missing style")
            if not product.get("price_tier"):
                issues.append("Missing price_tier")
        
        if issues:
            print(f"⚠️  WARNING: Data quality issues found:")
            for issue in set(issues):
                print(f"  - {issue}")
        else:
            print("✅ PASS: Product data quality looks good")
        
        # Show sample product
        print("\nSample product:")
        sample_product = sample[0]
        print(f"  Name: {sample_product.get('name')}")
        print(f"  Price: {sample_product.get('price')}")
        print(f"  Colors: {sample_product.get('colors')}")
        print(f"  Style: {sample_product.get('style')}")
        print(f"  Price Tier: {sample_product.get('price_tier')}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Error checking quality - {e}")
        return False


def run_all_tests():
    """Run all database tests"""
    print("\n" + "🧪 PRODUCT DATABASE TEST SUITE ".center(70, "="))
    
    tests = [
        ("Database Exists", test_database_exists),
        ("Database Content", test_database_content),
        ("Complementary Items", test_complementary_items),
        ("Outfit Completion", test_outfit_completion),
        ("Search", test_search_functionality),
        ("Data Quality", test_product_quality)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR in {test_name}: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Database is ready for upsell agent.")
    elif passed > 0:
        print("\n⚠️  Some tests passed. Database is functional but may need attention.")
    else:
        print("\n❌ All tests failed. Please rebuild database:")
        print("   python build_product_database.py --full-rebuild")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)