"""
🚀 Outfitter.ai - Assistify-Inspired AI Startup UI
Production-grade interface with stunning gradients, animations, and modern design
"""

import gradio as gr
import asyncio
from typing import List, Dict, Any, Tuple, Optional
from main import OutfitterAssistant
import html
import json
import re

class AssistifyUI:
    def __init__(self):
        self.assistant = OutfitterAssistant()
        self.assistant.setup_graph()
        self.conversation_history = []
        self.current_products = []
        self.current_cart = []
        self.current_user_photo = None
        self.pending_cart_removal = None  # Track pending cart removal
    
    def _safe_price_calculation(self, item: Dict[str, Any]) -> float:
        """Safely calculate price * quantity, handling string prices"""
        try:
            price = item.get('price', 0)
            quantity = item.get('quantity', 1)
            
            # Convert price to float if it's a string
            if isinstance(price, str):
                # Remove currency symbols and convert to float
                price_str = price.replace('$', '').replace(',', '').strip()
                price = float(price_str)
            elif not isinstance(price, (int, float)):
                price = 0.0
            
            # Ensure quantity is numeric
            if not isinstance(quantity, (int, float)):
                quantity = 1
            
            return price * quantity
        except (ValueError, TypeError):
            return 0.0
        
    def extract_products_from_state(self, conversation_result: List[Dict]) -> List[Dict[str, Any]]:
        """Extract products from conversation state"""
        try:
            if hasattr(self.assistant, 'last_products') and self.assistant.last_products:
                print(f"🔍 Found {len(self.assistant.last_products)} products")
                return self.assistant.last_products
            
            if hasattr(self.assistant, '_last_state'):
                products = self.assistant._last_state.get('products_shown', [])
                if not products:
                    products = self.assistant._last_state.get('search_results', [])
                
                if products:
                    print(f"🔍 Found {len(products)} products from state")
                    return products
            
            return []
            
        except Exception as e:
            print(f"❌ Error extracting products: {e}")
            return []

    def extract_cart_from_state(self, conversation_result: List[Dict]) -> List[Dict[str, Any]]:
        """Extract cart items from conversation state"""
        try:
            print(f"🔍 DEBUG: Extracting cart from state...")
            print(f"🔍 DEBUG: assistant._last_state exists: {hasattr(self.assistant, '_last_state')}")
            
            if hasattr(self.assistant, '_last_state') and self.assistant._last_state:
                print(f"🔍 DEBUG: _last_state keys: {list(self.assistant._last_state.keys())}")
                cart_items = self.assistant._last_state.get('selected_products', [])
                print(f"🔍 DEBUG: selected_products from state: {len(cart_items)} items")
                if cart_items:
                    print(f"🛒 Found {len(cart_items)} cart items")
                    for i, item in enumerate(cart_items):
                        print(f"   {i+1}. {item.get('name', 'Unknown')} - {item.get('price', 'N/A')}")
                    return cart_items
                else:
                    print("🛒 No cart items in selected_products")
            else:
                print("🛒 No _last_state available")
            
            print("🛒 Returning empty cart")
            return []
            
        except Exception as e:
            print(f"❌ Error extracting cart: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def handle_cart_removal(self, index: int) -> Tuple[List, str, str, gr.Column]:
        """Handle cart item removal by index"""
        print(f"🗑️ Handling cart removal for index: {index}")
        
        # Get current cart from state
        cart_items = self.extract_cart_from_state([])
        
        if 0 <= index < len(cart_items):
            # Remove the item
            removed_item = cart_items.pop(index)
            print(f"   ✅ Removed item: {removed_item.get('name', 'Unknown')}")
            
            # Update the assistant's state
            if hasattr(self.assistant, '_last_state'):
                self.assistant._last_state['selected_products'] = cart_items
            
            # Create removal message
            message = f"remove item #{index + 1} from cart"
            
            # Process with backend to get proper response
            try:
                result = await self.assistant.run_conversation(message, self.conversation_history)
                self.conversation_history = result.get("messages", [])
                
                # Extract updated cart
                updated_cart = result.get("selected_products", cart_items)
                
                return (
                    self.conversation_history,
                    self.create_empty_products_html(),
                    self.format_cart_page_html_simple(updated_cart),
                    gr.update(visible=False)
                )
            except Exception as e:
                print(f"❌ Error processing cart removal: {e}")
                return (
                    self.conversation_history,
                    self.create_empty_products_html(),
                    self.format_cart_page_html_simple(cart_items),
                    gr.update(visible=False)
                )
        else:
            print(f"❌ Invalid index for removal: {index}")
            return (
                self.conversation_history,
                self.create_empty_products_html(),
                self.format_cart_page_html_simple(cart_items),
                gr.update(visible=False)
            )

    def handle_direct_removal(self, item_index: int, history: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], str, str, gr.update, gr.update, gr.update, *List[gr.update]]:
        """Handle direct removal of cart item by index"""
        try:
            # Get current cart items
            cart_items = self.extract_cart_from_state([])
            
            if not cart_items or item_index >= len(cart_items):
                error_msg = "Item not found in cart."
                error_history = history + [
                    {"role": "user", "content": f"Remove item #{item_index + 1}"}, 
                    {"role": "assistant", "content": error_msg}
                ]
                # Get empty remove button updates
                row_updates, button_updates = self.get_remove_button_updates([])
                return error_history, self.create_error_html(error_msg), self.create_direct_cart_display([]), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), *row_updates, *button_updates
            
            # Remove the item
            removed_item = cart_items.pop(item_index)
            removed_item_name = removed_item.get('name', 'Unknown Product')
            
            # Update the assistant's state
            if hasattr(self, 'assistant') and hasattr(self.assistant, 'state'):
                self.assistant.state['cart'] = cart_items
            
            # Update current cart
            self.current_cart = cart_items
            
            # Create success message
            success_msg = f"✅ Removed '{removed_item_name}' from your cart."
            updated_history = history + [
                {"role": "user", "content": f"Remove item #{item_index + 1}"}, 
                {"role": "assistant", "content": success_msg}
            ]
            
            # Create updated displays
            products_html = self.create_products_grid_html(self.current_products) if self.current_products else self.create_empty_products_html()
            cart_html = self.create_direct_cart_display(cart_items)
            
            # Show virtual try-on sidebar if cart has items
            sidebar_visible = len(cart_items) > 0
            remove_controls_visible = len(cart_items) > 0
            
            # Get remove button updates
            row_updates, button_updates = self.get_remove_button_updates(cart_items)
            
            return updated_history, products_html, cart_html, gr.update(visible=sidebar_visible), gr.update(visible=remove_controls_visible), gr.update(visible=remove_controls_visible), *row_updates, *button_updates
            
        except Exception as e:
            print(f"❌ Error in direct removal: {e}")
            import traceback
            traceback.print_exc()
            error_msg = "I encountered an error removing the item. Please try again."
            error_history = history + [
                {"role": "user", "content": f"Remove item #{item_index + 1}"}, 
                {"role": "assistant", "content": error_msg}
            ]
            # Get empty remove button updates
            row_updates, button_updates = self.get_remove_button_updates([])
            return error_history, self.create_error_html(str(e)), self.create_direct_cart_display([]), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), *row_updates, *button_updates

    async def handle_conversation(self, message: str, history: List) -> Tuple[List, str, str, gr.Column]:
        """Handle conversation with product and cart extraction"""
        
        if not message.strip():
            return history, self.create_empty_products_html(), self.format_cart_page_html_simple([]), gr.update(visible=False)
        
        try:
            # Convert message format
            history_dicts = []
            for msg in history:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    history_dicts.append(msg)
                elif isinstance(msg, list) and len(msg) == 2:
                    user_msg, assistant_msg = msg
                    if user_msg:
                        history_dicts.append({"role": "user", "content": user_msg})
                    if assistant_msg:
                        history_dicts.append({"role": "assistant", "content": assistant_msg})
            
            # Process with backend
            updated_history_dicts = await self.assistant.run_conversation(message, history_dicts)
            
            # Extract products
            products = self.extract_products_from_state(updated_history_dicts)
            
            # Extract cart items
            cart_items = self.extract_cart_from_state(updated_history_dicts)
            
            if products:
                self.current_products = products
            
            if cart_items:
                self.current_cart = cart_items
            
            products_html = self.create_products_grid_html(products) if products else self.create_empty_products_html()
            cart_html = self.create_direct_cart_display(cart_items) if cart_items else self.create_direct_cart_display([])
            
            # Show virtual try-on sidebar if cart has items
            sidebar_visible = len(cart_items) > 0
            remove_controls_visible = len(cart_items) > 0
            
            # Get remove button updates
            row_updates, button_updates = self.get_remove_button_updates(cart_items)
            
            return updated_history_dicts, products_html, cart_html, gr.update(visible=sidebar_visible), gr.update(visible=remove_controls_visible), gr.update(visible=remove_controls_visible), *row_updates, *button_updates
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            error_msg = "I encountered an error. Please try again."
            error_history = history + [
                {"role": "user", "content": message}, 
                {"role": "assistant", "content": error_msg}
            ]
            # Get empty remove button updates
            row_updates, button_updates = self.get_remove_button_updates([])
            return error_history, self.create_error_html(str(e)), self.create_direct_cart_display([]), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), *row_updates, *button_updates

    def create_assistify_css(self):
        """🎨 Assistify-Inspired CSS - Professional AI Startup Design"""
        return """
        /* 🎨 ASSISTIFY COLOR SYSTEM */
        :root {
            /* Primary Gradient (Pink to Orange like Assistify) */
            --gradient-primary: linear-gradient(135deg, #FF6B9D 0%, #FFA06B 50%, #FFD06B 100%);
            --gradient-secondary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-accent: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            
            /* Dark Theme (Navy/Purple like Assistify) */
            --bg-primary: #0F0F23;
            --bg-secondary: #1A1A2E;
            --bg-tertiary: #16213E;
            --bg-card: rgba(26, 26, 46, 0.8);
            
            /* Glassmorphism */
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-border: rgba(255, 255, 255, 0.1);
            --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            
            /* Text */
            --text-primary: #FFFFFF;
            --text-secondary: #B8B8D1;
            --text-muted: #8B8BA7;
            
            /* Accents */
            --accent-cyan: #4ECDC4;
            --accent-pink: #FF6B9D;
            --accent-purple: #667eea;
            
            /* Spacing */
            --space-xs: 0.5rem;
            --space-sm: 1rem;
            --space-md: 1.5rem;
            --space-lg: 2rem;
            --space-xl: 3rem;
            
            /* Border Radius */
            --radius-sm: 8px;
            --radius-md: 16px;
            --radius-lg: 24px;
            --radius-xl: 32px;
            
            /* Transitions */
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        /* 🌐 GLOBAL STYLES */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body, .gradio-container {
            background: var(--bg-primary) !important;
            color: var(--text-primary) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
            line-height: 1.6 !important;
        }
        
        .gradio-container {
            max-width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        
        /* 🎯 CUSTOM SCROLLBAR */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-secondary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--gradient-primary);
            border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--gradient-accent);
        }
        
        /* 🌟 HERO HEADER (Assistify Style) */
        .assistify-hero {
            background: var(--bg-primary);
            padding: var(--space-xl) var(--space-lg);
            text-align: center;
            position: relative;
            overflow: hidden;
            border-bottom: 1px solid var(--glass-border);
        }
        
        .assistify-hero::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(circle at 50% 50%, rgba(102, 126, 234, 0.1) 0%, transparent 50%);
            pointer-events: none;
        }
        
        .hero-content {
            position: relative;
            z-index: 1;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .hero-logo {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            margin-bottom: var(--space-lg);
        }
        
        .hero-logo-icon {
            font-size: 3rem;
            animation: float 3s ease-in-out infinite;
        }
        
        .hero-logo-text {
            font-size: 2.5rem;
            font-weight: 800;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .hero-title {
            font-size: 3.5rem;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: var(--space-md);
            color: var(--text-primary);
        }
        
        .hero-title .gradient-text {
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .hero-subtitle {
            font-size: 1.25rem;
            color: var(--text-secondary);
            max-width: 700px;
            margin: 0 auto var(--space-lg) auto;
            line-height: 1.6;
        }
        
        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: var(--space-xs);
            background: var(--glass-bg);
            backdrop-filter: blur(10px);
            border: 1px solid var(--glass-border);
            padding: var(--space-sm) var(--space-md);
            border-radius: var(--radius-xl);
            font-weight: 600;
            font-size: 0.9rem;
            color: var(--text-primary);
        }
        
        /* 🎬 ANIMATIONS */
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes shimmer {
            0% { background-position: -1000px 0; }
            100% { background-position: 1000px 0; }
        }
        
        /* 📱 MAIN LAYOUT */
        .main-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: var(--space-lg);
        }
        
        /* 🎭 TABS STYLING */
        .gradio-tabs {
            background: transparent !important;
            border: none !important;
        }
        
        .tabitem {
            background: transparent !important;
            border: none !important;
            padding: var(--space-lg) 0 !important;
        }
        
        .tabs {
            display: flex !important;
            gap: var(--space-sm) !important;
            background: var(--glass-bg) !important;
            padding: var(--space-xs) !important;
            border-radius: var(--radius-lg) !important;
            backdrop-filter: blur(10px) !important;
            border: 1px solid var(--glass-border) !important;
            margin-bottom: var(--space-lg) !important;
        }
        
        .tabs button {
            background: transparent !important;
            color: var(--text-secondary) !important;
            border: none !important;
            border-radius: var(--radius-md) !important;
            padding: var(--space-sm) var(--space-lg) !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            transition: var(--transition) !important;
        }
        
        .tabs button:hover {
            background: var(--glass-bg) !important;
            color: var(--text-primary) !important;
        }
        
        .tabs button.selected {
            background: var(--gradient-primary) !important;
            color: white !important;
            box-shadow: 0 4px 15px rgba(255, 107, 157, 0.4) !important;
        }
        
        /* 💬 CHAT SECTION */
        .chat-section {
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-lg);
            padding: var(--space-md);
            box-shadow: var(--glass-shadow);
            height: 100%;
        }
        
        .section-header {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: var(--space-md);
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: var(--space-sm);
        }
        
        .section-header .icon {
            font-size: 1.8rem;
        }
        
        /* 🛍️ PRODUCTS SECTION */
        .products-section {
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-lg);
            padding: var(--space-md);
            box-shadow: var(--glass-shadow);
            min-height: 600px;
        }
        
        .products-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--space-lg);
            padding-bottom: var(--space-md);
            border-bottom: 1px solid var(--glass-border);
        }
        
        .products-count {
            font-size: 1.5rem;
            font-weight: 700;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .products-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: var(--space-lg);
        }
        
        /* 🎴 PRODUCT CARD */
        .product-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-md);
            overflow: hidden;
            transition: var(--transition);
            cursor: pointer;
            animation: fadeIn 0.5s ease-out;
        }
        
        .product-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 20px 40px rgba(255, 107, 157, 0.2);
            border-color: var(--accent-pink);
        }
        
        .product-image-container {
            position: relative;
            width: 100%;
            height: 250px;
            overflow: hidden;
            background: var(--bg-tertiary);
        }
        
        .product-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.5s ease;
        }
        
        .product-card:hover .product-image {
            transform: scale(1.1);
        }
        
        .product-badge {
            position: absolute;
            top: var(--space-sm);
            left: var(--space-sm);
            background: var(--gradient-accent);
            color: white;
            padding: 6px 12px;
            border-radius: var(--radius-sm);
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .store-badge {
            position: absolute;
            bottom: var(--space-sm);
            right: var(--space-sm);
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(10px);
            color: white;
            padding: 6px 12px;
            border-radius: var(--radius-sm);
            font-size: 0.85rem;
            font-weight: 600;
        }
        
        .product-content {
            padding: var(--space-md);
        }
        
        .product-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .product-price {
            font-size: 1.5rem;
            font-weight: 800;
            color: #4ECDC4 !important;
            margin-bottom: var(--space-md);
            text-shadow: 0 0 10px rgba(78, 205, 196, 0.3);
        }
        
        .product-actions {
            display: flex;
            gap: var(--space-sm);
        }
        
        .view-btn {
            flex: 1;
            background: var(--gradient-primary);
            color: white;
            border: none;
            padding: var(--space-sm) var(--space-md);
            border-radius: var(--radius-sm);
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: var(--transition);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-xs);
            text-decoration: none;
        }
        
        .view-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(255, 107, 157, 0.4);
        }
        
        /* 🎯 EMPTY STATES */
        .empty-state {
            text-align: center;
            padding: var(--space-xl);
            color: var(--text-secondary);
        }
        
        .empty-state-icon {
            font-size: 5rem;
            margin-bottom: var(--space-md);
            animation: float 3s ease-in-out infinite;
        }
        
        .empty-state-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
        }
        
        .empty-state-text {
            font-size: 1.1rem;
            color: var(--text-secondary);
        }
        
        /* 🔘 BUTTONS */
        .gradio-button {
            border-radius: var(--radius-sm) !important;
            font-weight: 600 !important;
            transition: var(--transition) !important;
            border: none !important;
        }
        
        .gradio-button.primary {
            background: var(--gradient-primary) !important;
            color: white !important;
        }
        
        .gradio-button.primary:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 20px rgba(255, 107, 157, 0.4) !important;
        }
        
        .gradio-button.secondary {
            background: var(--glass-bg) !important;
            color: var(--text-primary) !important;
            border: 1px solid var(--glass-border) !important;
            backdrop-filter: blur(10px) !important;
        }
        
        .gradio-button.secondary:hover {
            background: var(--bg-card) !important;
        }
        
        /* 📝 INPUT FIELDS */
        .gradio-textbox input,
        .gradio-textbox textarea {
            background: var(--glass-bg) !important;
            border: 1px solid var(--glass-border) !important;
            color: var(--text-primary) !important;
            border-radius: var(--radius-sm) !important;
            backdrop-filter: blur(10px) !important;
        }
        
        .gradio-textbox input:focus,
        .gradio-textbox textarea:focus {
            border-color: var(--accent-pink) !important;
            box-shadow: 0 0 0 2px rgba(255, 107, 157, 0.2) !important;
        }
        
        /* 💬 CHATBOT */
        .chatbot {
            background: transparent !important;
            border: none !important;
        }
        
        .message {
            background: rgba(15, 15, 35, 0.9) !important;
            backdrop-filter: blur(10px) !important;
            border: 1px solid rgba(78, 205, 196, 0.3) !important;
            border-radius: var(--radius-md) !important;
            color: #FFFFFF !important;
        }
        
        .message .markdown {
            color: #FFFFFF !important;
        }
        
        .message .markdown p {
            color: #FFFFFF !important;
        }
        
        .message .markdown h1,
        .message .markdown h2,
        .message .markdown h3,
        .message .markdown h4,
        .message .markdown h5,
        .message .markdown h6 {
            color: #FFFFFF !important;
        }
        
        .message .markdown ul,
        .message .markdown ol {
            color: #FFFFFF !important;
        }
        
        .message .markdown li {
            color: #FFFFFF !important;
        }
        
        .message .markdown strong,
        .message .markdown b {
            color: #FFFFFF !important;
        }
        
        .message .markdown em,
        .message .markdown i {
            color: #FFFFFF !important;
        }
        
        .message .markdown code {
            background: rgba(78, 205, 196, 0.2) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(78, 205, 196, 0.3) !important;
        }
        
        .message .markdown pre {
            background: rgba(15, 15, 35, 0.8) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(78, 205, 196, 0.3) !important;
        }
        
        .message .markdown blockquote {
            background: rgba(78, 205, 196, 0.1) !important;
            color: #FFFFFF !important;
            border-left: 3px solid #4ECDC4 !important;
        }
        
        /* Additional message styling for better contrast */
        .message .markdown a {
            color: #4ECDC4 !important;
            text-decoration: underline !important;
        }
        
        .message .markdown a:hover {
            color: #FF6B9D !important;
        }
        
        .message .markdown table {
            background: rgba(15, 15, 35, 0.8) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(78, 205, 196, 0.3) !important;
        }
        
        .message .markdown th,
        .message .markdown td {
            background: rgba(15, 15, 35, 0.6) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(78, 205, 196, 0.2) !important;
        }
        
        .message .markdown th {
            background: rgba(78, 205, 196, 0.2) !important;
            color: #FFFFFF !important;
        }
        
        /* Ensure all text in messages is white */
        .message * {
            color: #FFFFFF !important;
        }
        
        .message .markdown * {
            color: #FFFFFF !important;
        }
        
        /* 📱 RESPONSIVE */
        @media (max-width: 768px) {
            .hero-title {
                font-size: 2rem;
            }
            
            .hero-subtitle {
                font-size: 1rem;
            }
            
            .products-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        /* Very small screens - single column for better readability */
        @media (max-width: 480px) {
            .products-grid {
                grid-template-columns: 1fr;
            }
        }
        
        /* 🎨 NEON BUTTONS */
        .neon-button {
            background: linear-gradient(135deg, #0F0F23, #1A1A2E) !important;
            color: #FFFFFF !important;
            border: 2px solid #4ECDC4 !important;
            border-radius: 12px !important;
            padding: 12px 24px !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            box-shadow: 0 0 20px rgba(78, 205, 196, 0.3) !important;
            transition: all 0.3s ease !important;
            min-height: 50px !important;
        }
        
        .neon-button:hover {
            background: linear-gradient(135deg, #1A1A2E, #16213E) !important;
            border-color: #FF6B9D !important;
            box-shadow: 0 0 30px rgba(255, 107, 157, 0.5) !important;
            transform: translateY(-2px) !important;
        }
        
        .neon-button:active {
            transform: translateY(0) !important;
            box-shadow: 0 0 15px rgba(78, 205, 196, 0.4) !important;
        }
        
        /* 📝 LARGE TEXT INPUT */
        .large-text-input {
            min-height: 80px !important;
            font-size: 16px !important;
            padding: 16px !important;
            border-radius: 12px !important;
            background: rgba(255, 255, 255, 0.05) !important;
            border: 2px solid rgba(78, 205, 196, 0.3) !important;
            color: #FFFFFF !important;
            backdrop-filter: blur(10px) !important;
            transition: all 0.3s ease !important;
        }
        
        .large-text-input:focus {
            border-color: #4ECDC4 !important;
            box-shadow: 0 0 20px rgba(78, 205, 196, 0.3) !important;
            background: rgba(255, 255, 255, 0.08) !important;
        }
        
        .large-text-input::placeholder {
            color: #B8B8D1 !important;
            opacity: 0.8 !important;
        }
        
        /* 🛒 CART SECTION STYLING */
        .cart-section {
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-lg);
            padding: var(--space-lg);
            box-shadow: var(--glass-shadow);
            min-height: 600px;
        }
        
        .cart-header {
            margin-bottom: var(--space-xl);
            padding-bottom: var(--space-lg);
            border-bottom: 2px solid var(--glass-border);
        }
        
        .cart-title {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .cart-title h2 {
            font-size: 2rem;
            font-weight: 800;
            color: var(--text-primary);
            margin: 0;
        }
        
        .cart-count {
            background: var(--gradient-primary);
            color: white;
            padding: 8px 16px;
            border-radius: var(--radius-xl);
            font-weight: 700;
            font-size: 0.9rem;
        }
        
        /* 🛍️ CART ITEMS CONTAINER */
        .cart-items-container {
            display: flex;
            flex-direction: column;
            gap: var(--space-md);
            margin-bottom: var(--space-xl);
        }
        
        /* 🎴 CART ITEM CARD */
        .cart-item-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-md);
            padding: var(--space-lg);
            display: flex;
            align-items: center;
            gap: var(--space-lg);
            transition: var(--transition);
            animation: fadeIn 0.5s ease-out;
        }
        
        .cart-item-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(78, 205, 196, 0.2);
            border-color: var(--accent-cyan);
        }
        
        .cart-item-image {
            flex-shrink: 0;
            width: 80px;
            height: 80px;
            border-radius: var(--radius-sm);
            overflow: hidden;
            background: var(--bg-tertiary);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .cart-item-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .cart-item-placeholder {
            font-size: 2rem;
            color: var(--text-muted);
        }
        
        .cart-item-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: var(--space-sm);
        }
        
        .cart-item-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }
        
        .cart-item-name {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin: 0;
            line-height: 1.4;
        }
        
        .cart-item-remove {
            background: rgba(255, 107, 157, 0.2);
            color: var(--accent-pink);
            border: 1px solid var(--accent-pink);
            border-radius: 50%;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 1.2rem;
            font-weight: bold;
            transition: var(--transition);
        }
        
        .cart-item-remove:hover {
            background: var(--accent-pink);
            color: white;
            transform: scale(1.1);
        }
        
        .cart-item-remove-instruction {
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 4px;
        }
        
        .cart-instructions {
            background: rgba(255, 107, 157, 0.1);
            border: 1px solid var(--accent-pink);
            border-radius: var(--border-radius);
            padding: var(--space-md);
            margin-top: var(--space-lg);
        }
        
        .cart-instructions h4 {
            color: var(--accent-pink);
            margin: 0 0 var(--space-xs) 0;
            font-size: 1rem;
        }
        
        .cart-instructions p {
            color: var(--text-secondary);
            margin: 0;
            font-size: 0.9rem;
        }
        
        .remove-controls-header h4 {
            color: var(--accent-pink);
            margin: 0 0 var(--space-sm) 0;
            font-size: 1.1rem;
        }
        
        .remove-button {
            background: #dc3545 !important;
            color: white !important;
            border: none !important;
            border-radius: var(--border-radius) !important;
            padding: var(--space-sm) var(--space-md) !important;
            font-weight: 600 !important;
            transition: var(--transition) !important;
        }
        
        .remove-button:hover {
            background: #c82333 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3) !important;
        }
        
        .remove-instructions {
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: var(--space-xs);
        }
        
        .cart-item-number {
            background: rgba(255, 107, 157, 0.2);
            color: var(--accent-pink);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .cart-item-actions {
            display: flex;
            align-items: center;
            gap: var(--space-xs);
        }
        
        .cart-item-remove-btn {
            background: #dc3545 !important;
            color: white !important;
            border: none !important;
            border-radius: 50% !important;
            width: 28px !important;
            height: 28px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            font-size: 16px !important;
            font-weight: bold !important;
            transition: all 0.2s ease !important;
            line-height: 1 !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        
        .cart-item-remove-btn:hover {
            background: #c82333 !important;
            transform: scale(1.1) !important;
            box-shadow: 0 2px 8px rgba(220, 53, 69, 0.3) !important;
        }
        
        .cart-item-remove-btn:active {
            transform: scale(0.95) !important;
        }
        
        .cart-item-details {
            display: flex;
            flex-direction: column;
            gap: var(--space-xs);
        }
        
        .cart-item-store {
            display: flex;
            align-items: center;
            gap: var(--space-xs);
        }
        
        .store-icon {
            font-size: 0.9rem;
        }
        
        .store-name {
            font-size: 0.9rem;
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .cart-item-specs {
            display: flex;
            gap: var(--space-md);
        }
        
        .spec-item {
            display: flex;
            gap: var(--space-xs);
            font-size: 0.85rem;
        }
        
        .spec-label {
            color: var(--text-muted);
            font-weight: 500;
        }
        
        .spec-value {
            color: var(--text-primary);
            font-weight: 600;
        }
        
        .cart-item-pricing {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: var(--space-xs);
            text-align: right;
        }
        
        .cart-item-price {
            font-size: 1rem;
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .cart-item-total {
            font-size: 1.3rem;
            font-weight: 800;
            color: var(--accent-cyan);
            text-shadow: 0 0 10px rgba(78, 205, 196, 0.3);
        }
        
        /* 🎭 Virtual Try-On Styles */
        .tryon-results {
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            color: white;
            margin: 10px 0;
        }
        
        .tryon-category {
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            backdrop-filter: blur(10px);
        }
        
        .tryon-item {
            margin-top: 10px;
        }
        
        .tryon-item img {
            border: 2px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .tryon-error {
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(255, 107, 107, 0.2);
            border-radius: 8px;
            border: 1px solid rgba(255, 107, 107, 0.3);
        }
        
        /* 📋 CART SUMMARY CARD */
        .cart-summary-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-lg);
            padding: var(--space-lg);
            box-shadow: var(--glass-shadow);
        }
        
        .cart-summary-header {
            margin-bottom: var(--space-lg);
            padding-bottom: var(--space-md);
            border-bottom: 1px solid var(--glass-border);
        }
        
        .cart-summary-header h3 {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
            margin: 0;
        }
        
        .cart-summary-details {
            margin-bottom: var(--space-lg);
        }
        
        .summary-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: var(--space-sm) 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .summary-row:last-child {
            border-bottom: none;
        }
        
        .summary-label {
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .summary-value {
            color: var(--text-primary);
            font-weight: 600;
        }
        
        .total-row {
            margin-top: var(--space-md);
            padding-top: var(--space-md);
            border-top: 2px solid var(--glass-border);
        }
        
        .total-row .summary-label {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        
        .total-amount {
            font-size: 1.3rem;
            font-weight: 800;
            color: var(--accent-cyan);
            text-shadow: 0 0 10px rgba(78, 205, 196, 0.3);
        }
        
        /* 🔘 CART ACTION BUTTONS */
        .cart-actions {
            display: flex;
            gap: var(--space-md);
            flex-wrap: wrap;
        }
        
        .primary-btn {
            flex: 1;
            background: var(--gradient-primary);
            color: white;
            border: none;
            padding: var(--space-md) var(--space-lg);
            border-radius: var(--radius-md);
            font-weight: 700;
            font-size: 1rem;
            cursor: pointer;
            transition: var(--transition);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            min-height: 50px;
        }
        
        .primary-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(255, 107, 157, 0.4);
        }
        
        .secondary-btn {
            flex: 1;
            background: var(--glass-bg);
            color: var(--text-primary);
            border: 1px solid var(--glass-border);
            padding: var(--space-md) var(--space-lg);
            border-radius: var(--radius-md);
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: var(--transition);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            min-height: 50px;
            backdrop-filter: blur(10px);
        }
        
        .secondary-btn:hover {
            background: var(--bg-card);
            border-color: var(--accent-cyan);
        }
        
        .btn-icon {
            font-size: 1.1rem;
        }
        
        /* 📱 RESPONSIVE CART */
        @media (max-width: 768px) {
            .cart-item-card {
                flex-direction: column;
                align-items: flex-start;
                gap: var(--space-md);
            }
            
            .cart-item-image {
                width: 100%;
                height: 200px;
            }
            
            .cart-item-pricing {
                align-items: flex-start;
                width: 100%;
            }
            
            .cart-actions {
                flex-direction: column;
            }
            
            .primary-btn,
            .secondary-btn {
                width: 100%;
            }
        }
        """

    def create_hero_html(self):
        """🌟 Create Assistify-style hero header"""
        return """
        <div class="assistify-hero">
            <div class="hero-content">
                
                <h1 class="hero-title">
                    🛍️ Outfitter.ai <span class="gradient-text">AI Assistant</span>
                </h1>
                
                <p class="hero-subtitle">
                    Your AI-powered shopping assistant with intelligent product discovery.
                    Seamlessly connect to multiple stores for comprehensive assistance.
                </p>
                
            </div>
        </div>
        """
    
    def create_empty_products_html(self):
        """Create empty products state"""
        return """
        <div class="products-section">
            <div class="empty-state">
                <div class="empty-state-icon">👕</div>
                <h3 class="empty-state-title">Products will appear here</h3>
                <p class="empty-state-text">Start by telling me what you're looking for...</p>
            </div>
        </div>
        """
    
    def create_product_card_html(self, product: Dict[str, Any], index: int) -> str:
        """Create product card"""
        name = html.escape(product.get("name") or "Unknown Product")
        price = html.escape(product.get("price") or "Price unavailable")
        url = product.get("url") or "#"
        image_url = product.get("image_url") or ""
        store = html.escape(product.get("store_name") or "Unknown Store")
        is_on_sale = product.get("is_on_sale", False)
        
        if not image_url:
            image_url = "https://via.placeholder.com/400x400/1a1a2e/667eea?text=No+Image"
        
        sale_badge = '<div class="product-badge">🔥 SALE</div>' if is_on_sale else ""
        
        return f"""
        <div class="product-card" data-index="{index}">
            <div class="product-image-container">
                <img 
                    src="{image_url}" 
                    alt="{name}"
                    class="product-image"
                    onerror="this.src='https://via.placeholder.com/400x400/1a1a2e/667eea?text=No+Image'"
                />
                {sale_badge}
                <div class="store-badge">{store}</div>
            </div>
            
            <div class="product-content">
                <h3 class="product-title">{name}</h3>
                <div class="product-price">{price}</div>
                
                <div class="product-actions">
                    <a href="{url}" target="_blank" class="view-btn">
                        <span>View Product</span>
                        <span>→</span>
                    </a>
                </div>
            </div>
        </div>
        """
    
    def create_products_grid_html(self, products: List[Dict[str, Any]]) -> str:
        """Create products grid"""
        if not products:
            return self.create_empty_products_html()
        
        header = f"""
        <div class="products-header">
            <div class="products-count">Found {len(products)} products</div>
        </div>
        """
        
        cards = '<div class="products-grid">'
        for index, product in enumerate(products, 1):
            cards += self.create_product_card_html(product, index)
        cards += '</div>'
        
        return f"""
        <div class="products-section">
            {header}
            {cards}
        </div>
        """
    
    def create_error_html(self, error: str) -> str:
        """Create error state"""
        return f"""
        <div class="products-section">
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <h3 class="empty-state-title">Something went wrong</h3>
                <p class="empty-state-text">Please try your search again</p>
            </div>
        </div>
        """
    
    def format_cart_page_html_with_buttons(self, cart_items: List[Dict[str, Any]]) -> Tuple[str, List[gr.Button]]:
        """Format cart page with individual remove buttons for each item"""
        if not cart_items:
            return '<div class="empty-state"><div class="empty-state-icon">🛒</div><h3 class="empty-state-title">Your cart is empty</h3></div>', []
        
        total_items = len(cart_items)
        total_price = sum(self._safe_price_calculation(item) for item in cart_items)
        
        cart_items_html = ""
        remove_buttons = []
        
        for index, item in enumerate(cart_items):
            name = item.get('name', 'Unknown Product')
            price = item.get('price', 0)
            quantity = item.get('quantity', 1)
            size = item.get('size', 'One Size')
            store = item.get('store', 'Unknown Store')
            image_url = item.get('image_url', '')
            
            # Format price safely
            try:
                if isinstance(price, str):
                    # Remove currency symbols and convert to float
                    price_str = price.replace('$', '').replace(',', '').strip()
                    price_float = float(price_str)
                    price_str = f"${price_float:.2f}"
                    item_total = price_float * quantity
                elif isinstance(price, (int, float)):
                    price_str = f"${price:.2f}"
                    item_total = price * quantity
                else:
                    price_str = str(price)
                    item_total = 0
            except (ValueError, TypeError):
                price_str = str(price)
                item_total = 0
            
            # Handle image
            if image_url and image_url.startswith('http'):
                image_html = f'<img src="{image_url}" alt="{name}" class="cart-item-image-img" loading="lazy">'
            else:
                image_html = '<div class="cart-item-placeholder">📦</div>'
            
            cart_items_html += f"""
            <div class="cart-item-card" data-index="{index}">
                <div class="cart-item-image">
                    {image_html}
                </div>
                
                <div class="cart-item-content">
                    <div class="cart-item-header">
                        <h4 class="cart-item-name">{name}</h4>
                        <div class="cart-item-remove-container" id="remove-{index}"></div>
                    </div>
                    
                    <div class="cart-item-details">
                        <div class="cart-item-store">
                            <span class="store-icon">🏪</span>
                            <span class="store-name">{store}</span>
                        </div>
                        
                        <div class="cart-item-specs">
                            <span class="spec-item">
                                <span class="spec-label">Size:</span>
                                <span class="spec-value">{size}</span>
                            </span>
                            <span class="spec-item">
                                <span class="spec-label">Qty:</span>
                                <span class="spec-value">{quantity}</span>
                            </span>
                        </div>
                    </div>
                </div>
                
                <div class="cart-item-pricing">
                    <div class="cart-item-price">{price_str}</div>
                    <div class="cart-item-total">${item_total:.2f}</div>
                </div>
            </div>
            """
        
        return f"""
        <div class="cart-section">
            <div class="cart-header">
                <div class="cart-title">
                    <h2>🛒 Shopping Cart</h2>
                    <span class="cart-count">{total_items} item{'s' if total_items != 1 else ''}</span>
                </div>
            </div>
            
            <div class="cart-items-container">
                {cart_items_html}
            </div>
            
            <div class="cart-summary-card">
                <div class="cart-summary-header">
                    <h3>Order Summary</h3>
                </div>
                
                <div class="cart-summary-details">
                    <div class="summary-row">
                        <span class="summary-label">Subtotal ({total_items} items)</span>
                        <span class="summary-value">${total_price:.2f}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Shipping</span>
                        <span class="summary-value">Calculated at checkout</span>
                    </div>
                    <div class="summary-row total-row">
                        <span class="summary-label">Total</span>
                        <span class="summary-value total-amount">${total_price:.2f}</span>
                    </div>
                </div>
                
                <div class="cart-actions">
                    <button class="checkout-btn primary-btn">
                        <span class="btn-icon">💳</span>
                        Proceed to Checkout
                    </button>
                    <button class="continue-btn secondary-btn">
                        <span class="btn-icon">🛍️</span>
                        Continue Shopping
                    </button>
                </div>
            </div>
        </div>
        """, remove_buttons

    def create_cart_components(self, cart_items: List[Dict[str, Any]]) -> Tuple[str, List[gr.Button]]:
        """Create cart display with individual remove buttons for each item"""
        if not cart_items:
            return """
            <div class="cart-section">
                <div class="empty-state">
                    <div class="empty-state-icon">🛒</div>
                    <h3 class="empty-state-title">Your cart is empty</h3>
                    <p class="empty-state-text">Add some items to get started!</p>
                </div>
            </div>
            """, []
        
        total_items = len(cart_items)
        total_price = sum(self._safe_price_calculation(item) for item in cart_items)
        
        cart_items_html = ""
        remove_buttons = []
        
        for index, item in enumerate(cart_items):
            name = item.get('name', 'Unknown Product')
            price = item.get('price', 0)
            quantity = item.get('quantity', 1)
            size = item.get('size', 'One Size')
            store = item.get('store', 'Unknown Store')
            image_url = item.get('image_url', '')
            
            # Format price safely
            try:
                if isinstance(price, str):
                    price_str = price.replace('$', '').replace(',', '').strip()
                    price_float = float(price_str)
                    price_str = f"${price_float:.2f}"
                    item_total = price_float * quantity
                elif isinstance(price, (int, float)):
                    price_str = f"${price:.2f}"
                    item_total = price * quantity
                else:
                    price_str = str(price)
                    item_total = 0
            except (ValueError, TypeError):
                price_str = str(price)
                item_total = 0
            
            # Handle image
            if image_url and image_url.startswith('http'):
                image_html = f'<img src="{image_url}" alt="{name}" class="cart-item-image-img" loading="lazy">'
            else:
                image_html = '<div class="cart-item-placeholder">📦</div>'
            
            cart_items_html += f"""
            <div class="cart-item-card" data-index="{index}">
                <div class="cart-item-image">
                    {image_html}
                </div>
                
                <div class="cart-item-content">
                    <div class="cart-item-header">
                        <h4 class="cart-item-name">{name}</h4>
                        <div class="cart-item-remove-container" id="remove-btn-{index}">
                            <!-- Remove button will be inserted here -->
                        </div>
                    </div>
                    
                    <div class="cart-item-details">
                        <div class="cart-item-store">
                            <span class="store-icon">🏪</span>
                            <span class="store-name">{store}</span>
                        </div>
                        
                        <div class="cart-item-specs">
                            <span class="spec-item">
                                <span class="spec-label">Size:</span>
                                <span class="spec-value">{size}</span>
                            </span>
                            <span class="spec-item">
                                <span class="spec-label">Qty:</span>
                                <span class="spec-value">{quantity}</span>
                            </span>
                        </div>
                    </div>
                </div>
                
                <div class="cart-item-pricing">
                    <div class="cart-item-price">{price_str}</div>
                    <div class="cart-item-total">${item_total:.2f}</div>
                </div>
            </div>
            """
        
        cart_html = f"""
        <div class="cart-section">
            <div class="cart-header">
                <div class="cart-title">
                    <h2>🛒 Shopping Cart</h2>
                    <span class="cart-count">{total_items} item{'s' if total_items != 1 else ''}</span>
                </div>
            </div>
            
            <div class="cart-items-container">
                {cart_items_html}
            </div>
            
            <div class="cart-summary-card">
                <div class="cart-summary-header">
                    <h3>Order Summary</h3>
                </div>
                
                <div class="cart-summary-details">
                    <div class="summary-row">
                        <span class="summary-label">Subtotal ({total_items} items)</span>
                        <span class="summary-value">${total_price:.2f}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Shipping</span>
                        <span class="summary-value">Calculated at checkout</span>
                    </div>
                    <div class="summary-row total-row">
                        <span class="summary-label">Total</span>
                        <span class="summary-value total-amount">${total_price:.2f}</span>
                    </div>
                </div>
                
                <div class="cart-actions">
                    <button class="checkout-btn primary-btn">
                        <span class="btn-icon">💳</span>
                        Proceed to Checkout
                    </button>
                    <button class="continue-btn secondary-btn">
                        <span class="btn-icon">🛍️</span>
                        Continue Shopping
                    </button>
                </div>
            </div>
        </div>
        """
        
        return cart_html, remove_buttons

    def create_direct_cart_display(self, cart_items: List[Dict[str, Any]]) -> str:
        """Create cart display with X buttons on each item"""
        if not cart_items:
            return """
            <div class="cart-section">
                <div class="empty-state">
                    <div class="empty-state-icon">🛒</div>
                    <h3 class="empty-state-title">Your cart is empty</h3>
                    <p class="empty-state-text">Add some items to get started!</p>
                </div>
            </div>
            """
        
        total_items = len(cart_items)
        total_price = sum(self._safe_price_calculation(item) for item in cart_items)
        
        cart_items_html = ""
        
        for index, item in enumerate(cart_items):
            name = item.get('name', 'Unknown Product')
            price = item.get('price', 0)
            quantity = item.get('quantity', 1)
            size = item.get('size', 'One Size')
            store = item.get('store', 'Unknown Store')
            image_url = item.get('image_url', '')
            
            # Format price safely
            try:
                if isinstance(price, str):
                    price_str = price.replace('$', '').replace(',', '').strip()
                    price_float = float(price_str)
                    price_str = f"${price_float:.2f}"
                    item_total = price_float * quantity
                elif isinstance(price, (int, float)):
                    price_str = f"${price:.2f}"
                    item_total = price * quantity
                else:
                    price_str = str(price)
                    item_total = 0
            except (ValueError, TypeError):
                price_str = str(price)
                item_total = 0
            
            # Handle image
            if image_url and image_url.startswith('http'):
                image_html = f'<img src="{image_url}" alt="{name}" class="cart-item-image-img" loading="lazy">'
            else:
                image_html = '<div class="cart-item-placeholder">📦</div>'
            
            cart_items_html += f"""
            <div class="cart-item-card" data-index="{index}">
                <div class="cart-item-image">
                    {image_html}
                </div>
                
                <div class="cart-item-content">
                    <div class="cart-item-header">
                        <h4 class="cart-item-name">{name}</h4>
                        <div class="cart-item-actions">
                            <div class="cart-item-number">#{index + 1}</div>
                            <button class="cart-item-remove-btn" onclick="removeCartItem({index})" title="Remove item #{index + 1}" data-item-index="{index}">×</button>
                        </div>
                    </div>
                    
                    <div class="cart-item-details">
                        <div class="cart-item-store">
                            <span class="store-icon">🏪</span>
                            <span class="store-name">{store}</span>
                        </div>
                        
                        <div class="cart-item-specs">
                            <span class="spec-item">
                                <span class="spec-label">Size:</span>
                                <span class="spec-value">{size}</span>
                            </span>
                            <span class="spec-item">
                                <span class="spec-label">Qty:</span>
                                <span class="spec-value">{quantity}</span>
                            </span>
                        </div>
                    </div>
                </div>
                
                <div class="cart-item-pricing">
                    <div class="cart-item-price">{price_str}</div>
                    <div class="cart-item-total">${item_total:.2f}</div>
                </div>
            </div>
            """
        
        cart_html = f"""
        <div class="cart-section">
            <div class="cart-header">
                <div class="cart-title">
                    <h2>🛒 Shopping Cart</h2>
                    <span class="cart-count">{total_items} item{'s' if total_items != 1 else ''}</span>
                </div>
            </div>
            
            <div class="cart-items-container">
                {cart_items_html}
            </div>
            
            <div class="cart-summary-card">
                <div class="cart-summary-header">
                    <h3>Order Summary</h3>
                </div>
                
                <div class="cart-summary-details">
                    <div class="summary-row">
                        <span class="summary-label">Subtotal ({total_items} items)</span>
                        <span class="summary-value">${total_price:.2f}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Shipping</span>
                        <span class="summary-value">Calculated at checkout</span>
                    </div>
                    <div class="summary-row total-row">
                        <span class="summary-label">Total</span>
                        <span class="summary-value total-amount">${total_price:.2f}</span>
                    </div>
                </div>
                
                <div class="cart-actions">
                    <button class="checkout-btn primary-btn">
                        <span class="btn-icon">💳</span>
                        Proceed to Checkout
                    </button>
                    <button class="continue-btn secondary-btn">
                        <span class="btn-icon">🛍️</span>
                        Continue Shopping
                    </button>
                </div>
            </div>
        </div>
        
        <script>
        // Enhanced removeCartItem function for X buttons
        window.removeCartItem = function(index) {{
            console.log('X button clicked - removing item at index:', index);
            
            // Try multiple ways to find the message input
            let messageInput = null;
            const selectors = [
                'textarea[placeholder*="Tell me what"]',
                'textarea[placeholder*="Tell me"]',
                'textarea[data-testid*="textbox"]',
                'textarea',
                'input[type="text"]'
            ];
            
            for (const selector of selectors) {{
                messageInput = document.querySelector(selector);
                if (messageInput) break;
            }}
            
            if (messageInput) {{
                console.log('Found message input:', messageInput);
                
                // Set the message
                const message = `remove item #${{index + 1}} from cart`;
                messageInput.value = message;
                messageInput.focus();
                
                // Trigger multiple events to ensure Gradio picks up the change
                const events = ['input', 'change', 'keyup', 'keydown', 'blur'];
                events.forEach(eventType => {{
                    messageInput.dispatchEvent(new Event(eventType, {{ bubbles: true, cancelable: true }}));
                }});
                
                // Try multiple ways to find the send button
                let sendButton = null;
                const buttonSelectors = [
                    'button:has-text("Send")',
                    'button[class*="neon-button"]',
                    'button[type="submit"]',
                    'button[data-testid*="send"]',
                    'button:contains("Send")',
                    'button'
                ];
                
                for (const selector of buttonSelectors) {{
                    const buttons = document.querySelectorAll(selector);
                    for (const btn of buttons) {{
                        if (btn.textContent.includes('Send') || btn.textContent.includes('send')) {{
                            sendButton = btn;
                            break;
                        }}
                    }}
                    if (sendButton) break;
                }}
                
                if (sendButton) {{
                    console.log('Found send button:', sendButton);
                    // Click the send button with a delay
                    setTimeout(() => {{
                        sendButton.click();
                        console.log('Send button clicked for X button removal');
                    }}, 300);
                }} else {{
                    console.error('Could not find send button');
                    // Try to trigger form submission
                    const form = messageInput.closest('form');
                    if (form) {{
                        form.submit();
                    }}
                }}
            }} else {{
                console.error('Could not find message input');
                alert(`Remove item #${{index + 1}} from cart - Please type this in the chat`);
            }}
        }};
        
        // Ensure the function is available globally
        if (typeof window !== 'undefined') {{
            window.removeCartItem = window.removeCartItem || function(index) {{
                console.log('Fallback removeCartItem called with index:', index);
                alert(`Remove item #${{index + 1}} from cart - Please type this in the chat`);
            }};
        }}
        </script>
        """
        
        return cart_html

    def update_remove_buttons(self, cart_items: List[Dict[str, Any]]) -> List[gr.update]:
        """Update the visibility and content of remove buttons based on cart items"""
        updates = []
        
        for i in range(10):  # Support up to 10 items
            if i < len(cart_items):
                # Show this remove button
                item_name = cart_items[i].get('name', 'Unknown Product')
                updates.append(gr.update(visible=True, value=f"Remove #{i+1}: {item_name[:30]}..."))
            else:
                # Hide this remove button
                updates.append(gr.update(visible=False))
        
        return updates

    def get_remove_button_updates(self, cart_items: List[Dict[str, Any]]) -> List[gr.update]:
        """Get updates for all remove button rows and buttons"""
        row_updates = []
        button_updates = []
        
        for i in range(10):  # Support up to 10 items
            if i < len(cart_items):
                # Show this remove button row and button
                item_name = cart_items[i].get('name', 'Unknown Product')
                row_updates.append(gr.update(visible=True))
                button_updates.append(gr.update(visible=True, value=f"Remove #{i+1}: {item_name[:30]}..."))
            else:
                # Hide this remove button row and button
                row_updates.append(gr.update(visible=False))
                button_updates.append(gr.update(visible=False))
        
        return row_updates, button_updates

    def create_cart_with_individual_buttons(self, cart_items: List[Dict[str, Any]]) -> Tuple[str, List[gr.Button], bool]:
        """Create cart display with individual remove buttons for each item using Gradio components"""
        if not cart_items:
            return """
            <div class="cart-section">
                <div class="empty-state">
                    <div class="empty-state-icon">🛒</div>
                    <h3 class="empty-state-title">Your cart is empty</h3>
                    <p class="empty-state-text">Add some items to get started!</p>
                </div>
            </div>
            """, [], False
        
        total_items = len(cart_items)
        total_price = sum(self._safe_price_calculation(item) for item in cart_items)
        
        # Create individual remove buttons for each item
        remove_buttons = []
        cart_items_html = ""
        
        for index, item in enumerate(cart_items):
            name = item.get('name', 'Unknown Product')
            price = item.get('price', 0)
            quantity = item.get('quantity', 1)
            size = item.get('size', 'One Size')
            store = item.get('store', 'Unknown Store')
            image_url = item.get('image_url', '')
            
            # Format price safely
            try:
                if isinstance(price, str):
                    price_str = price.replace('$', '').replace(',', '').strip()
                    price_float = float(price_str)
                    price_str = f"${price_float:.2f}"
                    item_total = price_float * quantity
                elif isinstance(price, (int, float)):
                    price_str = f"${price:.2f}"
                    item_total = price * quantity
                else:
                    price_str = str(price)
                    item_total = 0
            except (ValueError, TypeError):
                price_str = str(price)
                item_total = 0
            
            # Handle image
            if image_url and image_url.startswith('http'):
                image_html = f'<img src="{image_url}" alt="{name}" class="cart-item-image-img" loading="lazy">'
            else:
                image_html = '<div class="cart-item-placeholder">📦</div>'
            
            cart_items_html += f"""
            <div class="cart-item-card" data-index="{index}">
                <div class="cart-item-image">
                    {image_html}
                </div>
                
                <div class="cart-item-content">
                    <div class="cart-item-header">
                        <h4 class="cart-item-name">{name}</h4>
                        <div class="cart-item-number">#{index + 1}</div>
                    </div>
                    
                    <div class="cart-item-details">
                        <div class="cart-item-store">
                            <span class="store-icon">🏪</span>
                            <span class="store-name">{store}</span>
                        </div>
                        
                        <div class="cart-item-specs">
                            <span class="spec-item">
                                <span class="spec-label">Size:</span>
                                <span class="spec-value">{size}</span>
                            </span>
                            <span class="spec-item">
                                <span class="spec-label">Qty:</span>
                                <span class="spec-value">{quantity}</span>
                            </span>
                        </div>
                    </div>
                </div>
                
                <div class="cart-item-pricing">
                    <div class="cart-item-price">{price_str}</div>
                    <div class="cart-item-total">${item_total:.2f}</div>
                </div>
            </div>
            """
        
        cart_html = f"""
        <div class="cart-section">
            <div class="cart-header">
                <div class="cart-title">
                    <h2>🛒 Shopping Cart</h2>
                    <span class="cart-count">{total_items} item{'s' if total_items != 1 else ''}</span>
                </div>
            </div>
            
            <div class="cart-items-container">
                {cart_items_html}
            </div>
            
            <div class="cart-summary-card">
                <div class="cart-summary-header">
                    <h3>Order Summary</h3>
                </div>
                
                <div class="cart-summary-details">
                    <div class="summary-row">
                        <span class="summary-label">Subtotal ({total_items} items)</span>
                        <span class="summary-value">${total_price:.2f}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Shipping</span>
                        <span class="summary-value">Calculated at checkout</span>
                    </div>
                    <div class="summary-row total-row">
                        <span class="summary-label">Total</span>
                        <span class="summary-value total-amount">${total_price:.2f}</span>
                    </div>
                </div>
                
                <div class="cart-actions">
                    <button class="checkout-btn primary-btn">
                        <span class="btn-icon">💳</span>
                        Proceed to Checkout
                    </button>
                    <button class="continue-btn secondary-btn">
                        <span class="btn-icon">🛍️</span>
                        Continue Shopping
                    </button>
                </div>
            </div>
        </div>
        """
        
        return cart_html, remove_buttons, True

    def format_cart_page_with_remove_buttons(self, cart_items: List[Dict[str, Any]]) -> Tuple[str, List[str], bool]:
        """Format cart page with remove button functionality"""
        if not cart_items:
            return """
            <div class="cart-section">
                <div class="empty-state">
                    <div class="empty-state-icon">🛒</div>
                    <h3 class="empty-state-title">Your cart is empty</h3>
                    <p class="empty-state-text">Add some items to get started!</p>
                </div>
            </div>
            """, [], False
        
        total_items = len(cart_items)
        total_price = sum(self._safe_price_calculation(item) for item in cart_items)
        
        # Create dropdown choices for removal
        dropdown_choices = []
        cart_items_html = ""
        
        for index, item in enumerate(cart_items):
            name = item.get('name', 'Unknown Product')
            price = item.get('price', 0)
            quantity = item.get('quantity', 1)
            size = item.get('size', 'One Size')
            store = item.get('store', 'Unknown Store')
            image_url = item.get('image_url', '')
            
            # Format price safely
            try:
                if isinstance(price, str):
                    price_str = price.replace('$', '').replace(',', '').strip()
                    price_float = float(price_str)
                    price_str = f"${price_float:.2f}"
                    item_total = price_float * quantity
                elif isinstance(price, (int, float)):
                    price_str = f"${price:.2f}"
                    item_total = price * quantity
                else:
                    price_str = str(price)
                    item_total = 0
            except (ValueError, TypeError):
                price_str = str(price)
                item_total = 0
            
            # Create dropdown choice
            choice_text = f"#{index + 1}: {name} - {price_str}"
            dropdown_choices.append(choice_text)
            
            # Handle image
            if image_url and image_url.startswith('http'):
                image_html = f'<img src="{image_url}" alt="{name}" class="cart-item-image-img" loading="lazy">'
            else:
                image_html = '<div class="cart-item-placeholder">📦</div>'
            
            cart_items_html += f"""
            <div class="cart-item-card" data-index="{index}">
                <div class="cart-item-image">
                    {image_html}
                </div>
                
                <div class="cart-item-content">
                    <div class="cart-item-header">
                        <h4 class="cart-item-name">{name}</h4>
                        <div class="cart-item-actions">
                            <div class="cart-item-number">#{index + 1}</div>
                            <button class="cart-item-remove-btn" onclick="removeCartItem({index})" title="Remove item #1" data-item-index="{index}">×</button>
                        </div>
                    </div>
                    
                    <div class="cart-item-details">
                        <div class="cart-item-store">
                            <span class="store-icon">🏪</span>
                            <span class="store-name">{store}</span>
                        </div>
                        
                        <div class="cart-item-specs">
                            <span class="spec-item">
                                <span class="spec-label">Size:</span>
                                <span class="spec-value">{size}</span>
                            </span>
                            <span class="spec-item">
                                <span class="spec-label">Qty:</span>
                                <span class="spec-value">{quantity}</span>
                            </span>
                        </div>
                    </div>
                </div>
                
                <div class="cart-item-pricing">
                    <div class="cart-item-price">{price_str}</div>
                    <div class="cart-item-total">${item_total:.2f}</div>
                </div>
            </div>
            """
        
        cart_html = f"""
        <div class="cart-section">
            <div class="cart-header">
                <div class="cart-title">
                    <h2>🛒 Shopping Cart</h2>
                    <span class="cart-count">{total_items} item{'s' if total_items != 1 else ''}</span>
                </div>
            </div>
            
            <div class="cart-items-container">
                {cart_items_html}
            </div>
            
            <div class="cart-summary-card">
                <div class="cart-summary-header">
                    <h3>Order Summary</h3>
                </div>
                
                <div class="cart-summary-details">
                    <div class="summary-row">
                        <span class="summary-label">Subtotal ({total_items} items)</span>
                        <span class="summary-value">${total_price:.2f}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Shipping</span>
                        <span class="summary-value">Calculated at checkout</span>
                    </div>
                    <div class="summary-row total-row">
                        <span class="summary-label">Total</span>
                        <span class="summary-value total-amount">${total_price:.2f}</span>
                    </div>
                </div>
                
                <div class="cart-actions">
                    <button class="checkout-btn primary-btn">
                        <span class="btn-icon">💳</span>
                        Proceed to Checkout
                    </button>
                    <button class="continue-btn secondary-btn">
                        <span class="btn-icon">🛍️</span>
                        Continue Shopping
                    </button>
                </div>
            </div>
        </div>
        
        <script>
        // Make sure the function is available globally
        window.removeCartItem = function(index) {{
            console.log('removeCartItem called with index:', index);
            
            // Try multiple ways to find the message input
            let messageInput = null;
            const selectors = [
                'textarea[placeholder*="Tell me what"]',
                'textarea[placeholder*="Tell me"]',
                'textarea[data-testid*="textbox"]',
                'textarea',
                'input[type="text"]'
            ];
            
            for (const selector of selectors) {{
                messageInput = document.querySelector(selector);
                if (messageInput) break;
            }}
            
            if (messageInput) {{
                console.log('Found message input:', messageInput);
                
                // Set the message
                const message = `remove item #${{index + 1}} from cart`;
                messageInput.value = message;
                messageInput.focus();
                
                // Trigger multiple events to ensure Gradio picks up the change
                const events = ['input', 'change', 'keyup', 'keydown', 'blur'];
                events.forEach(eventType => {{
                    messageInput.dispatchEvent(new Event(eventType, {{ bubbles: true, cancelable: true }}));
                }});
                
                // Try multiple ways to find the send button
                let sendButton = null;
                const buttonSelectors = [
                    'button:has-text("Send")',
                    'button[class*="neon-button"]',
                    'button[type="submit"]',
                    'button[data-testid*="send"]',
                    'button:contains("Send")',
                    'button'
                ];
                
                for (const selector of buttonSelectors) {{
                    const buttons = document.querySelectorAll(selector);
                    for (const btn of buttons) {{
                        if (btn.textContent.includes('Send') || btn.textContent.includes('send')) {{
                            sendButton = btn;
                            break;
                        }}
                    }}
                    if (sendButton) break;
                }}
                
                if (sendButton) {{
                    console.log('Found send button:', sendButton);
                    // Click the send button with a delay
                    setTimeout(() => {{
                        sendButton.click();
                        console.log('Send button clicked for removal');
                    }}, 300);
                }} else {{
                    console.error('Could not find send button');
                    // Try to trigger form submission
                    const form = messageInput.closest('form');
                    if (form) {{
                        form.submit();
                    }}
                }}
            }} else {{
                console.error('Could not find message input');
                alert('Could not find message input. Please try using the dropdown method instead.');
            }}
        }};
        
        // Also try to attach the function to the window object immediately
        if (typeof window !== 'undefined') {{
            window.removeCartItem = window.removeCartItem || function(index) {{
                console.log('Fallback removeCartItem called with index:', index);
                alert(`Remove item #${{index + 1}} from cart - Please type this in the chat`);
            }};
        }}
        </script>
        """
        
        return cart_html, dropdown_choices, True

    def format_cart_page_html_simple(self, cart_items: List[Dict[str, Any]]) -> str:
        """Simple cart display without JavaScript - just shows items with text instructions"""
        if not cart_items:
            return """
            <div class="cart-section">
                <div class="empty-state">
                    <div class="empty-state-icon">🛒</div>
                    <h3 class="empty-state-title">Your cart is empty</h3>
                    <p class="empty-state-text">Add some items to get started!</p>
                </div>
            </div>
            """
        
        total_items = len(cart_items)
        total_price = sum(self._safe_price_calculation(item) for item in cart_items)
        
        cart_items_html = ""
        
        for index, item in enumerate(cart_items):
            name = item.get('name', 'Unknown Product')
            price = item.get('price', 0)
            quantity = item.get('quantity', 1)
            size = item.get('size', 'One Size')
            store = item.get('store', 'Unknown Store')
            image_url = item.get('image_url', '')
            
            # Format price safely
            try:
                if isinstance(price, str):
                    # Remove currency symbols and convert to float
                    price_str = price.replace('$', '').replace(',', '').strip()
                    price_float = float(price_str)
                    price_str = f"${price_float:.2f}"
                    item_total = price_float * quantity
                elif isinstance(price, (int, float)):
                    price_str = f"${price:.2f}"
                    item_total = price * quantity
                else:
                    price_str = str(price)
                    item_total = 0
            except (ValueError, TypeError):
                price_str = str(price)
                item_total = 0
            
            # Handle image
            if image_url and image_url.startswith('http'):
                image_html = f'<img src="{image_url}" alt="{name}" class="cart-item-image-img" loading="lazy">'
            else:
                image_html = '<div class="cart-item-placeholder">📦</div>'
            
            cart_items_html += f"""
            <div class="cart-item-card" data-index="{index}">
                <div class="cart-item-image">
                    {image_html}
                </div>
                
                <div class="cart-item-content">
                    <div class="cart-item-header">
                        <h4 class="cart-item-name">{name}</h4>
                        <div class="cart-item-remove-instruction">
                            <small>To remove: Type "remove item #{index + 1}" in chat</small>
                        </div>
                    </div>
                    
                    <div class="cart-item-details">
                        <div class="cart-item-store">
                            <span class="store-icon">🏪</span>
                            <span class="store-name">{store}</span>
                        </div>
                        
                        <div class="cart-item-specs">
                            <span class="spec-item">
                                <span class="spec-label">Size:</span>
                                <span class="spec-value">{size}</span>
                            </span>
                            <span class="spec-item">
                                <span class="spec-label">Qty:</span>
                                <span class="spec-value">{quantity}</span>
                            </span>
                        </div>
                    </div>
                </div>
                
                <div class="cart-item-pricing">
                    <div class="cart-item-price">{price_str}</div>
                    <div class="cart-item-total">${item_total:.2f}</div>
                </div>
            </div>
            """
        
        return f"""
        <div class="cart-section">
            <div class="cart-header">
                <div class="cart-title">
                    <h2>🛒 Shopping Cart</h2>
                    <span class="cart-count">{total_items} item{'s' if total_items != 1 else ''}</span>
                </div>
            </div>
            
            <div class="cart-items-container">
                {cart_items_html}
            </div>
            
            <div class="cart-summary-card">
                <div class="cart-summary-header">
                    <h3>Order Summary</h3>
                </div>
                
                <div class="cart-summary-details">
                    <div class="summary-row">
                        <span class="summary-label">Subtotal ({total_items} items)</span>
                        <span class="summary-value">${total_price:.2f}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Shipping</span>
                        <span class="summary-value">Calculated at checkout</span>
                    </div>
                    <div class="summary-row total-row">
                        <span class="summary-label">Total</span>
                        <span class="summary-value total-amount">${total_price:.2f}</span>
                    </div>
                </div>
                
                <div class="cart-actions">
                    <button class="checkout-btn primary-btn">
                        <span class="btn-icon">💳</span>
                        Proceed to Checkout
                    </button>
                    <button class="continue-btn secondary-btn">
                        <span class="btn-icon">🛍️</span>
                        Continue Shopping
                    </button>
                </div>
            </div>
            
            <div class="cart-instructions">
                <h4>🗑️ To remove items:</h4>
                <p>Type "remove item #1" or "remove item #2" etc. in the chat to remove specific items from your cart.</p>
            </div>
        </div>
        """

    def format_cart_page_html(self, cart_items: List[Dict[str, Any]]) -> str:
        """Format cart page with modern list card design"""
        if not cart_items:
            return """
            <div class="cart-section">
                <div class="empty-state">
                    <div class="empty-state-icon">🛒</div>
                    <h3 class="empty-state-title">Your cart is empty</h3>
                    <p class="empty-state-text">Select products from search results to add them to your cart</p>
                </div>
            </div>
            """
        
        # Calculate totals
        total_items = 0
        total_price = 0.0
        
        for item in cart_items:
            quantity = item.get("quantity", 1)
            total_items += quantity
            
            # Calculate price
            price_str = item.get("price", "$0.00")
            price_match = re.search(r'\d+\.?\d*', price_str.replace(',', ''))
            if price_match:
                price_value = float(price_match.group())
                total_price += price_value * quantity
        
        # Build modern cart HTML
        cart_items_html = ""
        for index, item in enumerate(cart_items, 1):
            quantity = item.get("quantity", 1)
            name = html.escape(item.get('name') or 'Unknown Product')
            price_str = html.escape(item.get('price') or 'N/A')
            store = html.escape(item.get('store_name') or 'Unknown Store')
            size = html.escape(item.get('selected_size') or 'M')
            image_url = item.get("image_url", "")
            
            # Calculate item total
            price_match = re.search(r'\d+\.?\d*', price_str.replace(',', ''))
            item_total = 0.0
            if price_match:
                item_price = float(price_match.group())
                item_total = item_price * quantity
            
            # Product image
            if image_url:
                image_html = f'<img src="{image_url}" alt="{name}" class="cart-item-img" onerror="this.src=\'https://via.placeholder.com/80x80/1a1a2e/ffffff?text=No+Image\'">'
            else:
                image_html = '<div class="cart-item-placeholder">📦</div>'
            
            cart_items_html += f"""
            <div class="cart-item-card" data-index="{index}">
                <div class="cart-item-image">
                    {image_html}
                </div>
                
                <div class="cart-item-content">
                    <div class="cart-item-header">
                        <h4 class="cart-item-name">{name}</h4>
                        <button class="cart-item-remove" data-index="{index}" onclick="removeCartItem({index})">×</button>
                    </div>
                    
                    <div class="cart-item-details">
                        <div class="cart-item-store">
                            <span class="store-icon">🏪</span>
                            <span class="store-name">{store}</span>
                        </div>
                        
                        <div class="cart-item-specs">
                            <span class="spec-item">
                                <span class="spec-label">Size:</span>
                                <span class="spec-value">{size}</span>
                            </span>
                            <span class="spec-item">
                                <span class="spec-label">Qty:</span>
                                <span class="spec-value">{quantity}</span>
                            </span>
                        </div>
                    </div>
                </div>
                
                <div class="cart-item-pricing">
                    <div class="cart-item-price">{price_str}</div>
                    <div class="cart-item-total">${item_total:.2f}</div>
                </div>
            </div>
            """
        
        return f"""
        <div class="cart-section">
            <div class="cart-header">
                <div class="cart-title">
                    <h2>🛒 Shopping Cart</h2>
                    <span class="cart-count">{total_items} item{'s' if total_items != 1 else ''}</span>
                </div>
            </div>
            
            <div class="cart-items-container">
                {cart_items_html}
            </div>
            
            <div class="cart-summary-card">
                <div class="cart-summary-header">
                    <h3>Order Summary</h3>
                </div>
                
                <div class="cart-summary-details">
                    <div class="summary-row">
                        <span class="summary-label">Subtotal ({total_items} items)</span>
                        <span class="summary-value">${total_price:.2f}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Shipping</span>
                        <span class="summary-value">Calculated at checkout</span>
                    </div>
                    <div class="summary-row total-row">
                        <span class="summary-label">Total</span>
                        <span class="summary-value total-amount">${total_price:.2f}</span>
                    </div>
                </div>
                
                <div class="cart-actions">
                    <button class="checkout-btn primary-btn">
                        <span class="btn-icon">💳</span>
                        Proceed to Checkout
                    </button>
                    <button class="continue-btn secondary-btn">
                        <span class="btn-icon">🛍️</span>
                        Continue Shopping
                    </button>
                </div>
            </div>
        </div>
        
        """
    
    def process_virtual_tryon(self, cart_items: List[Dict[str, Any]], photo_path: str) -> str:
        """Process virtual try-on request"""
        try:
            if not cart_items:
                return "<div class='empty-state'><div class='empty-state-icon'>🛒</div><p>Your cart is empty!</p></div>"
            
            if not photo_path:
                return "<div class='empty-state'><div class='empty-state-icon'>📸</div><p>Please upload your photo first!</p></div>"
            
            # Import and use the actual virtual try-on agent
            try:
                from agents.conversation_agents.virtualTryOnAgent import VirtualTryOnAgent
                
                # Create virtual try-on agent
                virtual_tryon_agent = VirtualTryOnAgent()
                
                # Prepare state for virtual try-on
                state = {
                    "selected_products": cart_items,
                    "user_photo": photo_path
                }
                
                # Process virtual try-on
                result = virtual_tryon_agent.process_virtual_tryon(state)
                
                # Extract results from the agent response
                tryon_results = result.get("virtual_tryon_results", {})
                
                if not tryon_results:
                    return "<div class='error-state'><p>❌ No try-on results generated</p></div>"
                
                # Build HTML display for results
                html_content = "<div class='tryon-results'>"
                html_content += "<h3>🎭 Virtual Try-On Results</h3>"
                
                for category, result_data in tryon_results.items():
                    if result_data.get('success', False):
                        item = result_data.get('item', {})
                        tryon_image = result_data.get('tryon_image', '')
                        
                        if tryon_image:
                            html_content += f"""
                            <div class='tryon-category'>
                                <h4>🎭 {category.title()} Try-On</h4>
                                <div class='tryon-item'>
                                    <p><strong>{item.get('name', 'Unknown Item')}</strong> - {item.get('price', 'N/A')}</p>
                                    <img src="data:image/jpeg;base64,{tryon_image}" 
                                         style="max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0;" />
                                </div>
                            </div>
                            """
                    else:
                        error = result_data.get('error', 'Unknown error')
                        html_content += f"""
                        <div class='tryon-error'>
                            <h4>❌ {category.title()} Try-On Failed</h4>
                            <p>Error: {error}</p>
                        </div>
                        """
                
                html_content += "</div>"
                return html_content
                
            except ImportError as e:
                return f"<div class='error-state'><p>❌ Virtual try-on agent not available: {str(e)}</p></div>"
            except Exception as e:
                return f"<div class='error-state'><p>❌ Virtual try-on processing error: {str(e)}</p></div>"
            
        except Exception as e:
            return f"<div class='error-state'><p>❌ Error: {str(e)}</p></div>"

def create_assistify_interface():
    """🚀 Create Assistify-inspired interface"""
    
    ui = AssistifyUI()
    
    with gr.Blocks(
        theme=gr.themes.Soft(
            primary_hue="purple",
            secondary_hue="pink",
            neutral_hue="slate",
        ),
        css=ui.create_assistify_css(),
        title="Outfitter.ai - AI Shopping Assistant",
    ) as interface:
        
        # Hero Header
        gr.HTML(ui.create_hero_html())
        
        # Main Container
        with gr.Column(elem_classes=["main-container"]):
            
            # Tabs
            with gr.Tabs():
                # Shopping Tab
                with gr.Tab("🛍️ Shopping", id="shopping"):
                    with gr.Row(equal_height=False):
                        # Chat Section
                        with gr.Column(scale=2, min_width=500):
                            gr.HTML('<div class="section-header"><span class="icon">💬</span>Chat with AI</div>')
                            
                            chatbot = gr.Chatbot(
                                label="",
                                height=700,
                                show_label=False,
                                avatar_images=("👤", "🤖"),
                                bubble_full_width=False,
                                type="messages",
                                elem_classes=["chat-section"]
                            )

                            # Input row (full width)
                            msg = gr.Textbox(
                                label="",
                                placeholder="Tell me what you're looking for...",
                                lines=3,
                                show_label=False,
                                scale=1,
                                elem_classes=["large-text-input"],
                            )

                            # Buttons row (side-by-side)
                            with gr.Row(equal_height=True):
                                send_btn = gr.Button("Send", variant="primary", scale=1, elem_classes=["neon-button"])
                                clear_btn = gr.Button("Clear Chat", variant="secondary", scale=1, elem_classes=["neon-button"])
                        
                        # Products Section
                        with gr.Column(scale=3, min_width=600):
                            gr.HTML('<div class="section-header"><span class="icon">🛍️</span>Products Found</div>')
                            products_display = gr.HTML(
                                value=ui.create_empty_products_html()
                            )
                
                # Cart Tab
                with gr.Tab("🛒 Cart", id="cart"):
                    with gr.Row(equal_height=False):
                        # Cart Items Section
                        with gr.Column(scale=2, min_width=500):
                            gr.HTML('<div class="section-header"><span class="icon">🛒</span>Shopping Cart</div>')
                            
                            # Cart display with individual remove buttons
                            cart_display = gr.HTML(
                                value='<div class="empty-state"><div class="empty-state-icon">🛒</div><h3 class="empty-state-title">Your cart is empty</h3></div>'
                            )
                            
                            # Individual remove buttons for each cart item
                            with gr.Column(visible=False) as cart_remove_buttons_container:
                                gr.HTML('<div class="remove-controls-header"><h4>🗑️ Remove Items</h4></div>')
                                
                                # Create individual remove buttons for up to 10 items (expandable)
                                remove_buttons = []
                                remove_rows = []
                                remove_btn_components = []
                                
                                for i in range(10):  # Support up to 10 items
                                    with gr.Row(visible=False) as remove_row:
                                        gr.HTML(f'<div class="remove-item-info">Item #{i+1}: <span id="item-name-{i}">Loading...</span></div>')
                                        remove_btn = gr.Button(
                                            f"Remove #{i+1}", 
                                            variant="stop", 
                                            size="sm",
                                            elem_classes=["remove-button"],
                                            visible=False
                                        )
                                        remove_buttons.append((remove_row, remove_btn))
                                        remove_rows.append(remove_row)
                                        remove_btn_components.append(remove_btn)
                        
                        # Virtual Try-On Sidebar
                        with gr.Column(scale=1, min_width=400, visible=False, elem_id="virtual_tryon_sidebar") as virtual_tryon_sidebar:
                            gr.HTML('<div class="section-header"><span class="icon">🎭</span>Virtual Try-On</div>')
                            
                            # Photo Upload Section
                            with gr.Group():
                                gr.Markdown("### 📸 Upload Your Photo")
                                photo_upload = gr.File(
                                    label="Upload your photo",
                                    file_types=["image"],
                                    type="filepath"
                                )
                                upload_btn = gr.Button("📸 Use This Photo", variant="primary", size="sm")
                            
                            # Try-On Results Section
                            with gr.Group():
                                tryon_results = gr.HTML(
                                    value="<div class='empty-state'><div class='empty-state-icon'>🎭</div><p>Upload your photo and try on items!</p></div>"
                                )
                                tryon_btn = gr.Button("🎭 Try On Items", variant="secondary", visible=False)
                            
                            # Instructions
                            gr.Markdown("""
                            <div style="color: white;">
                            **How it works:**
                            1. Upload a clear photo of yourself
                            2. Click "Try On Items" to see how your cart items look on you
                            3. The AI will overlay the clothing onto your photo realistically
                            </div>
                            """)
        
        # Event Handlers
        async def send_message(message, history):
            return await ui.handle_conversation(message, history)
        
        def clear_conversation():
            # Get empty remove button updates
            row_updates, button_updates = ui.get_remove_button_updates([])
            return [], ui.create_empty_products_html(), ui.create_direct_cart_display([]), "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), *row_updates, *button_updates
        
        
        # Bind Events
        send_btn.click(
            send_message,
            inputs=[msg, chatbot],
            outputs=[chatbot, products_display, cart_display, virtual_tryon_sidebar, cart_remove_buttons_container, cart_remove_buttons_container] + remove_rows + remove_btn_components
        ).then(lambda: "", outputs=[msg])
        
        # Bind individual remove button events
        def create_remove_handler(index):
            def remove_handler():
                return ui.handle_direct_removal(index, [])
            return remove_handler
        
        for i, (remove_row, remove_btn) in enumerate(remove_buttons):
            remove_btn.click(
                create_remove_handler(i),
                inputs=[],
                outputs=[chatbot, products_display, cart_display, virtual_tryon_sidebar, cart_remove_buttons_container, cart_remove_buttons_container] + remove_rows + remove_btn_components
            )
        
        msg.submit(
            send_message,
            inputs=[msg, chatbot],
            outputs=[chatbot, products_display, cart_display, virtual_tryon_sidebar, cart_remove_buttons_container, cart_remove_buttons_container] + remove_rows + remove_btn_components
        ).then(lambda: "", outputs=[msg])
        
        clear_btn.click(clear_conversation, outputs=[chatbot, products_display, cart_display, msg, virtual_tryon_sidebar, cart_remove_buttons_container, cart_remove_buttons_container] + remove_rows + remove_btn_components)
        
        # Virtual Try-On Event Handlers
        def handle_photo_upload(photo_path):
            """Handle photo upload for virtual try-on"""
            if photo_path:
                try:
                    # Process the photo and store it
                    ui.current_user_photo = photo_path
                    return gr.update(visible=True), "✅ Photo uploaded! Ready for virtual try-on."
                except Exception as e:
                    return gr.update(visible=False), f"❌ Error uploading photo: {str(e)}"
            return gr.update(visible=False), "Please upload a photo first."
        
        def handle_virtual_tryon():
            """Handle virtual try-on request"""
            try:
                if not ui.current_user_photo:
                    return "❌ Please upload your photo first!"
                
                # Get current cart items
                cart_items = ui.extract_cart_from_state([])
                if not cart_items:
                    return "❌ Your cart is empty! Add some items first."
                
                # Process virtual try-on
                result = ui.process_virtual_tryon(cart_items, ui.current_user_photo)
                return result
                
            except Exception as e:
                return f"❌ Virtual try-on error: {str(e)}"
        
        # Bind Virtual Try-On Events
        upload_btn.click(
            handle_photo_upload,
            inputs=[photo_upload],
            outputs=[tryon_btn, tryon_results]
        )
        
        tryon_btn.click(
            handle_virtual_tryon,
            outputs=[tryon_results]
        )
    
    return interface

if __name__ == "__main__":
    interface = create_assistify_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7863,
        share=False
    )