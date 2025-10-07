"""
Complete Gradio App for Outfitter.ai with Cart Functionality
Production-ready implementation with real backend integration and shopping cart
"""

import gradio as gr
import asyncio
from typing import List, Dict, Any, Tuple, Optional
from main import OutfitterAssistant
import html
import json
import re

class ProductionShoppingUI:
    def __init__(self):
        self.assistant = OutfitterAssistant()
        self.assistant.setup_graph()
        self.conversation_history = []
        self.current_products = []
        self.current_cart = []
        
    def extract_products_from_state(self, conversation_result: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract products from conversation state.
        Works with your existing backend to get real product data.
        """
        
        try:
            # Method 1: Check if the assistant has stored products
            if hasattr(self.assistant, 'last_products') and self.assistant.last_products:
                print(f"🔍 Found {len(self.assistant.last_products)} products from assistant state")
                return self.assistant.last_products
            
            # Method 2: Access from graph state
            if hasattr(self.assistant, '_last_state'):
                products = self.assistant._last_state.get('products_shown', [])
                if not products:
                    products = self.assistant._last_state.get('search_results', [])
                
                if products:
                    print(f"🔍 Found {len(products)} products from graph state")
                    return products
            
            # Method 3: Check conversation messages for product indicators
            if conversation_result:
                latest_message = ""
                for msg in reversed(conversation_result):
                    if isinstance(msg, dict) and msg.get("role") == "assistant":
                        latest_message = msg.get("content", "")
                        break
                
                # Check if products were mentioned in message
                product_indicators = [
                    "found" in latest_message.lower() and "product" in latest_message.lower(),
                    "🛍️" in latest_message,
                    "🏪" in latest_message,
                ]
                
                if any(product_indicators):
                    print("🔍 Product indicators found in message")
                    # Try to get from state one more time
                    if hasattr(self.assistant, 'get_current_products'):
                        return self.assistant.get_current_products()
            
            print("🔍 No products found in conversation state")
            return []
            
        except Exception as e:
            print(f"❌ Error extracting products: {e}")
            return []

    def extract_cart_from_state(self, conversation_result: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract cart items from conversation state.
        Returns list of cart items with quantities.
        """
        
        try:
            # Method 1: Check if assistant has get_current_cart method
            if hasattr(self.assistant, 'get_current_cart'):
                cart_items = self.assistant.get_current_cart()
                print(f"🛒 Found {len(cart_items)} items from get_current_cart()")
                return cart_items
            
            # Method 2: Access from last state
            if hasattr(self.assistant, '_last_state'):
                cart_items = self.assistant._last_state.get('selected_products', [])
                print(f"🛒 Found {len(cart_items)} items from _last_state")
                return cart_items
            
            # Method 3: Try to get from graph state
            if hasattr(self.assistant, 'graph') and hasattr(self.assistant, 'session_id'):
                try:
                    config = {"configurable": {"thread_id": self.assistant.session_id}}
                    if hasattr(self.assistant.graph, 'get_state'):
                        current_state = self.assistant.graph.get_state(config)
                        if current_state and hasattr(current_state, 'values'):
                            cart_items = current_state.values.get('selected_products', [])
                            print(f"🛒 Found {len(cart_items)} items from graph.get_state()")
                            return cart_items
                except Exception as e:
                    print(f"⚠️ Could not access graph state for cart: {e}")
            
            print("🛒 No cart items found")
            return []
            
        except Exception as e:
            print(f"❌ Error extracting cart: {e}")
            return []
    
    def format_cart_for_display(self, cart_items: List[Dict[str, Any]]) -> str:
        """
        Format cart items as HTML for Gradio display.
        Shows items grouped by store with totals.
        """
        if not cart_items:
            return """
            <div class="cart-container">
                <div class="empty-cart">
                    <div class="empty-cart-icon">🛒</div>
                    <h3>Your cart is empty</h3>
                    <p>Select products from search results to add them to your cart</p>
                </div>
            </div>
            """
        
        # Group by store
        by_store = {}
        total_items = 0
        total_price = 0.0
        
        for item in cart_items:
            store = item.get("store_name", "Unknown Store")
            if store not in by_store:
                by_store[store] = []
            by_store[store].append(item)
            
            quantity = item.get("quantity", 1)
            total_items += quantity
            
            # Calculate price
            price_str = item.get("price", "$0.00")
            price_match = re.search(r'\d+\.?\d*', price_str.replace(',', ''))
            if price_match:
                price_value = float(price_match.group())
                total_price += price_value * quantity
        
        # Build HTML
        html_parts = [f"""
        <div class="cart-container">
            <div class="cart-header">
                <h2>🛒 Your Cart</h2>
                <span class="cart-count">{total_items} item{'s' if total_items != 1 else ''}</span>
            </div>
        """]
        
        # Add items by store
        cart_index = 0
        for store_name, items in by_store.items():
            html_parts.append(f"""
            <div class="cart-store-section">
                <h3 class="cart-store-name">🏪 {html.escape(store_name)}</h3>
                <div class="cart-items">
            """)
            
            for item in items:
                quantity = item.get("quantity", 1)
                qty_badge = f'<span class="quantity-badge">x{quantity}</span>' if quantity > 1 else ''
                
                # Get product image
                image_url = item.get("image_url", "")
                if image_url:
                    image_html = f'<img src="{image_url}" alt="{html.escape(item.get("name", ""))}" onerror="this.src=\'https://via.placeholder.com/80x80/f1f5f9/64748b?text=No+Image\'">'
                else:
                    image_html = '<div class="cart-no-image">📦</div>'
                
                price_str = item.get("price", "N/A")
                
                html_parts.append(f"""
                <div class="cart-item" data-cart-index="{cart_index}">
                    <div class="cart-item-image">
                        {image_html}
                    </div>
                    <div class="cart-item-details">
                        <div class="cart-item-name">{html.escape(item.get('name', 'Unknown Product'))}</div>
                        <div class="cart-item-price">{html.escape(price_str)}{qty_badge}</div>
                        <div class="cart-item-meta">
                            <span class="cart-item-size">Size: {html.escape(item.get('selected_size', 'M'))}</span>
                        </div>
                    </div>
                </div>
                """)
                
                cart_index += 1
            
            html_parts.append("</div></div>")  # Close cart-items and cart-store-section
        
        # Add cart summary
        html_parts.append(f"""
        <div class="cart-summary">
            <div class="cart-total">
                <span>Total:</span>
                <span class="cart-total-amount">${total_price:.2f}</span>
            </div>
            <div class="cart-info">
                <p style="margin: 0; font-size: 0.875rem; color: #64748b; text-align: center;">
                    💡 Use chat to view cart details, remove items, or continue shopping
                </p>
            </div>
        </div>
        </div>
        """)
        
        return "\n".join(html_parts)
    
    async def handle_conversation(self, message: str, history: List) -> Tuple[List, str, str]:
        """
        Complete conversation handler with product and cart extraction.
        Returns: (updated_history, products_html, cart_html)
        """
        
        if not message.strip():
            return history, self.create_empty_products_html(), self.format_cart_for_display([])
        
        try:
            # Convert Gradio messages format to dictionary format
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
            
            # Process message with backend
            updated_history_dicts = await self.assistant.run_conversation(message, history_dicts)
            
            # Extract products and cart
            products = self.extract_products_from_state(updated_history_dicts)
            cart_items = self.extract_cart_from_state(updated_history_dicts)
            
            # Update internal state
            if products:
                self.current_products = products
            
            self.current_cart = cart_items
            
            # Format displays
            products_html = self.create_products_grid_html(products) if products else self.create_empty_products_html()
            cart_html = self.format_cart_for_display(cart_items)
            
            return updated_history_dicts, products_html, cart_html
            
        except Exception as e:
            print(f"❌ Error in handle_conversation: {e}")
            import traceback
            traceback.print_exc()
            error_msg = f"I encountered an error while processing your request. Please try again."
            error_history = history + [
                {"role": "user", "content": message}, 
                {"role": "assistant", "content": error_msg}
            ]
            return error_history, self.create_error_html(str(e)), self.format_cart_for_display([])

    def create_modern_css(self):
        """Modern CSS styling for high-quality appearance"""
        return """
        /* Modern Design System */
        :root {
            --primary-color: #2563eb;
            --primary-hover: #1d4ed8;
            --secondary-color: #64748b;
            --success-color: #059669;
            --warning-color: #d97706;
            --error-color: #dc2626;
            --background: #ffffff;
            --surface: #f8fafc;
            --border: #e2e8f0;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            --radius: 12px;
            --radius-sm: 8px;
        }
        
        /* Global Overrides */
        .gradio-container {
            max-width: 1600px !important;
            margin: 0 auto !important;
            background: var(--surface) !important;
        }
        
        /* Header Styling */
        .main-header {
            background: linear-gradient(135deg, var(--primary-color), #3b82f6) !important;
            color: white !important;
            padding: 2rem !important;
            margin: -1rem -1rem 2rem -1rem !important;
            border-radius: 0 0 var(--radius) var(--radius) !important;
            text-align: center !important;
        }
        
        .main-header h1 {
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            margin: 0 0 0.5rem 0 !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        }
        
        .main-header p {
            font-size: 1.2rem !important;
            opacity: 0.9 !important;
            margin: 0 !important;
        }
        
        /* Chat Interface Styling */
        .chat-container {
            background: var(--background) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius) !important;
            box-shadow: var(--shadow) !important;
            overflow: hidden !important;
        }
        
        /* Products Container */
        .products-container {
            background: var(--background) !important;
            border-radius: var(--radius) !important;
            padding: 1.5rem !important;
            box-shadow: var(--shadow) !important;
            min-height: 400px !important;
        }
        
        /* Responsive Design */
        @media (max-width: 1024px) {
            .main-header h1 {
                font-size: 2rem !important;
            }
            
            .main-header p {
                font-size: 1rem !important;
            }
        }
        """

    def create_product_cards_css(self):
        """CSS for premium product cards"""
        return """
        /* Products Header */
        .products-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }
        
        .products-count h3 {
            margin: 0 0 0.25rem 0;
            color: var(--text-primary);
            font-size: 1.25rem;
            font-weight: 600;
        }
        
        .products-count p {
            margin: 0;
            color: var(--text-secondary);
            font-size: 0.875rem;
        }
        
        /* Products Grid */
        .products-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        /* Product Card */
        .product-card {
            background: var(--background);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
            box-shadow: var(--shadow);
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
        }
        
        .product-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
            border-color: var(--primary-color);
        }
        
        /* Product Image */
        .product-image-container {
            position: relative;
            height: 220px;
            overflow: hidden;
            background: var(--surface);
        }
        
        .product-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }
        
        .product-card:hover .product-image {
            transform: scale(1.05);
        }
        
        /* Badges */
        .sale-badge {
            position: absolute;
            top: 0.75rem;
            left: 0.75rem;
            background: var(--error-color);
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: var(--radius-sm);
            font-size: 0.75rem;
            font-weight: 600;
            z-index: 2;
        }
        
        .store-badge {
            position: absolute;
            bottom: 0.75rem;
            left: 0.75rem;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: var(--radius-sm);
            font-size: 0.75rem;
            font-weight: 500;
            z-index: 2;
        }
        
        /* Product Content */
        .product-content {
            padding: 1rem;
        }
        
        .product-title {
            margin: 0 0 0.75rem 0;
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-primary);
            line-height: 1.4;
            height: 2.8em;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        
        .product-price {
            font-size: 1.125rem;
            font-weight: 700;
            color: var(--primary-color);
        }
        
        /* Product Actions */
        .product-actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 1rem;
        }
        
        .view-btn {
            flex: 1;
            padding: 0.625rem 0.75rem;
            border: none;
            border-radius: var(--radius-sm);
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            text-align: center;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.25rem;
            background: var(--primary-color);
            color: white;
        }
        
        .view-btn:hover {
            background: var(--primary-hover);
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .products-grid {
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 1rem;
            }
        }
        """
    
    def create_cart_css(self):
        """CSS for cart display"""
        return """
        /* Cart Container */
        .cart-container {
            background: white;
            border-radius: var(--radius);
            padding: 1.5rem;
            box-shadow: var(--shadow);
            max-height: 600px;
            overflow-y: auto;
        }
        
        .cart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid var(--border);
        }
        
        .cart-header h2 {
            margin: 0;
            font-size: 1.5rem;
            color: var(--text-primary);
        }
        
        .cart-count {
            background: var(--primary-color);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 600;
        }
        
        /* Empty Cart */
        .empty-cart {
            text-align: center;
            padding: 3rem 1rem;
            color: var(--text-secondary);
        }
        
        .empty-cart-icon {
            font-size: 64px;
            margin-bottom: 1rem;
            opacity: 0.3;
        }
        
        .empty-cart h3 {
            color: var(--text-primary);
            margin: 0 0 0.5rem 0;
        }
        
        .empty-cart p {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }
        
        /* Store Section */
        .cart-store-section {
            margin-bottom: 1.5rem;
        }
        
        .cart-store-name {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 0.75rem;
            padding: 0.5rem 0.75rem;
            background: var(--surface);
            border-radius: var(--radius-sm);
        }
        
        /* Cart Items */
        .cart-items {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }
        
        .cart-item {
            display: flex;
            gap: 0.75rem;
            padding: 0.75rem;
            background: var(--surface);
            border-radius: var(--radius-sm);
            transition: all 0.2s;
        }
        
        .cart-item:hover {
            background: var(--border);
        }
        
        .cart-item-image {
            width: 80px;
            height: 80px;
            border-radius: var(--radius-sm);
            overflow: hidden;
            flex-shrink: 0;
            background: white;
        }
        
        .cart-item-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .cart-no-image {
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            background: var(--surface);
        }
        
        .cart-item-details {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }
        
        .cart-item-name {
            font-weight: 600;
            color: var(--text-primary);
            font-size: 0.9rem;
            line-height: 1.3;
        }
        
        .cart-item-price {
            color: var(--primary-color);
            font-weight: 600;
            font-size: 1rem;
        }
        
        .quantity-badge {
            background: var(--success-color);
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            margin-left: 0.5rem;
        }
        
        .cart-item-meta {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        
        .cart-item-size {
            background: white;
            padding: 2px 8px;
            border-radius: 4px;
            border: 1px solid var(--border);
        }
        
        /* Cart Summary */
        .cart-summary {
            margin-top: 1.5rem;
            padding-top: 1rem;
            border-top: 2px solid var(--border);
        }
        
        .cart-total {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            font-size: 1.25rem;
            font-weight: 600;
        }
        
        .cart-total-amount {
            color: var(--success-color);
            font-size: 1.5rem;
        }
        
        .cart-info {
            padding: 0.75rem;
            background: var(--surface);
            border-radius: var(--radius-sm);
        }
        
        /* Scrollbar Styling */
        .cart-container::-webkit-scrollbar {
            width: 8px;
        }
        
        .cart-container::-webkit-scrollbar-track {
            background: var(--surface);
            border-radius: 4px;
        }
        
        .cart-container::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }
        
        .cart-container::-webkit-scrollbar-thumb:hover {
            background: var(--secondary-color);
        }
        """
    
    def create_header_html(self):
        """Create modern header with branding"""
        return """
        <div class="main-header">
            <h1>🛍️ Outfitter.ai</h1>
            <p>Your AI-powered shopping assistant with smart cart management</p>
        </div>
        """
    
    def create_empty_products_html(self):
        """Create placeholder for products area"""
        return """
        <div class="products-container">
            <div style="text-align: center; color: #64748b; padding: 3rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">👕</div>
                <h3 style="margin: 0 0 0.5rem 0; color: #334155;">Products will appear here</h3>
                <p style="margin: 0; font-size: 0.95rem;">Start by telling me what you're looking for...</p>
            </div>
        </div>
        """
        
    def create_product_card_html(self, product: Dict[str, Any], index: int) -> str:
        """Create a premium product card with modern design"""
        
        name = html.escape(product.get("name", "Unknown Product"))
        price = html.escape(product.get("price", "Price unavailable"))
        url = product.get("url", "#")
        image_url = product.get("image_url", "https://via.placeholder.com/300x300/f1f5f9/64748b?text=No+Image")
        
        fallback_url = "https://via.placeholder.com/400x400/f1f5f9/64748b?text=Loading..."
        store = html.escape(product.get("store_name", "Unknown Store"))
        is_on_sale = product.get("is_on_sale", False)
        
        # Sale badge
        sale_badge = '<div class="sale-badge"><span>🔥 SALE</span></div>' if is_on_sale else ""
        
        # Store badge
        store_colors = {
            "CultureKings": "#ff6b35",
            "Universal Store": "#2563eb", 
        }
        store_color = store_colors.get(store, "#64748b")
        
        return f"""
        <div class="product-card" data-index="{index}">
            <div class="product-image-container">
                <img 
                    src="{image_url}" 
                    alt="{name}"
                    class="product-image"
                    onerror="this.src='{fallback_url}'"
                    loading="lazy"
                />
                {sale_badge}
                <div class="store-badge" style="background-color: {store_color};">
                    {store}
                </div>
            </div>
            
            <div class="product-content">
                <h3 class="product-title" title="{name}">{name}</h3>
                
                <div class="product-price-container">
                    <span class="product-price">{price}</span>
                </div>
                
                <div class="product-actions">
                    <a href="{url}" target="_blank" rel="noopener noreferrer" class="view-btn">
                        <span>View Product</span>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                            <polyline points="15,3 21,3 21,9"></polyline>
                            <line x1="10" y1="14" x2="21" y2="3"></line>
                        </svg>
                    </a>
                </div>
            </div>
        </div>
        """
    
    def create_products_grid_html(self, products: List[Dict[str, Any]]) -> str:
        """Create a responsive grid of product cards"""
        
        if not products:
            return self.create_empty_products_html()
        
        # Header with product count
        header = f"""
        <div class="products-header">
            <div class="products-count">
                <h3>Found {len(products)} products</h3>
                <p>Use chat to select products by number (e.g., "I want #2")</p>
            </div>
        </div>
        """
        
        # Product cards grid
        cards_html = '<div class="products-grid">'
        
        for index, product in enumerate(products, 1):
            cards_html += self.create_product_card_html(product, index)
        
        cards_html += '</div>'
        
        return f"""
        <div class="products-container">
            {header}
            {cards_html}
        </div>
        """

    def create_error_html(self, error: str) -> str:
        """Create error state HTML"""
        return f"""
        <div class="products-container">
            <div style="text-align: center; color: #dc2626; padding: 3rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
                <h3>Something went wrong</h3>
                <p>Please try your search again.</p>
                <details style="margin-top: 1rem;">
                    <summary>Error Details</summary>
                    <code>{html.escape(error)}</code>
                </details>
            </div>
        </div>
        """
    
    def get_example_searches(self) -> List[str]:
        """Get example search queries"""
        return [
            "Show me black hoodies",
            "I need white sneakers", 
            "Looking for casual shirts under $50",
            "Red hoodies size L",
            "Blue jeans",
            "Show my cart"
        ]
    
    def create_complete_css(self) -> str:
        """Complete CSS including all components"""
        return self.create_modern_css() + self.create_product_cards_css() + self.create_cart_css()

def create_complete_interface():
    """Create the complete production-ready Gradio interface with cart"""
    
    ui = ProductionShoppingUI()
    
    with gr.Blocks(
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate", 
            neutral_hue="slate",
            radius_size="lg",
            text_size="md"
        ),
        css=ui.create_complete_css(),
        title="Outfitter.ai - AI Shopping Assistant with Cart",
        analytics_enabled=False
    ) as interface:
        
        # Header
        gr.HTML(ui.create_header_html())
        
        # Main layout - 3 columns: Chat, Products, Cart
        with gr.Row(equal_height=False):
            # LEFT: Chat Interface
            with gr.Column(scale=1, min_width=350):
                gr.Markdown("### 💬 Chat with Assistant")
                
                chatbot = gr.Chatbot(
                    label="",
                    height=500,
                    show_label=False,
                    avatar_images=("👤", "🤖"),
                    bubble_full_width=False,
                    show_copy_button=True,
                    elem_classes=["chat-container"],
                    type="messages"
                )
                
                # Input area
                with gr.Row():
                    msg = gr.Textbox(
                        label="",
                        placeholder="Tell me what you're looking for...",
                        lines=1,
                        show_label=False,
                        scale=4
                    )
                    
                    send_btn = gr.Button(
                        "Send",
                        variant="primary",
                        scale=1
                    )
                
                # Control buttons
                with gr.Row():
                    clear_btn = gr.Button(
                        "Clear Chat",
                        variant="secondary",
                        scale=1
                    )
                    
                    examples_dropdown = gr.Dropdown(
                        choices=ui.get_example_searches(),
                        label="Examples",
                        value=None,
                        scale=2
                    )
            
            # MIDDLE: Products Display
            with gr.Column(scale=2, min_width=400):
                gr.Markdown("### 🛍️ Products Found")
                
                products_display = gr.HTML(
                    value=ui.create_empty_products_html(),
                    elem_classes=["products-container"]
                )
            
            # RIGHT: Shopping Cart
            with gr.Column(scale=1, min_width=300):
                gr.Markdown("### 🛒 Shopping Cart")
                
                cart_display = gr.HTML(
                    value=ui.format_cart_for_display([]),
                    elem_classes=["cart-container"]
                )
                
                # Cart instructions
                gr.Markdown("""
                **Cart Commands:**
                - "I want #2" - Add item to cart
                - "Show my cart" - View cart details
                - "Remove #1" - Remove item
                - "Clear cart" - Empty cart
                """, elem_classes=["cart-instructions"])
        
        # Event handlers
        async def send_message(message, history):
            return await ui.handle_conversation(message, history)
        
        def clear_conversation():
            empty_products = ui.create_empty_products_html()
            empty_cart = ui.format_cart_for_display([])
            return [], empty_products, empty_cart, ""
        
        def use_example(example):
            return example if example else ""
        
        # Event bindings
        send_btn.click(
            send_message,
            inputs=[msg, chatbot],
            outputs=[chatbot, products_display, cart_display]
        ).then(
            lambda: "",
            outputs=[msg]
        )
        
        msg.submit(
            send_message,
            inputs=[msg, chatbot],
            outputs=[chatbot, products_display, cart_display]
        ).then(
            lambda: "",
            outputs=[msg]
        )
        
        clear_btn.click(
            clear_conversation,
            outputs=[chatbot, products_display, cart_display, msg]
        )
        
        examples_dropdown.change(
            use_example,
            inputs=[examples_dropdown],
            outputs=[msg]
        ).then(
            lambda: None,
            outputs=[examples_dropdown]
        )
    
    return interface

if __name__ == "__main__":
    interface = create_complete_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        show_tips=False,
        favicon_path=None,
        app_kwargs={"docs_url": None, "redoc_url": None}
    )