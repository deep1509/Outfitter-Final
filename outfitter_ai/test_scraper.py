"""
Test scraper with Google Shopping integration.
Tests both Universal Store and CultureKings (via Google Shopping).
"""

import asyncio
import json
from datetime import datetime
from tools.hybrid_scraper import search_all_stores


async def test_search(query: str):
    """Test a search and save results"""
    print(f"\n{'='*60}")
    print(f"Testing search: '{query}'")
    print(f"{'='*60}\n")
    
    try:
        # Run search
        products = await search_all_stores(query, max_products=20)
        
        if not products:
            print(f"⚠️ No products found for '{query}'\n")
            return
        
        # Convert to dict format
        product_dicts = []
        for product in products:
            product_dicts.append({
                "name": product.name,
                "price": product.price,
                "brand": product.brand,
                "url": product.url,
                "image_url": product.image_url,
                "store_name": product.store_name,
                "is_on_sale": product.is_on_sale,
                "extracted_at": product.extracted_at.isoformat() if product.extracted_at else None
            })
        
        # Save to file
        filename = f"test_search_{query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        data = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "products_found": len(product_dicts),
            "products": product_dicts
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Found {len(products)} products")
        print(f"💾 Saved to: {filename}\n")
        
        # Show breakdown by store
        store_counts = {}
        for product in products:
            store_name = product.store_name
            store_counts[store_name] = store_counts.get(store_name, 0) + 1
        
        print("📊 Products by store:")
        for store, count in store_counts.items():
            print(f"   • {store}: {count} products")
        
        # Show first 5 results
        print("\n🎯 First 5 results:")
        for i, product in enumerate(products[:5], 1):
            sale_tag = " 🔥" if product.is_on_sale else ""
            print(f"   {i}. {product.name}{sale_tag}")
            print(f"      💰 {product.price}")
            print(f"      🏪 {product.store_name}")
            if product.url:
                print(f"      🔗 {product.url[:60]}...")
            print()
        
    except Exception as e:
        print(f"❌ Error testing '{query}': {e}")
        import traceback
        traceback.print_exc()


async def test_individual_stores():
    """Test individual store scrapers separately for debugging"""
    print("\n" + "="*60)
    print("TESTING INDIVIDUAL STORES")
    print("="*60)
    
    # Test Universal Store
    print("\n🧪 Testing Universal Store (Firecrawl)...")
    try:
        from tools.universalstore_scraper import scrape_universalstore
        us_products = scrape_universalstore("black hoodies", max_products=5)
        print(f"✅ Universal Store: {len(us_products)} products")
        if us_products:
            print(f"   Sample: {us_products[0].name} - {us_products[0].price}")
    except Exception as e:
        print(f"❌ Universal Store failed: {e}")
    
    # Test CultureKings Google Shopping
    print("\n🧪 Testing CultureKings (Google Shopping)...")
    try:
        from tools.culturekings_google_shopping import scrape_culturekings_google_shopping
        ck_products = scrape_culturekings_google_shopping("black hoodies", max_products=5)
        print(f"✅ CultureKings: {len(ck_products)} products")
        if ck_products:
            print(f"   Sample: {ck_products[0].name} - {ck_products[0].price}")
    except Exception as e:
        print(f"❌ CultureKings failed: {e}")


async def main():
    """Run comprehensive tests"""
    
    # Test individual stores first
    await test_individual_stores()
    
    # Test combined searches
    print("\n\n" + "="*60)
    print("TESTING COMBINED HYBRID SEARCH")
    print("="*60)
    
    test_queries = [
        "black hoodies",
        "red shoes",
        "white shirts",
        "blue jeans"
    ]
    
    for query in test_queries:
        await test_search(query)
        await asyncio.sleep(2)  # Pause between searches to avoid rate limits


def check_environment():
    """Check if required API keys are configured"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("\n" + "="*60)
    print("CHECKING ENVIRONMENT CONFIGURATION")
    print("="*60 + "\n")
    
    required_keys = {
        "FIRECRAWL_API_KEY": "Universal Store scraping",
        "SERPAPI_KEY": "CultureKings Google Shopping"
    }
    
    all_configured = True
    
    for key, purpose in required_keys.items():
        value = os.getenv(key)
        if value:
            print(f"✅ {key}: Configured ({purpose})")
        else:
            print(f"❌ {key}: MISSING - Needed for {purpose}")
            all_configured = False
    
    if not all_configured:
        print("\n⚠️ Missing API keys. Add them to your .env file:")
        print("   FIRECRAWL_API_KEY=your_key_here")
        print("   SERPAPI_KEY=your_key_here")
        print("\n   Get SerpAPI key: https://serpapi.com/ (100 free searches/month)")
        print("   Get Firecrawl key: https://firecrawl.dev/\n")
        return False
    
    print("\n✅ All API keys configured!\n")
    return True


if __name__ == "__main__":
    print("🚀 Starting Enhanced Scraper Tests...")
    print("   • Universal Store: Firecrawl")
    print("   • CultureKings: Google Shopping API")
    
    # Check environment first
    if not check_environment():
        print("\n❌ Please configure API keys before testing.")
        exit(1)
    
    # Run tests
    asyncio.run(main())
    
    print("\n✅ All tests complete!")