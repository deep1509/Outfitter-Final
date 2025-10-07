"""
Updated main.py with real scraping integration and complete cart management
All cart persistence fixes applied
"""

import os
import uuid
import asyncio 
from typing import Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage
from agents.conversation_agents.needsAnalyzer import NeedsAnalyzer
from agents.conversation_agents.simpleClarificationAsker import SimpleClarificationAsker

from tools.hybrid_scraper import search_all_stores

from agents.state import OutfitterState
from agents.intent_classifier import RobustIntentClassifier
from agents.conversation_agents.greeterAgent import GreeterAgent
from agents.conversation_agents.clarificationAgent import ClarificationAgent
from agents.conversation_agents.generalResponderAgent import SimpleGeneralResponder

from tools.simple_product_verifier import SimpleProductVerifier
from agents.conversation_agents.selectionHandler import SelectionHandler
from agents.conversation_agents.cartManager import CartManager

# Load environment variables
load_dotenv()

class OutfitterAssistant:
    """
    Main Outfitter.ai shopping assistant using LangGraph with real scraping integration.
    Includes full cart management with state persistence.
    """
        
    def __init__(self):
        # Initialize all conversation agents
        self.intent_classifier = RobustIntentClassifier()
        self.greeter = GreeterAgent()
        self.needs_analyzer = NeedsAnalyzer()
        self.clarification_asker = SimpleClarificationAsker()
        self.general_responder = SimpleGeneralResponder()
        self.selection_handler = SelectionHandler()
        self.cart_manager = CartManager()
        
        # Memory for conversation persistence
        self.memory = MemorySaver()
        self.graph = None
        self.session_id = str(uuid.uuid4())
        
        # Store products and state for Gradio access
        self.last_products = []
        self._last_state = {}  # ADDED: Track last state for cart access

    def setup_graph(self):
        """Build the LangGraph workflow with complete cart management"""
        print("Setting up Outfitter.ai LangGraph with real scraping integration...")
        
        # Create the graph
        workflow = StateGraph(OutfitterState)
        
        # Add all nodes
        workflow.add_node("intent_classifier", self._intent_classifier_node)
        workflow.add_node("greeter", self._greeter_node)
        workflow.add_node("needs_analyzer", self._needs_analyzer_node)
        workflow.add_node("clarification_asker", self._clarification_node)
        workflow.add_node("general_responder", self._general_responder_node)
        workflow.add_node("parallel_searcher", self._real_parallel_searcher)
        workflow.add_node("product_presenter", self._product_presenter_node)
        workflow.add_node("selection_handler", self._selection_handler_node)
        workflow.add_node("cart_manager", self._cart_manager_node)
        workflow.add_node("checkout_handler", self._mock_checkout_handler)
        
        # Start edge
        workflow.add_edge(START, "intent_classifier")
        
        # Intent routing
        workflow.add_conditional_edges(
            "intent_classifier",
            self._route_after_intent_classification,
            {
                "greeter": "greeter",
                "needs_analyzer": "needs_analyzer",
                "selection_handler": "selection_handler",
                "cart_manager": "cart_manager",  # ADDED: Direct cart routing
                "checkout_handler": "checkout_handler",
                "general_responder": "general_responder",
                "clarification_asker": "clarification_asker"
            }
        )
        
        # Greeting routing
        workflow.add_conditional_edges(
            "greeter",
            self._route_after_greeting,
            {
                "needs_analyzer": "needs_analyzer",
                "wait_for_user": END
            }
        )
        
        # Needs analyzer routing
        workflow.add_conditional_edges(
            "needs_analyzer",
            self._route_after_needs_analysis,
            {
                "parallel_searcher": "parallel_searcher",
                "clarification_asker": "clarification_asker"
            }
        )
        
        # Parallel searcher routing
        workflow.add_conditional_edges(
            "parallel_searcher",
            self._route_after_search,
            {
                "product_presenter": "product_presenter",
                "clarification_asker": "clarification_asker",
                "general_responder": "general_responder"
            }
        )
        
        # Clarification routing  
        workflow.add_conditional_edges(
            "clarification_asker",
            self._route_after_clarification,
            {
                "needs_analyzer": "needs_analyzer",
                "wait_for_user": END
            }
        )
        
        # Product presenter routing
        workflow.add_conditional_edges(
            "product_presenter",
            self._route_after_presentation,
            {
                "selection_handler": "selection_handler",
                "wait_for_user": END
            }
        )
        
        # Selection handler routing - CRITICAL for cart
        workflow.add_conditional_edges(
            "selection_handler",
            self._route_after_selection,
            {
                "cart_manager": "cart_manager",  # Route to cart manager
                "checkout_handler": "checkout_handler",
                "product_presenter": "product_presenter",
                "wait_for_user": END
            }
        )
        
        # ADDED: Cart manager routing
        workflow.add_conditional_edges(
            "cart_manager",
            self._route_after_cart_action,
            {
                "wait_for_user": END,
                "product_presenter": "product_presenter",
                "checkout_handler": "checkout_handler"
            }
        )
        
        # End states
        workflow.add_edge("general_responder", END)
        workflow.add_edge("checkout_handler", END)
        
        # Compile with memory
        self.graph = workflow.compile(checkpointer=self.memory)
        print("✅ Real scraping integration setup complete!")

    # ============ AGENT NODE WRAPPERS ============
    
    def _intent_classifier_node(self, state: OutfitterState) -> Dict[str, Any]:
        """Enhanced AI-powered intent classification node"""
        return self.intent_classifier.classify_intent(state)
    
    def _needs_analyzer_node(self, state: OutfitterState) -> Dict[str, Any]:
        """AI-powered needs analysis and extraction node"""
        return self.needs_analyzer.analyze_needs(state)
    
    def _greeter_node(self, state: OutfitterState) -> Dict[str, Any]:
        """Enhanced personalized greeting node"""
        return self.greeter.greet_user(state)
    
    def _clarification_node(self, state: OutfitterState) -> Dict[str, Any]:
        """Simple clarification question generator node"""  
        return self.clarification_asker.ask_clarification(state)
    
    def _general_responder_node(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Enhanced AI-powered general response node.
        CRITICAL FIX: Preserves cart state across questions.
        """
        print("💬 GeneralResponder: Handling general query...")
        
        result = self.general_responder.respond_to_general_query(state)
        
        # CRITICAL: Preserve products_shown and awaiting_selection
        products_shown = state.get("products_shown", [])
        awaiting_selection = state.get("awaiting_selection", False)
        
        # CRITICAL FIX: Preserve cart state
        selected_products = state.get("selected_products", [])
        
        if products_shown and awaiting_selection:
            print(f"   ✓ Preserving {len(products_shown)} shown products for selection")
            result["products_shown"] = products_shown
            result["awaiting_selection"] = True
            result["conversation_stage"] = "presenting"
        
        # CRITICAL FIX: Always preserve cart
        if selected_products:
            print(f"   ✓ Preserving {len(selected_products)} items in cart")
            result["selected_products"] = selected_products
        else:
            # Even if empty, explicitly set it to preserve the field
            result["selected_products"] = []
        
        return result
    
    def _selection_handler_node(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Handle product selections.
        ADDED: Debug logging to track cart flow.
        """
        print("🛒 SelectionHandler: Processing product selection...")
        
        result = self.selection_handler.handle_selection(state)
        
        # DEBUG: Track what's being set
        print(f"   🔍 Selection result next_step: {result.get('next_step')}")
        print(f"   🔍 Pending additions: {len(result.get('pending_cart_additions', []))}")
        print(f"   🔍 Existing cart preserved: {len(result.get('selected_products', []))}")
        
        return result
    
    def _cart_manager_node(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Handle cart operations - add, remove, view, clear.
        ADDED: Comprehensive debug logging.
        """
        print(f"🛒 CART MANAGER NODE CALLED")
        print(f"   📦 Current cart: {len(state.get('selected_products', []))} items")
        print(f"   ➕ Pending additions: {len(state.get('pending_cart_additions', []))} items")
        print(f"   🔧 Operation: {state.get('cart_operation', 'add')}")
        
        result = self.cart_manager.process_cart_action(state)
        
        print(f"   ✅ After processing: {len(result.get('selected_products', []))} items in cart")
        
        return result
    
    # ============ REAL SCRAPING INTEGRATION NODES ============
    
    def _real_parallel_searcher(self, state: OutfitterState) -> Dict[str, Any]:
        """Real parallel searcher with client-side filtering and debug logging"""
        print("🔍 Starting real parallel search across stores...")
        search_criteria = state.get("search_criteria", {})
        search_query = self._build_search_query_from_criteria(search_criteria)
        
        if not search_query:
            search_query = "clothing"
        
        print(f"🔎 Searching for: '{search_query}' with criteria: {search_criteria}")
        
        try:
            # Run async scraping
            products = asyncio.run(search_all_stores(
                query=search_query,
                max_products=100
            ))
            
            print(f"✅ Found {len(products)} products from scraping")
            
            # Convert ProductData to dicts
            product_dicts = []
            for product in products:
                product_dict = {
                    "name": product.name,
                    "price": product.price,
                    "brand": product.brand,
                    "url": product.url,
                    "image_url": product.image_url,
                    "store_name": product.store_name,
                    "is_on_sale": product.is_on_sale,
                    "extracted_at": product.extracted_at.isoformat() if product.extracted_at else None
                }
                product_dicts.append(product_dict)
            
            # Client-side filtering
            if len(product_dicts) > 0:
                from tools.simple_product_verifier import SimpleProductVerifier
                verifier = SimpleProductVerifier()
                
                user_request = self._build_user_request_string(search_criteria, search_query)
                
                print(f"🔍 Applying AI filter for: '{user_request}'")
                original_count = len(product_dicts)
                
                product_dicts = verifier.filter_relevant_products(user_request, product_dicts)
                
                print(f"📊 Filtering result: {original_count} → {len(product_dicts)} products")
            
            if len(product_dicts) > 0:
                return {
                    "messages": [AIMessage(content=f"Great! I found {len(product_dicts)} products from multiple stores. Let me show you:")],
                    "search_results": product_dicts,
                    "conversation_stage": "presenting",
                    "next_step": "product_presenter"
                }
            else:
                return self._handle_no_products_found_sync(search_query, search_criteria)
                
        except Exception as e:
            print(f"❌ Scraping error: {e}")
            import traceback
            traceback.print_exc()
            return self._handle_scraping_error_sync(search_query, str(e))
    
    def _product_presenter_node(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Present products with relevance verification AND store for Gradio access.
        """
        print("📱 Formatting products for presentation with AI verification...")
        
        search_results = state.get("search_results", [])
        search_criteria = state.get("search_criteria", {})
        search_query = state.get("search_query", "items")
        
        if not search_results:
            self.last_products = []
            return self._handle_empty_presentation(search_query)
        
        # Build user request string
        user_request = self._build_user_request_string(search_criteria, search_query)
        
        # AI verification
        from tools.simple_product_verifier import SimpleProductVerifier
        verifier = SimpleProductVerifier()
        
        relevant_products = verifier.filter_relevant_products(user_request, search_results)
        
        # CRITICAL: Store products for Gradio access
        self.last_products = relevant_products
        print(f"🔗 Stored {len(relevant_products)} products for Gradio access")
        
        if not relevant_products:
            self.last_products = []
            
            message = f"""I found {len(search_results)} products but none actually matched your request for "{user_request}".

The products were different categories or colors than what you asked for.

Would you like me to:
1. Show you similar items anyway?
2. Try a different search?
3. Help refine your request?"""

            return {
                "messages": [AIMessage(content=message)],
                "products_shown": search_results,
                "verification_failed": True,
                "conversation_stage": "presenting",
                "next_step": "wait_for_user",
                "awaiting_selection": True
            }
        
        # Group by store and build presentation
        products_by_store = {}
        for product in relevant_products:
            store_name = product.get("store_name", "Unknown Store")
            if store_name not in products_by_store:
                products_by_store[store_name] = []
            products_by_store[store_name].append(product)
        
        presentation = self._build_product_presentation(products_by_store, user_request)
        selection_instructions = self._build_selection_instructions(len(relevant_products))
        
        full_message = f"{presentation}\n\n{selection_instructions}"
        
        return {
            "messages": [AIMessage(content=full_message)],
            "products_shown": relevant_products,
            "conversation_stage": "presenting", 
            "next_step": "wait_for_user",
            "awaiting_selection": True,
            "verification_completed": True
        }
    
    # ============ ROUTING LOGIC ============
    
    def _route_after_intent_classification(self, state: OutfitterState) -> str:
        """
        Smart routing based on intent with cart awareness.
        """
        import re
        
        next_step = state.get("next_step", "general_responder")
        current_intent = state.get("current_intent", "")
        
        # Check if products are shown and awaiting interaction
        products_shown = state.get("products_shown", [])
        awaiting_selection = state.get("awaiting_selection", False)
        
        if products_shown and awaiting_selection:
            # Get user's message
            messages = state.get("messages", [])
            if messages:
                last_msg = messages[-1]
                content = ""
                if hasattr(last_msg, 'content'):
                    content = last_msg.content
                elif isinstance(last_msg, dict):
                    content = last_msg.get('content', '')
                
                content_lower = content.lower()
                
                # Selection indicators
                selection_keywords = [
                    '#', 'number', 'option',
                    'i want', 'i\'ll take', 'i like', 
                    'add', 'choose', 'select', 'pick',
                    'get me', 'buy', 'purchase'
                ]
                
                # Question indicators
                question_keywords = [
                    'how', 'what', 'why', 'which', 'when', 'where',
                    'should i', 'can you', 'tell me', 'show me more',
                    'style', 'match', 'wear', 'look', 'advice',
                    'recommend', 'suggest', 'help', 'think'
                ]
                
                # Check for ordinal numbers
                ordinals = ['first', 'second', 'third', 'fourth', 'fifth']
                has_ordinal = any(ord in content_lower for ord in ordinals)
                
                # Check for explicit numbers
                has_numbers = bool(re.search(r'\b\d+\b', content))
                
                # Decision logic
                is_selection = (
                    any(keyword in content_lower for keyword in selection_keywords) or
                    (has_numbers and not any(q in content_lower for q in question_keywords)) or
                    has_ordinal
                )
                
                is_question = any(keyword in content_lower for keyword in question_keywords)
                
                # Route based on primary intent
                if is_selection and not is_question:
                    print(f"   🛒 Routing: SELECTION detected → selection_handler")
                    return "selection_handler"
                
                if is_question:
                    print(f"   💬 Routing: QUESTION detected → general_responder")
                    return "general_responder"
                
                # If unclear but has numbers, assume selection
                if has_numbers:
                    print(f"   🔢 Routing: Numbers detected → selection_handler")
                    return "selection_handler"
        
        # Cart intent routing
        if current_intent == "cart":
            print(f"   🛒 Routing: CART intent → cart_manager")
            return "cart_manager"
        
        # Existing routing logic
        if next_step == "clarification_asker" and current_intent == "search":
            return "needs_analyzer"
        
        if state.get("needs_clarification", False):
            return "clarification_asker"
        
        return next_step

    def _route_after_greeting(self, state: OutfitterState) -> str:
        """Route after greeting"""
        next_step = state.get("next_step", "wait_for_user")
        
        if next_step == "needs_analyzer":
            return "needs_analyzer"
        
        return "wait_for_user"
    
    def _route_after_needs_analysis(self, state: OutfitterState) -> str:
        """Route after needs analysis"""
        return state.get("next_step", "clarification_asker")
    
    def _route_after_clarification(self, state: OutfitterState) -> str:
        """Route after clarification - always wait for user"""
        return "wait_for_user"
    
    def _route_after_search(self, state: OutfitterState) -> str:
        """Route after parallel search"""
        
        print(f"🔄 ROUTING AFTER SEARCH:")
        
        search_results = state.get("search_results", [])
        next_step = state.get("next_step", None)
        conversation_stage = state.get("conversation_stage", "unknown")
        scraping_error = state.get("scraping_error", False)
        
        print(f"   🔍 search_results count: {len(search_results)}")
        print(f"   ➡️  next_step: {next_step}")
        print(f"   🎭 conversation_stage: {conversation_stage}")
        
        # Route by explicit next_step
        if next_step == "product_presenter":
            print("✅ Routing to product_presenter")
            return "product_presenter"
        
        # Route by results count
        if len(search_results) > 0:
            print(f"✅ Found {len(search_results)} products - routing to product_presenter")
            return "product_presenter"
        
        # Error handling
        if scraping_error:
            print("❌ Routing to general_responder (scraping error)")
            return "general_responder"
        
        # Default
        print("🔄 Routing to clarification_asker")
        return "clarification_asker"
    
    def _route_after_selection(self, state: OutfitterState) -> str:
        """
        Route after selection - CRITICAL for cart persistence.
        """
        next_step = state.get("next_step", "cart_manager")
        
        print(f"   🔄 Routing after selection: next_step = {next_step}")
        
        if next_step == "checkout_handler":
            return "checkout_handler"
        
        if next_step == "product_presenter":
            return "product_presenter"
        
        # DEFAULT: Route to cart_manager to persist selections
        print(f"   🔄 → cart_manager (to add items)")
        return "cart_manager"
    
    def _route_after_presentation(self, state: OutfitterState) -> str:
        """Route after showing products"""
        products_shown = state.get("products_shown", [])
        
        if products_shown:
            return "wait_for_user"
        
        return "wait_for_user"
    
    def _route_after_cart_action(self, state: OutfitterState) -> str:
        """
        Route after cart operation completes.
        ADDED: Critical routing method for cart flow.
        """
        next_step = state.get("next_step", "wait_for_user")
        
        print(f"   🔄 Routing after cart action: {next_step}")
        
        if next_step == "product_presenter":
            return "product_presenter"
        
        if next_step == "checkout_handler":
            return "checkout_handler"
        
        return "wait_for_user"
    
    # ============ HELPER METHODS ============
    
    def _build_search_query_from_criteria(self, criteria: Dict[str, Any]) -> str:
        """Build a search query string from extracted user criteria"""
        query_parts = []
        
        color = criteria.get("color_preference", "").strip()
        if color:
            query_parts.append(color)
        
        category = criteria.get("category", "").strip()
        if category:
            query_parts.append(category)
        else:
            query_parts.append("clothing")
        
        style = criteria.get("style_preference", "").strip()
        if style:
            query_parts.append(style)
        
        if query_parts:
            return " ".join(query_parts)
        
        return "clothing"
    
    def _build_user_request_string(self, criteria: Dict[str, Any], query: str) -> str:
        """Build clear user request string for AI verification"""
        parts = []
        
        color = criteria.get("color_preference", "")
        if color:
            parts.append(color)
        
        category = criteria.get("category", "")
        if category:
            parts.append(category)
        
        size = criteria.get("size", "")
        if size:
            parts.append(f"size {size}")
        
        style = criteria.get("style_preference", "")
        if style:
            parts.append(style)
        
        if parts:
            return " ".join(parts)
        
        return query if query != "items" else "clothing"
    
    def _build_product_presentation(self, products_by_store: Dict[str, List[Dict]], query: str) -> str:
        """Build formatted product presentation organized by store"""
        presentation_parts = []
        item_number = 1
        
        total_products = sum(len(products) for products in products_by_store.values())
        store_count = len(products_by_store)
        
        presentation_parts.append(f"🛍️ Found {total_products} great options from {store_count} stores for '{query}':")
        presentation_parts.append("")
        
        for store_name, products in products_by_store.items():
            if not products:
                continue
                
            presentation_parts.append(f"🏪 **{store_name}:**")
            
            for product in products[:5]:
                product_line = self._format_single_product(product, item_number)
                presentation_parts.append(product_line)
                item_number += 1
            
            presentation_parts.append("")
        
        return "\n".join(presentation_parts)
    
    def _format_single_product(self, product: Dict[str, Any], item_number: int) -> str:
        """Format a single product for display"""
        name = product.get("name", "Unknown Product")
        price = product.get("price", "Price unavailable")
        is_on_sale = product.get("is_on_sale", False)
        url = product.get("url", "")
        
        sale_indicator = " 🔥" if is_on_sale else ""
        
        product_line = f"{item_number}. **{name}**{sale_indicator}"
        product_line += f"\n   💰 {price}"
        
        if url:
            product_line += f"\n   🔗 {url}"
        
        return product_line
    
    def _build_selection_instructions(self, product_count: int) -> str:
        """Build clear instructions for product selection"""
        if product_count <= 3:
            return """💡 **What would you like to do?**
• Tell me the number of any item you're interested in (e.g., "I like #1")
• Ask questions about sizing, colors, or details
• Request a different search or more options
• Get styling advice for any of these items"""
        
        elif product_count <= 8:
            return """💡 **How to proceed:**
• Choose items by number (e.g., "Show me more about #2 and #5") 
• Ask for specific details about sizing, materials, or colors
• Request to see more options or try a different search
• Get styling suggestions for putting together an outfit"""
        
        else:
            return """💡 **Next steps:**
• Select specific items by number (e.g., "I'm interested in #1, #3, and #7")
• Ask me to narrow down options based on price, style, or store preference
• Request more details about any items that caught your eye
• Let me know if you'd like styling advice or outfit suggestions"""
    
    def _handle_empty_presentation(self, query: str) -> Dict[str, Any]:
        """Handle case where no products to present"""
        message = f"""I don't have any products to show you right now for '{query}'. 

This could be because:
• No products were found in the search
• There was a technical issue with the stores
• The search criteria might need adjustment

Would you like to:
1. Try searching for something different
2. Broaden your search terms
3. Get some fashion advice while we figure out what you need"""

        return {
            "messages": [AIMessage(content=message)],
            "products_shown": [],
            "conversation_stage": "discovery",
            "next_step": "clarification_asker"
        }
    
    def _handle_no_products_found_sync(self, query: str, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Handle case where no products are found"""
        message = f"""I searched for '{query}' but couldn't find any products right now. 

Would you like me to:
1. Try a broader search with different terms
2. Search for similar items  
3. Help you refine your search criteria"""

        return {
            "messages": [AIMessage(content=message)],
            "search_results": [],
            "search_query": query,
            "search_successful": False,
            "needs_clarification": True,
            "conversation_stage": "discovery", 
            "next_step": "clarification_asker"
        }

    def _handle_scraping_error_sync(self, query: str, error: str) -> Dict[str, Any]:
        """Handle scraping errors"""
        print(f"Scraping error details: {error}")
        
        message = """I'm having trouble accessing the stores right now. Let me help you in other ways - what would you like to know about fashion or styling?"""

        return {
            "messages": [AIMessage(content=message)],
            "search_results": [],
            "search_query": query,
            "search_successful": False,
            "scraping_error": True,
            "conversation_stage": "general",
            "next_step": "general_responder"
        }
    
    def _mock_checkout_handler(self, state: OutfitterState) -> Dict[str, Any]:
        """Mock checkout handler"""
        return {
            "messages": [AIMessage(content="🔧 Checkout feature coming soon! Your cart has been saved.")],
            "next_step": "wait_for_user"
        }
    
    # ============ GRADIO INTERFACE METHODS ============
    
    def get_current_cart(self) -> List[Dict[str, Any]]:
        """
        Get current cart items for Gradio UI.
        ADDED: Essential method for cart display.
        """
        try:
            if hasattr(self, '_last_state'):
                cart = self._last_state.get("selected_products", [])
                print(f"🛒 get_current_cart(): Returning {len(cart)} items")
                return cart
            
            print(f"🛒 get_current_cart(): No _last_state, returning empty cart")
            return []
        except Exception as e:
            print(f"❌ Error getting cart: {e}")
            return []
    
    # ============ MAIN INTERFACE ============
    
    async def run_conversation(self, message: str, history: List[Dict]) -> List[Dict]:
        """
        Run conversation with complete cart management.
        UPDATED: Stores state for cart access.
        """
        print(f"🤖 Processing: '{message}' with {len(history)} history items")
        
        config = {"configurable": {"thread_id": self.session_id}}
        
        # Convert history to proper message format
        from langchain_core.messages import HumanMessage, AIMessage
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Add new user message
        messages.append(HumanMessage(content=message))
        
        # Build state
        user_message_count = len([msg for msg in messages if isinstance(msg, HumanMessage)])
        
        state = {
            "messages": messages,
            "current_intent": None,
            "search_criteria": {},
            "search_results": [],
            "selected_products": [],
            "next_step": None,
            "needs_clarification": False,
            "conversation_stage": "greeting" if user_message_count == 1 else "discovery",
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat() if user_message_count == 1 else None
        }
        
        try:
            # Run the conversation graph
            result = await self.graph.ainvoke(state, config=config)
            
            # CRITICAL: Store state for cart access
            self._last_state = result
            
            # Debug logging
            print(f"🔄 DEBUG: Final state conversation_stage: {result.get('conversation_stage')}")
            print(f"🔄 DEBUG: Final cart items: {len(result.get('selected_products', []))}")
            print(f"✅ Graph execution completed")
            
            # Extract the latest assistant message
            assistant_messages = [msg for msg in result.get("messages", []) if isinstance(msg, AIMessage)]
            if assistant_messages:
                latest_response = assistant_messages[-1].content
            else:
                latest_response = "I'm here to help you find great clothing! What are you looking for today?"
            
            # Format response for interface
            user_msg = {"role": "user", "content": message}
            assistant_msg = {"role": "assistant", "content": latest_response}
            
            return history + [user_msg, assistant_msg]
            
        except Exception as e:
            print(f"❌ Conversation error: {e}")
            import traceback
            traceback.print_exc()
            
            # Error handling
            user_msg = {"role": "user", "content": message}
            error_msg = {"role": "assistant", "content": "I apologize for the technical hiccup. I'm your fashion and shopping assistant - what can I help you find today?"}
            return history + [user_msg, error_msg]
    
    def cleanup(self):
        """Clean up conversation resources"""
        print("🧹 Cleaning up conversation resources...")


# ============ MAIN EXECUTION ============

def main():
    """Test the Outfitter.ai setup"""
    print("🚀 Starting Outfitter.ai with Complete Cart Management...")
    
    assistant = OutfitterAssistant()
    assistant.setup_graph()
    
    print("\n✅ Setup complete!")
    print("🎯 Features:")
    print("   ✓ AI-powered intent classification")
    print("   ✓ Smart clarification questions")
    print("   ✓ Real product search and presentation")
    print("   ✓ Complete cart management with persistence")
    print("   ✓ Cart survives questions and interactions")
    print("\n🛍️ Ready to shop!")

if __name__ == "__main__":
    main()