"""
Comprehensive test suite for CultureKings scraper.
Tests all strategies and validates product data quality.
"""

import sys
import json
from datetime import datetime
from tools.culturekings_serper_shopify import (
    scrape_culturekings_serper,
    try_serper_search,
    scrape_direct_shopify,
    scrape_by_category,
    fetch_shopify_product
)


def print_separator(char="=", length=70):
    """Print a separator line."""
    print(char * length)


def print_product(product, index=None):
    """Print product details nicely formatted."""
    prefix = f"{index}. " if index else ""
    print(f"{prefix}📦 {product.name}")
    print(f"   💰 Price: {product.price}")
    print(f"   🏪 Store: {product.store_name}")
    if product.url:
        print(f"   🔗 URL: {product.url[:70]}...")
    if product.image_url:
        print(f"   🖼️  Image: {product.image_url[:70]}...")
    if product.is_on_sale:
        print(f"   🔥 ON SALE!")
    print()


def validate_product(product):
    """Validate product has required fields."""
    issues = []
    
    if not product.name or len(product.name) < 3:
        issues.append("Invalid name")
    
    if not product.price or not product.price.startswith('$'):
        issues.append("Invalid price")
    
    if not product.url or 'culturekings.com.au' not in product.url:
        issues.append("Invalid URL")
    
    if product.store_name != "CultureKings":
        issues.append("Wrong store name")
    
    return issues


def test_main_scraper():
    """Test 1: Main scraper function with various queries."""
    print_separator()
    print("TEST 1: Main Scraper Function")
    print_separator()
    
    test_queries = [
        ("black hoodies", 5),
        ("red shoes", 5),
        ("white shirts", 5),
    ]
    
    all_passed = True
    
    for query, max_products in test_queries:
        print(f"\n🔍 Testing query: '{query}' (max: {max_products})")
        print("-" * 70)
        
        products = scrape_culturekings_serper(query, max_products)
        
        if not products:
            print(f"❌ FAILED: No products found for '{query}'")
            all_passed = False
            continue
        
        print(f"✅ Found {len(products)} products\n")
        
        # Show first 2 products
        for i, product in enumerate(products[:2], 1):
            print_product(product, i)
            
            # Validate
            issues = validate_product(product)
            if issues:
                print(f"   ⚠️ Validation issues: {', '.join(issues)}")
                all_passed = False
        
        if len(products) > 2:
            print(f"   ... and {len(products) - 2} more products")
    
    return all_passed


def test_direct_shopify():
    """Test 2: Direct Shopify collection API."""
    print_separator()
    print("TEST 2: Direct Shopify Collection API")
    print_separator()
    
    print("\n🔍 Testing direct Shopify collection scraping")
    print("-" * 70)
    
    products = scrape_direct_shopify("hoodies", 5)
    
    if not products:
        print("❌ FAILED: No products from direct Shopify")
        return False
    
    print(f"✅ Found {len(products)} products from collection API\n")
    
    for i, product in enumerate(products[:3], 1):
        print_product(product, i)
    
    return True


def test_category_fallback():
    """Test 3: Category-based fallback."""
    print_separator()
    print("TEST 3: Category Fallback")
    print_separator()
    
    categories = ["hoodies", "shirts", "shoes"]
    all_passed = True
    
    for category in categories:
        print(f"\n🔍 Testing category: '{category}'")
        print("-" * 70)
        
        products = scrape_by_category(category, 3)
        
        if not products:
            print(f"❌ FAILED: No products for category '{category}'")
            all_passed = False
            continue
        
        print(f"✅ Found {len(products)} products\n")
        
        for i, product in enumerate(products[:2], 1):
            print_product(product, i)
    
    return all_passed


def test_individual_product():
    """Test 4: Fetch individual product by URL."""
    print_separator()
    print("TEST 4: Individual Product Fetch")
    print_separator()
    
    # Test with a known CultureKings product URL
    test_url = "https://www.culturekings.com.au/products/champion-rochester-graphic-hoodie-red-mens"
    
    print(f"\n🔍 Testing individual product fetch")
    print(f"   URL: {test_url}")
    print("-" * 70)
    
    product = fetch_shopify_product(test_url)
    
    if not product:
        print("❌ FAILED: Could not fetch individual product")
        return False
    
    print(f"✅ Successfully fetched product\n")
    print_product(product)
    
    # Validate
    issues = validate_product(product)
    if issues:
        print(f"⚠️ Validation issues: {', '.join(issues)}")
        return False
    
    return True


def test_data_quality():
    """Test 5: Data quality checks."""
    print_separator()
    print("TEST 5: Data Quality Validation")
    print_separator()
    
    print("\n🔍 Testing data quality across multiple products")
    print("-" * 70)
    
    products = scrape_culturekings_serper("hoodies", 10)
    
    if not products:
        print("❌ FAILED: No products to validate")
        return False
    
    print(f"✅ Retrieved {len(products)} products for validation\n")
    
    # Run quality checks
    quality_report = {
        'total': len(products),
        'with_images': sum(1 for p in products if p.image_url),
        'with_urls': sum(1 for p in products if p.url),
        'on_sale': sum(1 for p in products if p.is_on_sale),
        'invalid': 0
    }
    
    for product in products:
        issues = validate_product(product)
        if issues:
            quality_report['invalid'] += 1
    
    # Print report
    print("📊 Quality Report:")
    print(f"   Total products: {quality_report['total']}")
    print(f"   With images: {quality_report['with_images']} ({quality_report['with_images']/quality_report['total']*100:.1f}%)")
    print(f"   With URLs: {quality_report['with_urls']} ({quality_report['with_urls']/quality_report['total']*100:.1f}%)")
    print(f"   On sale: {quality_report['on_sale']}")
    print(f"   Invalid: {quality_report['invalid']}")
    
    # Pass if at least 80% have images and URLs
    passed = (quality_report['with_images'] >= quality_report['total'] * 0.8 and
              quality_report['with_urls'] >= quality_report['total'] * 0.8 and
              quality_report['invalid'] == 0)
    
    if passed:
        print("\n✅ Data quality test PASSED")
    else:
        print("\n❌ Data quality test FAILED")
    
    return passed


def save_test_results(results):
    """Save test results to JSON file."""
    filename = f"test_results_culturekings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Test results saved to: {filename}")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("🧪 CULTUREKINGS SCRAPER - COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # Run all tests
    tests = [
        ("Main Scraper", test_main_scraper),
        ("Direct Shopify API", test_direct_shopify),
        ("Category Fallback", test_category_fallback),
        ("Individual Product", test_individual_product),
        ("Data Quality", test_data_quality),
    ]
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results['tests'][test_name] = {
                'status': 'PASSED' if passed else 'FAILED',
                'passed': passed
            }
        except Exception as e:
            print(f"\n❌ ERROR in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results['tests'][test_name] = {
                'status': 'ERROR',
                'passed': False,
                'error': str(e)
            }
    
    # Print summary
    print_separator()
    print("📊 TEST SUMMARY")
    print_separator()
    
    total_tests = len(tests)
    passed_tests = sum(1 for t in results['tests'].values() if t['passed'])
    
    for test_name, result in results['tests'].items():
        status = "✅" if result['passed'] else "❌"
        print(f"{status} {test_name}: {result['status']}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! CultureKings scraper is working perfectly.")
    elif passed_tests > 0:
        print(f"\n⚠️ PARTIAL SUCCESS: {passed_tests} out of {total_tests} tests passed.")
    else:
        print("\n❌ ALL TESTS FAILED. CultureKings scraper needs debugging.")
    
    # Save results
    save_test_results(results)
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)