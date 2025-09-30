"""
Intelligent AI Product Verification
Uses advanced AI reasoning to match products with user requests.
Handles edge cases, color variations, and provides smart fallbacks.
"""

from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re

class SimpleProductVerifier:
    """AI-powered product verifier with intelligent matching and fallbacks"""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.2)  # Use GPT-4o for better reasoning
    
    def filter_relevant_products(self, 
                                user_request: str, 
                                products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use advanced AI to intelligently match products with user requests.
        Handles color variations, category matching, and smart fallbacks.
        """
        
        if not products:
            return products
        
        print(f"🤖 AI VERIFICATION: Filtering {len(products)} products for '{user_request}'")
        
        # Build enhanced system prompt with smart matching rules
        system_prompt = """You are an intelligent product matching assistant for a fashion e-commerce platform.

Your job: Determine which products are RELEVANT to the user's request, using smart fashion knowledge.

INTELLIGENT MATCHING RULES:

**Category Matching (Strict):**
- User wants "hoodies" → Only show hoodies, sweatshirts, pullovers (NOT shirts, pants, shoes)
- User wants "shirts" → Only show shirts, tees, tops (NOT hoodies, jackets)
- User wants "pants" → Only show pants, jeans, trousers (NOT shorts, joggers unless specified)

**Color Matching (Flexible but Smart):**
- EXACT matches always work: "black hoodie" request → "Black Hoodie" product ✅
- COLOR VARIATIONS are okay:
  - "red" matches: crimson, burgundy, maroon, wine red
  - "blue" matches: navy, royal blue, sky blue, denim blue
  - "white" matches: off-white, cream, ivory, bone white
  - "black" matches: jet black, carbon black, onyx, midnight black
- If user specifies color but product is DIFFERENT color → Filter it out
- If user doesn't specify color → Show all colors

**Smart Fallback Logic:**
- If NO products match the exact color, consider showing close alternatives
- If user asks for "red hoodies" but only black/grey exist, those are NOT relevant
- Better to return empty than show wrong products

**Product Name Analysis:**
- Analyze the FULL product name carefully
- Colors are usually mentioned in the name: "Hoodie Black", "Red Sweatshirt", etc.
- Look for category keywords: "hoodie", "sweatshirt", "pullover" are all hoodies

EXAMPLES:

User: "black hoodies"
Products:
1. "Nike Black Hoodie" → ✅ MATCH (exact)
2. "Adidas Jet Black Sweatshirt" → ✅ MATCH (sweatshirt = hoodie, jet black = black)
3. "Grey Hoodie" → ❌ NO MATCH (wrong color)
4. "Black T-Shirt" → ❌ NO MATCH (wrong category)

User: "red hoodies"  
Products:
1. "Burgundy Hoodie" → ✅ MATCH (burgundy is red variation)
2. "Black Hoodie" → ❌ NO MATCH (black ≠ red)
3. "Red T-Shirt" → ❌ NO MATCH (wrong category)

User: "hoodies" (no color specified)
Products:
1. "Black Hoodie" → ✅ MATCH (any color ok)
2. "Red Sweatshirt" → ✅ MATCH (sweatshirt = hoodie)
3. "Blue T-Shirt" → ❌ NO MATCH (wrong category)

Return a JSON object with:
{
  "relevant_indices": [0, 1, 5],
  "reasoning": "brief explanation of matching logic",
  "match_quality": "exact" or "partial" or "none"
}"""

        # Build product analysis with more context
        product_analysis = []
        for i, product in enumerate(products[:20]):  # Increased to 20
            name = product.get("name", "Unknown")
            brand = product.get("brand", "")
            store = product.get("store_name", "")
            
            product_analysis.append(f"{i}. {name} (from {store})")
        
        user_prompt = f"""User Request: "{user_request}"

Available Products:
{chr(10).join(product_analysis)}

Analyze each product and determine which ones MATCH the user's request.
Consider category, color (if specified), and use smart fashion knowledge.

Return JSON with relevant product indices and your reasoning:"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            # Parse AI response
            response_text = response.content.strip()
            print(f"🧠 AI Analysis: {response_text[:200]}...")
            
            # Extract JSON from response
            json_match = re.search(r'\{[^}]*"relevant_indices"[^}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                indices = result.get("relevant_indices", [])
                reasoning = result.get("reasoning", "")
                match_quality = result.get("match_quality", "unknown")
                
                print(f"📊 Match Quality: {match_quality}")
                print(f"💭 Reasoning: {reasoning}")
                
                # Filter products by indices
                relevant_products = []
                for idx in indices:
                    if 0 <= idx < len(products):
                        relevant_products.append(products[idx])
                        print(f"   ✅ KEPT: {products[idx].get('name', 'Unknown')}")
                
                filtered_out = len(products) - len(relevant_products)
                print(f"   📊 Result: {len(products)} → {len(relevant_products)} products ({filtered_out} filtered out)")
                
                return relevant_products
            
            else:
                # Fallback: Try simpler JSON parsing
                return self._fallback_parsing(response_text, products)
                
        except Exception as e:
            print(f"   ❌ AI verification error: {e}")
            return self._rule_based_fallback(user_request, products)
    
    def _fallback_parsing(self, response_text: str, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback parsing if structured JSON doesn't work"""
        print("⚠️ Using fallback parsing...")
        
        # Try to find a simple list of numbers
        numbers = re.findall(r'\b(\d+)\b', response_text)
        indices = [int(n) for n in numbers if int(n) < len(products)]
        
        if indices:
            relevant = [products[i] for i in indices]
            print(f"   📊 Fallback: Found {len(relevant)} products")
            return relevant
        
        # If no indices found, be conservative - return all products
        print("   ⚠️ Could not parse response, returning all products")
        return products
    
    def _rule_based_fallback(self, user_request: str, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rule-based fallback when AI completely fails"""
        print("🔧 Using rule-based fallback matching...")
        
        request_lower = user_request.lower()
        
        # Extract category and color from request
        category_keywords = {
            "hoodies": ["hoodie", "sweatshirt", "pullover", "jumper"],
            "shirts": ["shirt", "tee", "t-shirt", "top"],
            "pants": ["pants", "jeans", "trousers", "chino"],
            "shoes": ["shoe", "sneaker", "boot", "trainer"]
        }
        
        color_keywords = ["black", "white", "red", "blue", "green", "grey", "gray", "navy", "brown"]
        
        # Determine what user wants
        user_category = None
        user_color = None
        
        for category, keywords in category_keywords.items():
            if any(kw in request_lower for kw in keywords):
                user_category = category
                break
        
        for color in color_keywords:
            if color in request_lower:
                user_color = color
                break
        
        # Filter products
        relevant = []
        for product in products:
            name_lower = product.get("name", "").lower()
            
            # Check category match
            if user_category:
                category_match = any(kw in name_lower for kw in category_keywords.get(user_category, []))
                if not category_match:
                    continue
            
            # Check color match (if user specified color)
            if user_color:
                # If user wants specific color, product must have it
                if user_color not in name_lower:
                    continue
            
            relevant.append(product)
        
        print(f"   📊 Rule-based: {len(products)} → {len(relevant)} products")
        return relevant