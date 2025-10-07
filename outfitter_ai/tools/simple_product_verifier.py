"""
Improved AI Product Verification with Flexible Color Matching
Uses semantic understanding for colors and related product categories
"""

from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re

class SimpleProductVerifier:
    """AI-powered product verification with intelligent color matching"""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    
    def filter_relevant_products(self, 
                                user_request: str, 
                                products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use AI to filter products using semantic understanding.
        Strict on category, flexible on colors and variations.
        """
        
        if not products:
            return products
        
        print(f"🤖 AI VERIFICATION: Filtering {len(products)} products for '{user_request}'")
        
        # Build the intelligent verification prompt
        system_prompt = """You are an intelligent product matcher. Your goal is to find products that reasonably match what the user wants.

MATCHING PHILOSOPHY:
✅ STRICT: Product category must match (hoodies ≠ shirts ≠ pants ≠ shoes)
✅ FLEXIBLE: Colors should match semantically, including similar shades and tones
✅ SMART: Use natural language understanding, not exact keyword matching

COLOR MATCHING RULES:
- This are just examples, be flexible with colors, but don't match totally unrelated colors similar are fine.
- Be semantically flexible with colors - understand color families and variations
- "Red" includes: burgundy, maroon, crimson, wine, ruby, scarlet, coral
- "Black" includes: charcoal, onyx, jet black, midnight
- "Blue" includes: navy, royal blue, sky blue, azure, cobalt, teal
- "White" includes: cream, ivory, off-white, eggshell
- "Grey/Gray" includes: charcoal, slate, silver, ash
- "Green" includes: olive, forest, lime, mint, emerald
- "Brown" includes: tan, beige, camel, khaki, chocolate
- If user doesn't specify color, match any color

CATEGORY MATCHING:
- Hoodies = hooded sweatshirts, pullover hoodies, zip hoodies, hoodie jackets
- Shirts = t-shirts, button-ups, polos, blouses, tops (NOT hoodies)
- Pants = jeans, trousers, chinos, joggers (NOT shorts)
- Shoes = sneakers, boots, trainers, footwear
- Jackets = coats, outerwear, windbreakers (may include hooded jackets)

EXAMPLES:
User: "red hoodies"
✅ KEEP: "Crimson Pullover Hoodie", "Burgundy Zip Hoodie", "Maroon Hooded Sweatshirt"
❌ FILTER: "Red T-Shirt", "Blue Hoodie", "Red Jacket"

User: "black shoes"  
✅ KEEP: "Onyx Sneakers", "Midnight Black Trainers", "Charcoal Running Shoes"
❌ FILTER: "Black Boots" (wait, this is shoes, so actually KEEP), "White Sneakers"

User: "hoodies" (no color specified)
✅ KEEP: Any color hoodie - "Red Hoodie", "Blue Hoodie", "Green Hoodie"
❌ FILTER: "T-Shirt", "Jacket" (unless it's specifically a hooded jacket)

DECISION PROCESS:
1. Does the product category match? If no → filter out
2. If color specified, is it in the same color family? If yes → keep
3. If color doesn't match but category does → STILL KEEP (be very generous)
4. When in doubt, ALWAYS keep the product (be generous, not strict)
5. Only filter out if category clearly doesn't match

IMPORTANT: For "red hoodies" - keep ALL hoodies regardless of color!

Return ONLY a JSON array of indices for products that match: [0, 2, 5, ...]"""

        # Build product list for AI
        product_list = []
        for i, product in enumerate(products):
            name = product.get("name", "Unknown")
            price = product.get("price", "")
            # Include price to help AI understand context
            product_list.append(f"{i}. {name} ({price})")
        
        user_prompt = f"""User is looking for: "{user_request}"

Available products:
{chr(10).join(product_list)}

Think through which products match:
1. What category is the user looking for?
2. What color (if any) did they specify?
3. Which products fit that category and color family?

Return ONLY a JSON array of matching product indices:"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            # Parse AI response
            response_text = response.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\[[\d,\s]*\]', response_text)
            if json_match:
                indices = json.loads(json_match.group())
                
                # Filter products by indices
                relevant_products = []
                filtered_names = []
                
                for idx in indices:
                    if 0 <= idx < len(products):
                        relevant_products.append(products[idx])
                        print(f"   ✅ KEPT: {products[idx].get('name', 'Unknown')}")
                
                # Show filtered out products (for debugging)
                filtered_products = []
                for i, product in enumerate(products):
                    if i not in indices:
                        filtered_names.append(product.get('name', 'Unknown'))
                        filtered_products.append({
                            'index': i,
                            'name': product.get('name', 'Unknown'),
                            'store_name': product.get('store_name', 'Unknown Store'),
                            'category': self._extract_category_from_name(product.get('name', '')),
                            'color': self._extract_color_from_name(product.get('name', ''))
                        })
                
                filtered_count = len(products) - len(relevant_products)
                print(f"   📊 Result: {len(products)} → {len(relevant_products)} products ({filtered_count} filtered out)")
                
                # Show detailed filtering info
                if filtered_products:
                    print(f"   🚫 Filtered products by store:")
                    store_filtered = {}
                    for fp in filtered_products:
                        store = fp['store_name']
                        if store not in store_filtered:
                            store_filtered[store] = []
                        store_filtered[store].append(fp['name'])
                    
                    for store, names in store_filtered.items():
                        print(f"      {store}: {len(names)} products - {', '.join(names[:2])}{'...' if len(names) > 2 else ''}")
                
                # Save detailed filtering analysis
                self._save_filtering_analysis(user_request, products, relevant_products, filtered_products, indices)
                
                return relevant_products
            else:
                print("   ⚠️ Could not parse AI response, keeping all products")
                return products
                
        except Exception as e:
            print(f"   ❌ AI verification error: {e}, keeping all products")
            return products

    def _extract_category_from_name(self, name: str) -> str:
        """Extract category from product name for analysis."""
        name_lower = name.lower()
        
        if any(word in name_lower for word in ['hoodie', 'hooded', 'pullover']):
            return 'hoodie'
        elif any(word in name_lower for word in ['shirt', 't-shirt', 'tee', 'top']):
            return 'shirt'
        elif any(word in name_lower for word in ['pant', 'jean', 'trouser', 'chino']):
            return 'pants'
        elif any(word in name_lower for word in ['shoe', 'sneaker', 'boot', 'trainer', 'footwear']):
            return 'shoes'
        elif any(word in name_lower for word in ['jacket', 'coat', 'outerwear']):
            return 'jacket'
        else:
            return 'unknown'

    def _extract_color_from_name(self, name: str) -> str:
        """Extract color from product name for analysis."""
        name_lower = name.lower()
        
        colors = ['black', 'white', 'red', 'blue', 'green', 'yellow', 'orange', 'purple', 
                 'pink', 'brown', 'grey', 'gray', 'navy', 'beige', 'tan', 'cream', 'ivory']
        
        for color in colors:
            if color in name_lower:
                return color
        
        return 'unknown'

    def _save_filtering_analysis(self, user_request: str, original_products: List[Dict], 
                                kept_products: List[Dict], filtered_products: List[Dict], 
                                kept_indices: List[int]) -> None:
        """Save detailed filtering analysis to JSON file."""
        import json
        from datetime import datetime
        
        # Group by store for analysis
        original_by_store = {}
        kept_by_store = {}
        filtered_by_store = {}
        
        for product in original_products:
            store = product.get('store_name', 'Unknown Store')
            if store not in original_by_store:
                original_by_store[store] = []
            original_by_store[store].append(product)
        
        for product in kept_products:
            store = product.get('store_name', 'Unknown Store')
            if store not in kept_by_store:
                kept_by_store[store] = []
            kept_by_store[store].append(product)
        
        for product in filtered_products:
            store = product.get('store_name', 'Unknown Store')
            if store not in filtered_by_store:
                filtered_by_store[store] = []
            filtered_by_store[store].append(product)
        
        # Calculate filtering rates by store
        store_analysis = {}
        for store in original_by_store.keys():
            original_count = len(original_by_store[store])
            kept_count = len(kept_by_store.get(store, []))
            filtered_count = len(filtered_by_store.get(store, []))
            
            store_analysis[store] = {
                'original_count': original_count,
                'kept_count': kept_count,
                'filtered_count': filtered_count,
                'filtering_rate': f"{(filtered_count / original_count * 100):.1f}%" if original_count > 0 else "0%",
                'kept_rate': f"{(kept_count / original_count * 100):.1f}%" if original_count > 0 else "0%"
            }
        
        # Create analysis data
        analysis_data = {
            'timestamp': datetime.now().isoformat(),
            'user_request': user_request,
            'total_original': len(original_products),
            'total_kept': len(kept_products),
            'total_filtered': len(filtered_products),
            'overall_filtering_rate': f"{(len(filtered_products) / len(original_products) * 100):.1f}%" if original_products else "0%",
            'store_analysis': store_analysis,
            'kept_products': kept_products,
            'filtered_products': filtered_products,
            'kept_indices': kept_indices
        }
        
        # Save to file
        filename = f"ai_filtering_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        print(f"   💾 AI Filtering Analysis saved to: {filename}")


# Example usage and test cases
if __name__ == "__main__":
    verifier = SimpleProductVerifier()
    
    # Test case 1: Red hoodies with color variations
    test_products = [
        {"name": "Crimson Pullover Hoodie", "price": "$50"},
        {"name": "Blue Zip Hoodie", "price": "$45"},
        {"name": "Burgundy Hooded Sweatshirt", "price": "$55"},
        {"name": "Red T-Shirt", "price": "$25"},
        {"name": "Maroon Hoodie", "price": "$48"},
    ]
    
    print("\n" + "="*60)
    print("TEST 1: User wants 'red hoodies'")
    print("="*60)
    results = verifier.filter_relevant_products("red hoodies", test_products)
    print(f"\nExpected: Should keep crimson, burgundy, maroon hoodies")
    print(f"Got: {len(results)} products")
    
    # Test case 2: Just hoodies (any color)
    print("\n" + "="*60)
    print("TEST 2: User wants 'hoodies' (no color)")
    print("="*60)
    results = verifier.filter_relevant_products("hoodies", test_products)
    print(f"\nExpected: Should keep all hoodies regardless of color")
    print(f"Got: {len(results)} products")
    
    # Test case 3: Black shoes with variations
    test_products_2 = [
        {"name": "Onyx Running Shoes", "price": "$80"},
        {"name": "White Sneakers", "price": "$70"},
        {"name": "Charcoal Trainers", "price": "$75"},
        {"name": "Black Hoodie", "price": "$50"},
    ]
    
    print("\n" + "="*60)
    print("TEST 3: User wants 'black shoes'")
    print("="*60)
    results = verifier.filter_relevant_products("black shoes", test_products_2)
    print(f"\nExpected: Should keep onyx and charcoal shoes")
    print(f"Got: {len(results)} products")