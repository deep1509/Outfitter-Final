"""
Cart Manager Agent - Manages Shopping Cart State
Handles add, remove, view, clear operations with cart persistence

INTEGRATION WITH main.py:
1. Add to imports: from agents.conversation_agents.cartManager import CartManager
2. Initialize in __init__: self.cart_manager = CartManager()  
3. Add node: workflow.add_node("cart_manager", self._cart_manager_node)
4. Add routing from selection_handler to cart_manager
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage
from agents.state import OutfitterState
from datetime import datetime
import json


class CartManager:
    """
    Manages shopping cart across conversation turns.
    Handles cart persistence, item management, and display.
    """
    
    def __init__(self):
        self.cart_operations = {
            "add": self._add_to_cart,
            "remove": self._remove_from_cart,
            "view": self._view_cart,
            "clear": self._clear_cart
        }
    
    def process_cart_action(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Main entry point for cart operations.
        Routes to appropriate handler based on user intent.
        """
        print("🛒 CartManager: Processing cart action...")
        
        # Get cart operation from state
        cart_operation = state.get("cart_operation", "add")
        
        # Route to appropriate handler
        handler = self.cart_operations.get(cart_operation, self._add_to_cart)
        return handler(state)
    
    def _add_to_cart(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Add selected products to cart.
        Merges with existing cart items.
        """
        print("   ➕ Adding items to cart...")
        
        # Get existing cart and new selections
        existing_cart = state.get("selected_products", [])
        new_selections = state.get("pending_cart_additions", [])
        
        if not new_selections:
            return {
                "messages": [AIMessage(content="I didn't catch which items you want to add. Could you tell me the product numbers?")],
                "conversation_stage": "presenting",
                "next_step": "wait_for_user"
            }
        
        # Merge new items with existing cart
        updated_cart = existing_cart.copy()
        
        for item in new_selections:
            # Check if item already in cart
            existing_item = self._find_item_in_cart(item, updated_cart)
            
            if existing_item:
                # Increment quantity if same item
                existing_item["quantity"] = existing_item.get("quantity", 1) + 1
                print(f"   📦 Increased quantity for: {item.get('name', 'Unknown')}")
            else:
                # Add new item
                item["quantity"] = item.get("quantity", 1)
                item["added_at"] = datetime.now().isoformat()
                updated_cart.append(item)
                print(f"   ✓ Added to cart: {item.get('name', 'Unknown')}")
        
        # Build response
        response = self._build_cart_addition_response(new_selections, updated_cart)
        
        return {
            "messages": [AIMessage(content=response)],
            "selected_products": updated_cart,  # Updated cart
            "pending_cart_additions": [],  # Clear pending additions
            "conversation_stage": "cart",
            "awaiting_cart_action": True,
            "next_step": "wait_for_user"
        }
    
    def _remove_from_cart(self, state: OutfitterState) -> Dict[str, Any]:
        """Remove items from cart by index."""
        print("   ➖ Removing items from cart...")
        
        cart = state.get("selected_products", [])
        indices_to_remove = state.get("cart_removal_indices", [])
        
        if not indices_to_remove or not cart:
            return {
                "messages": [AIMessage(content="Which items would you like to remove? (e.g., 'remove #1 and #3')")],
                "conversation_stage": "cart",
                "next_step": "wait_for_user"
            }
        
        # Remove items (in reverse order to maintain indices)
        removed_items = []
        for idx in sorted(indices_to_remove, reverse=True):
            if 0 <= idx < len(cart):
                removed_items.append(cart.pop(idx))
        
        response = self._build_removal_response(removed_items, cart)
        
        return {
            "messages": [AIMessage(content=response)],
            "selected_products": cart,
            "cart_removal_indices": [],
            "conversation_stage": "cart" if cart else "presenting",
            "next_step": "wait_for_user"
        }
    
    def _view_cart(self, state: OutfitterState) -> Dict[str, Any]:
        """Display current cart contents."""
        print("   👀 Viewing cart...")
        
        cart = state.get("selected_products", [])
        
        if not cart:
            response = """Your cart is empty! 🛒

Would you like to:
• Search for products
• Browse what's available
• Get some shopping recommendations"""
        else:
            response = self._build_cart_display(cart)
        
        return {
            "messages": [AIMessage(content=response)],
            "conversation_stage": "cart" if cart else "discovery",
            "next_step": "wait_for_user"
        }
    
    def _clear_cart(self, state: OutfitterState) -> Dict[str, Any]:
        """Clear all items from cart."""
        print("   🗑️ Clearing cart...")
        
        cart = state.get("selected_products", [])
        item_count = len(cart)
        
        response = f"""Cart cleared! Removed {item_count} item{'s' if item_count != 1 else ''}.

Ready to start fresh? What would you like to find?"""
        
        return {
            "messages": [AIMessage(content=response)],
            "selected_products": [],
            "conversation_stage": "discovery",
            "next_step": "wait_for_user"
        }
    
    # ============ HELPER METHODS ============
    
    def _find_item_in_cart(self, item: Dict[str, Any], cart: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find if item already exists in cart (by URL or name)."""
        item_url = item.get("url", "")
        item_name = item.get("name", "")
        
        for cart_item in cart:
            if cart_item.get("url") == item_url and item_url:
                return cart_item
            if cart_item.get("name") == item_name and item_name:
                return cart_item
        
        return None
    
    def _build_cart_addition_response(self, new_items: List[Dict], full_cart: List[Dict]) -> str:
        """Build response for items added to cart."""
        
        if len(new_items) == 1:
            item = new_items[0]
            response = f"""✅ Added to your cart:

**{item.get('name', 'Unknown Product')}**
💰 {item.get('price', 'N/A')}
🏪 {item.get('store_name', 'Unknown Store')}

**Cart Summary:**
{len(full_cart)} item{'s' if len(full_cart) != 1 else ''} • {self._calculate_cart_total(full_cart)}

What would you like to do next?
• Continue shopping
• View full cart
• Ask me questions about sizing or styling"""
        else:
            items_list = "\n".join([
                f"{i+1}. **{item.get('name', 'Unknown')}** - {item.get('price', 'N/A')}"
                for i, item in enumerate(new_items)
            ])
            
            response = f"""✅ Added {len(new_items)} items to your cart:

{items_list}

**Cart Summary:**
{len(full_cart)} total items • {self._calculate_cart_total(full_cart)}

What's next?
• Keep shopping for more items
• View your complete cart
• Ask about styling or product details"""
        
        return response
    
    def _build_removal_response(self, removed_items: List[Dict], remaining_cart: List[Dict]) -> str:
        """Build response for removed items."""
        
        if not removed_items:
            return "No items were removed from your cart."
        
        if len(removed_items) == 1:
            item = removed_items[0]
            response = f"""Removed from cart:
**{item.get('name', 'Unknown Product')}**

Cart now has {len(remaining_cart)} item{'s' if len(remaining_cart) != 1 else ''}.

Would you like to continue shopping?"""
        else:
            response = f"""Removed {len(removed_items)} items from cart.

Cart now has {len(remaining_cart)} item{'s' if len(remaining_cart) != 1 else ''}.

Anything else you'd like to do?"""
        
        return response
    
    def _build_cart_display(self, cart: List[Dict]) -> str:
        """Build formatted cart display grouped by store."""
        
        # Group by store
        by_store = {}
        for item in cart:
            store = item.get("store_name", "Unknown Store")
            if store not in by_store:
                by_store[store] = []
            by_store[store].append(item)
        
        # Build display
        display_parts = [f"🛒 **Your Cart** ({len(cart)} item{'s' if len(cart) != 1 else ''})"]
        display_parts.append("")
        
        for store_name, items in by_store.items():
            display_parts.append(f"🏪 **{store_name}:**")
            
            for i, item in enumerate(items, 1):
                quantity = item.get("quantity", 1)
                qty_str = f" (x{quantity})" if quantity > 1 else ""
                
                display_parts.append(f"{i}. **{item.get('name', 'Unknown')}**{qty_str}")
                display_parts.append(f"   💰 {item.get('price', 'N/A')}")
                
                if item.get('url'):
                    display_parts.append(f"   🔗 {item.get('url')}")
                
                display_parts.append("")
        
        # Add totals
        total = self._calculate_cart_total(cart)
        display_parts.append(f"**Total:** {total}")
        display_parts.append("")
        display_parts.append("""**What's next?**
• Add more items
• Remove items (e.g., "remove #2")
• Continue shopping
• Ask me anything about these products""")
        
        return "\n".join(display_parts)
    
    def _calculate_cart_total(self, cart: List[Dict]) -> str:
        """Calculate total cart value."""
        total = 0.0
        
        for item in cart:
            price_str = item.get("price", "$0.00")
            quantity = item.get("quantity", 1)
            
            # Extract numeric price
            import re
            price_match = re.search(r'\d+\.?\d*', price_str.replace(',', ''))
            if price_match:
                price_value = float(price_match.group())
                total += price_value * quantity
        
        return f"${total:.2f}"


# Helper function for main.py integration
def create_cart_manager_node(state: OutfitterState) -> Dict[str, Any]:
    """Node wrapper for LangGraph integration."""
    manager = CartManager()
    return manager.process_cart_action(state)