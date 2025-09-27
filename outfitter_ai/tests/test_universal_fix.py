"""
Quick test to verify Universal Store product name extraction fix.
"""

import asyncio
import sys
import os

# Add the project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.scraping_tools import search_single_store

async def test_universal_store_fix():
    """Test if Universal Store product names are now extracted correctly"""
    
    print("🧪 Testing Universal Store product name extraction fix...")
    print("="*60)
    
    try:
        products = await search_single_store("universalstore", "hoodie", max_products=3)
        
        print(f"📦 Found {len(products)} products")
        
        if products:
            print("\n🎯 Product Details:")
            for i, product in enumerate(products, 1):
                print(f"\n{i}. Product Name: '{product.name}'")
                print(f"   💰 Price: {product.price}")
                print(f"   🏪 Store: {product.store_name}")
                print(f"   🔗 URL: {product.url}")
                
                # Check if name looks clean (no HTML tags)
                if '<' in product.name or 'img' in product.name or len(product.name) > 200:
                    print(f"   ❌ Name still contains HTML or is too long!")
                    print(f"   📝 Raw name: {product.name[:100]}...")
                else:
                    print(f"   ✅ Name looks clean!")
                    
        else:
            print("❌ No products found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_universal_store_fix())