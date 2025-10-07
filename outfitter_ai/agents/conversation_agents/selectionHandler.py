"""
Selection Handler Agent - Stage 3
Parses user product selections from natural language without variant complexity.
Uses default sizes for simplicity.
"""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agents.state import OutfitterState
import re


class SelectionHandler:
    """
    AI-powered selection handler that understands natural language product selections.
    Simplified version without variant extraction - uses defaults.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    

    def handle_selection(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Main handler for processing product selections.
        FIXED: Uses pending_cart_additions to preserve existing cart
        """
        print("🛒 SelectionHandler: Processing product selection...")
        
        products_shown = state.get("products_shown", [])
        
        if not products_shown:
            return {
                "messages": [{"role": "assistant", "content": "I don't see any products that were shown to select from. Would you like me to search for something?"}],
                "conversation_stage": "discovery",
                "next_step": "needs_analyzer"
            }
        
        # Get user's latest message
        messages = state.get("messages", [])
        user_message = ""
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'human':
                user_message = msg.content
                break
            elif isinstance(msg, dict) and msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break
        
        if not user_message:
            return {
                "messages": [{"role": "assistant", "content": "I didn't catch that. Which products would you like?"}],
                "conversation_stage": "presenting",
                "next_step": "wait_for_user"
            }
        
        print(f"   User input: '{user_message}'")
        print(f"   Available products: {len(products_shown)}")
        
        # Parse selections using AI
        selected_indices = self._parse_selections_with_ai(user_message, len(products_shown))
        
        if not selected_indices:
            return self._handle_no_selection(user_message, products_shown)
        
        # Get selected products with default variants
        newly_selected = []
        for idx in selected_indices:
            if 0 <= idx < len(products_shown):
                product = products_shown[idx].copy()
                # Add default variant info
                product['selected_variant'] = 'default'
                product['selected_size'] = 'M'
                newly_selected.append(product)
        
        print(f"   ✓ Selected {len(newly_selected)} products")
        
        # CRITICAL FIX: Get existing cart and preserve it
        existing_cart = state.get("selected_products", [])
        
        # CRITICAL FIX: Don't create message here - let cart_manager handle confirmation
        # The cart_manager will create the proper confirmation message
        return {
            "pending_cart_additions": newly_selected,  # NEW items to add
            "selected_products": existing_cart,  # PRESERVE existing cart
            "conversation_stage": "cart",
            "next_step": "cart_manager",  # Route to cart_manager to merge
            "awaiting_cart_action": True
        }

    def _parse_selections_with_ai(self, user_message: str, num_products: int) -> List[int]:
        """
        Use AI to parse product selections from natural language.
        Returns 0-based indices.
        """
        # First try simple number extraction (more reliable)
        numbers = re.findall(r'\b(\d+)\b', user_message)
        if numbers:
            # Convert to 0-based indices
            indices = [int(n) - 1 for n in numbers]
            valid_indices = [i for i in indices if 0 <= i < num_products]
            if valid_indices:
                print(f"   Fallback parsed indices: {valid_indices}")
                return valid_indices
        
        # Try to extract product references like "product 9" or "option 2"
        product_refs = re.findall(r'(?:product|option|item|choice)\s+(\d+)', user_message, re.IGNORECASE)
        if product_refs:
            indices = [int(n) - 1 for n in product_refs]
            valid_indices = [i for i in indices if 0 <= i < num_products]
            if valid_indices:
                print(f"   Product reference parsed indices: {valid_indices}")
                return valid_indices
        
        # Then try AI parsing for more complex cases
        system_prompt = """You are a selection parser. Extract product numbers from user messages.

Users can reference products in many ways:
- Numbers: "I want #2 and #5" → [1, 4] (convert to 0-based)
- Ordinals: "the first and third one" → [0, 2]
- References: "the red hoodie" → try to match by description
- Multiple: "show me 1, 3, and 5" → [0, 2, 4]

IMPORTANT:
- Convert 1-based numbers to 0-based indices (user says "1" = index 0)
- Only return indices that exist (0 to N-1)
- If unclear or no selection, return empty list

Return ONLY a JSON array of indices: [0, 2, 4]"""

        user_prompt = f"""User message: "{user_message}"

Number of products shown: {num_products}

Parse which products the user wants. Return JSON array of 0-based indices:"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            response_text = response.content.strip()
            
            # Extract JSON array
            import json
            json_match = re.search(r'\[[\d,\s]*\]', response_text)
            
            if json_match:
                indices = json.loads(json_match.group())
                # Validate indices
                valid_indices = [i for i in indices if 0 <= i < num_products]
                
                print(f"   AI parsed indices: {valid_indices}")
                return valid_indices
            
            return []
            
        except Exception as e:
            print(f"   Parse error: {e}")
            return []
    
    def _handle_no_selection(self, user_message: str, products_shown: List[Dict]) -> Dict[str, Any]:
        """Handle cases where no valid selection was made."""
        
        # Check if user is asking questions about products
        question_keywords = ['how', 'what', 'which', 'where', 'when', 'size', 'color', 'price', 'available', 'good', 'summer', 'winter', 'quality', 'material']
        
        if any(keyword in user_message.lower() for keyword in question_keywords):
            # Check if they're asking about a specific product by number
            product_refs = re.findall(r'(?:product|option|item|choice)\s+(\d+)', user_message, re.IGNORECASE)
            if product_refs:
                # They're asking about a specific product - treat as selection
                indices = [int(n) - 1 for n in product_refs]
                valid_indices = [i for i in indices if 0 <= i < len(products_shown)]
                if valid_indices:
                    # Process as selection
                    newly_selected = []
                    for idx in valid_indices:
                        product = products_shown[idx].copy()
                        product['selected_variant'] = 'default'
                        product['selected_size'] = 'M'
                        newly_selected.append(product)
                    
                    return {
                        "pending_cart_additions": newly_selected,
                        "selected_products": [],
                        "conversation_stage": "cart",
                        "next_step": "cart_manager",
                        "awaiting_cart_action": True
                    }
            
            response = """I'm here to help! You can:

• Select products by number (e.g., "I want #2" or "add 1 and 3")
• Ask questions about the products
• Request to see more options
• Ask for styling advice

What would you like to know?"""
        else:
            response = f"""I didn't catch which product(s) you want. 

I'm showing you {len(products_shown)} products. You can select them by:
• Saying the number (e.g., "I like #2")
• Multiple numbers (e.g., "add 1, 3, and 5")
• Describing what you want (e.g., "the black hoodie")

Which ones interest you?"""
        
        return {
            "messages": [{"role": "assistant", "content": response}],
            "conversation_stage": "presenting",
            "next_step": "wait_for_user"
        }
    
    def _build_selection_confirmation(self, selected_products: List[Dict]) -> str:
        """Build confirmation message for selected products."""
        
        if len(selected_products) == 1:
            product = selected_products[0]
            response = f"""Perfect! I've added this to your selection:

**{product.get('name', 'Product')}**
💰 {product.get('price', 'N/A')}
🏪 {product.get('store_name', 'Unknown')}
📏 Size: M (default)

Would you like to:
• Add more items
• View your cart
• Proceed to checkout
• Continue shopping"""
        else:
            items_list = "\n".join([
                f"{i+1}. **{p.get('name', 'Product')}** - {p.get('price', 'N/A')}"
                for i, p in enumerate(selected_products)
            ])
            
            response = f"""Great choices! I've added {len(selected_products)} items to your selection:

{items_list}

📏 All items: Size M (default)

What would you like to do next?
• Add more items
• View full cart details
• Proceed to checkout
• Keep shopping"""
        
        return response


# Helper function for main.py integration
def create_selection_handler_node(state: OutfitterState) -> Dict[str, Any]:
    """Node wrapper for LangGraph integration."""
    handler = SelectionHandler()
    return handler.handle_selection(state)