"""
Simple AI Product Verification
Uses AI to filter products that don't match user requests
"""

from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json

class SimpleProductVerifier:
    """Simple AI-powered product verification"""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    
    def filter_relevant_products(self, 
                                user_request: str, 
                                products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use AI to filter products that actually match the user's request.
        Simple and direct approach.
        """
        
        if not products:
            return products
        
        print(f"🤖 AI VERIFICATION: Filtering {len(products)} products for '{user_request}'")
        
        # Build the verification prompt
        system_prompt = """You are a product filter. Your job is to identify which products actually match what the user asked for.

Return a JSON list of indices (0-based) for products that match the user's request.

MATCHING RULES:
- Category must match (hoodies vs shirts vs pants vs shoes)
- Color should match if specified 
- Don't be too strict on exact wording, but the core category and color should align

EXAMPLES:
User: "black hoodies" 
✅ Keep: "Nike Black Hoodie", "Adidas Hooded Sweatshirt Black"
❌ Filter: "Black T-Shirt", "Grey Hoodie", "Blue Jeans"

Return format: [0, 2, 5] (indices of matching products)"""

        # Build product list for AI
        product_list = []
        for i, product in enumerate(products[:15]):  # Limit to 15 for efficiency
            name = product.get("name", "Unknown")
            product_list.append(f"{i}. {name}")
        
        user_prompt = f"""User requested: "{user_request}"

Products to filter:
{chr(10).join(product_list)}

Return JSON list of indices for products that match the user's request:"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            # Parse AI response
            response_text = response.content.strip()
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\[[\d,\s]*\]', response_text)
            if json_match:
                indices = json.loads(json_match.group())
                
                # Filter products by indices
                relevant_products = []
                for idx in indices:
                    if 0 <= idx < len(products):
                        relevant_products.append(products[idx])
                        print(f"   ✅ KEPT: {products[idx].get('name', 'Unknown')}")
                
                # Show filtered out products
                filtered_out = len(products) - len(relevant_products)
                print(f"   📊 Result: {len(products)} → {len(relevant_products)} products ({filtered_out} filtered out)")
                
                return relevant_products
            else:
                print("   ⚠️ Could not parse AI response, returning all products")
                return products
                
        except Exception as e:
            print(f"   ❌ AI verification error: {e}, returning all products")
            return products