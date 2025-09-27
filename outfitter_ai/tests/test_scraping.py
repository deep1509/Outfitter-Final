"""
Test script for the scraping tools.
Run this to verify that our store configurations and scraping work correctly.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.scraping_tools import StoreProductScraper, MultiStoreScraper, search_single_store, search_all_stores
from config.store_config import get_all_store_names

async def test_single_store(store_name: str, query: str = "hoodie"):
    """Test scraping a single store"""
    print(f"\n{'='*50}")
    print(f"Testing {store_name} with query: '{query}'")
    print(f"{'='*50}")
    
    try:
        start_time = datetime.now()
        products = await search_single_store(store_name, query, max_products=5)
        end_time = datetime.now()
        
        print(f"⏱️  Time taken: {(end_time - start_time).total_seconds():.2f} seconds")
        print(f"📦 Found {len(products)} products")
        
        if products:
            print("\n🎯 Sample Products:")
            for i, product in enumerate(products[:3], 1):
                print(f"\n{i}. {product.name}")
                print(f"   💰 Price: {product.price}")
                print(f"   🏪 Store: {product.store_name}")
                print(f"   🔗 URL: {product.url[:60]}..." if product.url and len(product.url) > 60 else f"   🔗 URL: {product.url}")
                if product.is_on_sale:
                    print(f"   🔥 ON SALE!")
        else:
            print("❌ No products found!")
            
    except Exception as e:
        print(f"❌ Error testing {store_name}: {e}")

async def test_all_stores(query: str = "black hoodie"):
    """Test scraping all stores"""
    print(f"\n{'='*60}")
    print(f"Testing ALL STORES with query: '{query}'")
    print(f"{'='*60}")
    
    try:
        start_time = datetime.now()
        products = await search_all_stores(query, max_products=15)
        end_time = datetime.now()
        
        print(f"⏱️  Total time: {(end_time - start_time).total_seconds():.2f} seconds")
        print(f"📦 Total products found: {len(products)}")
        
        # Group by store
        store_counts = {}
        for product in products:
            store_counts[product.store_name] = store_counts.get(product.store_name, 0) + 1
        
        print(f"\n📊 Products per store:")
        for store, count in store_counts.items():
            print(f"   {store}: {count} products")
        
        if products:
            print(f"\n🎯 Top 5 Results:")
            for i, product in enumerate(products[:5], 1):
                sale_indicator = " 🔥" if product.is_on_sale else ""
                print(f"\n{i}. {product.name}{sale_indicator}")
                print(f"   💰 {product.price} | 🏪 {product.store_name}")
                
    except Exception as e:
        print(f"❌ Error testing all stores: {e}")

async def test_store_configurations():
    """Test that all store configurations are valid"""
    print(f"\n{'='*50}")
    print("Testing Store Configurations")
    print(f"{'='*50}")
    
    store_names = get_all_store_names()
    print(f"📋 Configured stores: {', '.join(store_names)}")
    
    for store_name in store_names:
        try:
            scraper = StoreProductScraper(store_name)
            print(f"✅ {scraper.config.name} configuration loaded successfully")
            print(f"   Base URL: {scraper.config.base_url}")
            print(f"   Loading strategy: {scraper.config.loading_strategy}")
        except Exception as e:
            print(f"❌ {store_name} configuration error: {e}")

async def main():
    """Run all tests"""
    print("🚀 Starting Outfitter.ai Scraping Tests")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Store configurations
    await test_store_configurations()
    
    # Test 2: Individual stores
    store_names = get_all_store_names()
    for store_name in store_names:
        await test_single_store(store_name, "hoodie")
        await asyncio.sleep(2)  # Be nice to the servers
    
    # Test 3: All stores together
    await test_all_stores("black hoodie")
    
    print(f"\n{'='*60}")
    print("🎉 All tests completed!")
    print(f"{'='*60}")

if __name__ == "__main__":
    # Run the tests
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()