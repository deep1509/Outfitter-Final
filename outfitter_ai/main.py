"""
Updated main.py with real scraping integration
Replace your current main.py with this version
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



# Load environment variables
load_dotenv()

class OutfitterAssistant:
    """
    Main Outfitter.ai shopping assistant using LangGraph with real scraping integration.
    Stage 2.3: Real Universal Store + CultureKings product search and presentation.
    """
        
    def __init__(self):
        # Initialize all conversation agents
        self.intent_classifier = RobustIntentClassifier()
        self.greeter = GreeterAgent()
        self.needs_analyzer = NeedsAnalyzer()  # NEW
        self.clarification_asker = SimpleClarificationAsker()  # UPDATED
        self.general_responder = SimpleGeneralResponder()
        
        # Memory for conversation persistence
        self.memory = MemorySaver()
        self.graph = None
        self.session_id = str(uuid.uuid4())
        
        self.last_products = []

    def setup_graph(self):
        """Build the LangGraph workflow with FIXED state propagation"""
        print("Setting up Outfitter.ai LangGraph with real scraping integration...")
        
        # Create the graph
        workflow = StateGraph(OutfitterState)
        
        # Add all nodes (keep your existing ones)
        workflow.add_node("intent_classifier", self._intent_classifier_node)
        workflow.add_node("greeter", self._greeter_node)
        workflow.add_node("needs_analyzer", self._needs_analyzer_node)
        workflow.add_node("clarification_asker", self._clarification_node)
        workflow.add_node("general_responder", self._general_responder_node)
        workflow.add_node("parallel_searcher", self._real_parallel_searcher)
        workflow.add_node("product_presenter", self._product_presenter_node)
        workflow.add_node("selection_handler", self._enhanced_selection_handler)
        workflow.add_node("checkout_handler", self._mock_checkout_handler)
        
        # CRITICAL FIX: Ensure state updates propagate properly
        workflow.add_edge(START, "intent_classifier")
        
        # Intent routing
        workflow.add_conditional_edges(
            "intent_classifier",
            self._route_after_intent_classification,
            {
                "greeter": "greeter",
                "needs_analyzer": "needs_analyzer",
                "selection_handler": "selection_handler", 
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
        
        # FIXED: Parallel searcher routing with proper state handling
        workflow.add_conditional_edges(
            "parallel_searcher",
            self._route_after_search,  # ← USE THIS INSTEAD
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
        
        # End states
        workflow.add_edge("product_presenter", END)
        workflow.add_edge("general_responder", END)
        workflow.add_edge("selection_handler", END)
        workflow.add_edge("checkout_handler", END)
        
        # Compile with memory
        self.graph = workflow.compile(checkpointer=self.memory)
        print("✅ Real scraping integration setup complete!")

            
  
    # ============ ENHANCED AGENT NODE WRAPPERS ============
    
    def _intent_classifier_node(self, state: OutfitterState) -> Dict[str, Any]:
        """Enhanced AI-powered intent classification node"""
        return self.intent_classifier.classify_intent(state)
    
    def _needs_analyzer_node(self, state: OutfitterState) -> Dict[str, Any]:
        """AI-powered needs analysis and extraction node"""
        return self.needs_analyzer.analyze_needs(state)

    
    def _greeter_node(self, state: OutfitterState) -> Dict[str, Any]:
        """Enhanced personalized greeting node"""
        return self.greeter.greet_user(state)
    

    
    # UPDATE THE CLARIFICATION NODE METHOD (replace existing _clarification_node method)
    def _clarification_node(self, state: OutfitterState) -> Dict[str, Any]:
        """Simple clarification question generator node"""  
        return self.clarification_asker.ask_clarification(state)
    
    def _general_responder_node(self, state: OutfitterState) -> Dict[str, Any]:
        """Enhanced AI-powered general response node"""
        return self.general_responder.respond_to_general_query(state)
    
    # ============ REAL SCRAPING INTEGRATION NODES ============
        
    # MAKE SURE your _real_parallel_searcher method returns this when products are found:

    def _real_parallel_searcher(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Real parallel searcher with client-side filtering and debug logging
        """
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
                max_products=30  # Get more since we'll filter
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
            
            # ============ CLIENT-SIDE FILTERING ============
            # Universal Store search doesn't work via URL, so filter client-side
            if len(product_dicts) > 0:
                from tools.simple_product_verifier import SimpleProductVerifier
                verifier = SimpleProductVerifier()
                
                # Build user request from criteria
                user_request = self._build_user_request_string(search_criteria, search_query)
                
                print(f"🔍 Applying AI filter for: '{user_request}'")
                original_count = len(product_dicts)
                
                # Filter to only relevant products
                product_dicts = verifier.filter_relevant_products(user_request, product_dicts)
                
                print(f"📊 Filtering result: {original_count} → {len(product_dicts)} products")
            # ============================================
            
            # ============ DEBUG: SAVE TO FILE ============
            import json
            from datetime import datetime
            
            debug_data = {
                "timestamp": datetime.now().isoformat(),
                "search_query": search_query,
                "search_criteria": search_criteria,
                "products_found_after_filtering": len(product_dicts),
                "products": product_dicts
            }
            
            # Save to debug file
            debug_filename = f"debug_scraped_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(debug_filename, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 DEBUG: Saved scraped products to {debug_filename}")
            # ============================================
            
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

    # Make sure you also have these helper methods:
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
    # Also add these SYNCHRONOUS helper methods:
    def _handle_no_products_found_sync(self, query: str, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Handle case where no products are found - SYNC version"""
        
        message = f"""I searched for '{query}' but couldn't find any products right now. This might be because:

    • The stores might be experiencing high traffic
    • Your specific criteria might be very specific  
    • There could be temporary connectivity issues

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
        """Handle scraping errors with user-friendly message - SYNC version"""
        
        print(f"Scraping error details: {error}")
        
        message = """I'm having trouble accessing the stores right now. This could be a temporary issue.

    Let me try to help you in other ways:
    • I can provide fashion advice and styling tips
    • We can refine what you're looking for and try again  
    • I can suggest general product categories to explore

    What would you prefer to do?"""

        return {
            "messages": [AIMessage(content=message)],
            "search_results": [],
            "search_query": query,
            "search_successful": False,
            "scraping_error": True,
            "conversation_stage": "general",
            "next_step": "general_responder"
        }
    
    def _product_presenter_node(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Present products with relevance verification AND store for Gradio access.
        """
        print("📱 Formatting products for presentation with AI verification...")
        
        search_results = state.get("search_results", [])
        search_criteria = state.get("search_criteria", {})
        search_query = state.get("search_query", "items")
        
        if not search_results:
            self.last_products = []  # Clear stored products
            return self._handle_empty_presentation(search_query)
        
        # BUILD USER REQUEST STRING
        user_request = self._build_user_request_string(search_criteria, search_query)
        
        # AI VERIFICATION - Simple and direct
        from tools.simple_product_verifier import SimpleProductVerifier  # Make sure this import works
        verifier = SimpleProductVerifier()
        relevant_products = verifier.filter_relevant_products(user_request, search_results)
        
        # CRITICAL: STORE PRODUCTS FOR GRADIO ACCESS
        self.last_products = relevant_products  # This is what Gradio will access
        print(f"🔗 Stored {len(relevant_products)} products for Gradio access")
        
        if not relevant_products:
            self.last_products = []  # Clear stored products
            
            message = f"""I found {len(search_results)} products but none actually matched your request for "{user_request}".

    The products were different categories or colors than what you asked for.

    Would you like me to:
    1. Show you similar items anyway?
    2. Try a different search?
    3. Help refine your request?"""

            return {
                "messages": [AIMessage(content=message)],
                "products_shown": [],
                "verification_failed": True,
                "conversation_stage": "discovery",
                "next_step": "clarification_asker"
            }
        
        # PRESENT ONLY RELEVANT PRODUCTS using existing logic
        products_by_store = {}
        for product in relevant_products:
            store_name = product.get("store_name", "Unknown Store")
            if store_name not in products_by_store:
                products_by_store[store_name] = []
            products_by_store[store_name].append(product)
        
        # Build the presentation message
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

    # ============ ENHANCED ROUTING LOGIC ============
    
    def _route_after_intent_classification(self, state: OutfitterState) -> str:
        """Route based on enhanced intent classification results"""
        next_step = state.get("next_step", "general_responder")
        
        # Map search intents to needs_analyzer instead of clarification_asker
        if next_step == "clarification_asker" and state.get("current_intent") == "search":
            return "needs_analyzer"
        
        # Handle special routing cases
        if state.get("needs_clarification", False):
            return "clarification_asker"
        
        if state.get("urgency_flag", False):
            return next_step
        
        return next_step

    def _route_after_greeting(self, state: OutfitterState) -> str:
        """Route after enhanced greeting based on user context"""
        next_step = state.get("next_step", "wait_for_user")
        
        # Enhanced greeter might fast-track urgent users
        if next_step == "needs_analyzer":
            return "needs_analyzer"
        
        return "wait_for_user"
    
    def _route_after_needs_analysis(self, state: OutfitterState) -> str:
        """Route after needs analysis based on sufficiency assessment"""
        return state.get("next_step", "clarification_asker")

    
    def _route_after_clarification(self, state: OutfitterState) -> str:
        """Route after clarification questioning - always wait for user"""
        # Clarification asker always waits for user input
        return "wait_for_user"
    
    def _route_after_search(self, state: OutfitterState) -> str:
        """
        UPDATED: Route after parallel search with enhanced debugging and multiple routing strategies.
        Handles LangGraph state propagation issues by checking multiple success indicators.
        """
        
        print(f"🔄 ROUTING AFTER SEARCH - ENHANCED DEBUG:")
        print(f"   📊 All state keys: {list(state.keys())}")
        
        # Extract all relevant state information
        search_results = state.get("search_results", [])
        search_successful = state.get("search_successful", False)
        next_step = state.get("next_step", None)
        conversation_stage = state.get("conversation_stage", "unknown")
        scraping_error = state.get("scraping_error", False)
        search_query = state.get("search_query", "unknown")
        
        print(f"   🔍 search_results count: {len(search_results)}")
        print(f"   ✅ search_successful flag: {search_successful}")
        print(f"   ➡️  next_step: {next_step}")
        print(f"   🎭 conversation_stage: {conversation_stage}")
        print(f"   ❌ scraping_error: {scraping_error}")
        print(f"   🔎 search_query: {search_query}")
        
        # STRATEGY 1: Route by explicit next_step (highest priority)
        if next_step == "product_presenter":
            print("✅ ROUTING STRATEGY 1: Using explicit next_step = product_presenter")
            return "product_presenter"
        
        # STRATEGY 2: Route by results count (most reliable indicator)
        if len(search_results) > 0:
            print(f"✅ ROUTING STRATEGY 2: Found {len(search_results)} products - routing to product_presenter")
            print(f"   📦 Sample product: {search_results[0].get('name', 'Unknown') if search_results else 'None'}")
            return "product_presenter"
        
        # STRATEGY 3: Route by success flag (if state propagated correctly)
        if search_successful:
            print("✅ ROUTING STRATEGY 3: search_successful=True - routing to product_presenter")
            return "product_presenter"
        
        # STRATEGY 4: Route by conversation stage
        if conversation_stage == "presenting":
            print("✅ ROUTING STRATEGY 4: conversation_stage=presenting - routing to product_presenter")
            return "product_presenter"
        
        # ERROR HANDLING: Route scraping errors to general responder
        if scraping_error:
            print("❌ ROUTING TO GENERAL_RESPONDER: scraping_error=True")
            return "general_responder"
        
        # DEFAULT: Route to clarification if no success indicators found
        print("🤔 ROUTING TO CLARIFICATION_ASKER: No success indicators detected")
        print("   💡 This suggests either:")
        print("      - No products were actually found")
        print("      - LangGraph state is not propagating correctly")
        print("      - There's an issue in _real_parallel_searcher return values")
        
        return "clarification_asker"


    def _build_search_query_from_criteria(self, criteria: Dict[str, Any]) -> str:
        """
        Build a search query string from extracted user criteria.
        Combines category, color, style preferences into searchable terms.
        """
        query_parts = []
        
        # Add color preference
        color = criteria.get("color_preference", "").strip()
        if color:
            query_parts.append(color)
        
        # Add category (most important)
        category = criteria.get("category", "").strip()
        if category:
            query_parts.append(category)
        else:
            # Default to common clothing types if no category specified
            query_parts.append("clothing")
        
        # Add style preference
        style = criteria.get("style_preference", "").strip()
        if style:
            query_parts.append(style)
        
        # Build final query
        if query_parts:
            return " ".join(query_parts)
        
        return "clothing"  # Safe fallback

    async def _handle_no_products_found(self, query: str, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Handle case where no products are found"""
        
        message = f"""I searched for '{query}' but couldn't find any products right now. This might be because:

• The stores might be experiencing high traffic
• Your specific criteria might be very specific
• There could be temporary connectivity issues

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

    async def _handle_scraping_error(self, query: str, error: str) -> Dict[str, Any]:
        """Handle scraping errors with user-friendly message"""
        
        print(f"Scraping error details: {error}")  # For debugging
        
        message = """I'm having trouble accessing the stores right now. This could be a temporary issue.

Let me try to help you in other ways:
• I can provide fashion advice and styling tips
• We can refine what you're looking for and try again
• I can suggest general product categories to explore

What would you prefer to do?"""

        return {
            "messages": [AIMessage(content=message)],
            "search_results": [],
            "search_query": query,
            "search_successful": False,
            "scraping_error": True,
            "conversation_stage": "general",
            "next_step": "general_responder"
        }
    
    def _build_product_presentation(self, products_by_store: Dict[str, List[Dict]], query: str) -> str:
        """Build formatted product presentation organized by store"""
        
        presentation_parts = []
        item_number = 1
        
        # Add header
        total_products = sum(len(products) for products in products_by_store.values())
        store_count = len(products_by_store)
        
        presentation_parts.append(f"🛍️ Found {total_products} great options from {store_count} stores for '{query}':")
        presentation_parts.append("")
        
        # Present products by store
        for store_name, products in products_by_store.items():
            if not products:
                continue
                
            presentation_parts.append(f"🏪 **{store_name}:**")
            
            for product in products[:5]:  # Limit to 5 per store for readability
                product_line = self._format_single_product(product, item_number)
                presentation_parts.append(product_line)
                item_number += 1
            
            presentation_parts.append("")  # Space between stores
        
        return "\n".join(presentation_parts)
    
    def _build_user_request_string(self, criteria: Dict[str, Any], query: str) -> str:
        """Build clear user request string for AI verification"""
        
        parts = []
        
        # Add color if specified
        color = criteria.get("color_preference", "")
        if color:
            parts.append(color)
        
        # Add category if specified  
        category = criteria.get("category", "")
        if category:
            parts.append(category)
        
        # Add size if specified
        size = criteria.get("size", "")
        if size:
            parts.append(f"size {size}")
        
        # Add style if specified
        style = criteria.get("style_preference", "")
        if style:
            parts.append(style)
        
        # If we have structured parts, use those
        if parts:
            return " ".join(parts)
        
        # Otherwise use the original query
        return query if query != "items" else "clothing"

    def _format_single_product(self, product: Dict[str, Any], item_number: int) -> str:
        """Format a single product for display"""
        
        name = product.get("name", "Unknown Product")
        price = product.get("price", "Price unavailable")
        is_on_sale = product.get("is_on_sale", False)
        url = product.get("url", "")
        
        # Build the product line
        sale_indicator = " 🔥" if is_on_sale else ""
        
        # Format with item number for easy selection
        product_line = f"{item_number}. **{name}**{sale_indicator}"
        product_line += f"\n   💰 {price}"
        
        if url:
            # Truncate long URLs for readability
            display_url = url
            product_line += f"\n   🔗 {display_url}"
        
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
    
    # ============ ENHANCED SELECTION HANDLER ============
    
    def _enhanced_selection_handler(self, state: OutfitterState) -> Dict[str, Any]:
        """Enhanced selection handler that works with real products"""
        products_shown = state.get("products_shown", [])
        
        if not products_shown:
            return {
                "messages": [AIMessage(content="I don't see any products that were shown to select from. Would you like me to search for something?")],
                "conversation_stage": "discovery",
                "next_step": "clarification_asker"
            }
        
        # Get user message for selection analysis
        messages = state.get("messages", [])
        user_input = ""
        for msg in reversed(messages):
            if hasattr(msg, 'content') and isinstance(msg.content, str) and not isinstance(msg, AIMessage):
                user_input = msg.content
                break
        
        response = f"""I can see you're interested in selecting from the {len(products_shown)} products I showed you.

Your selection: "{user_input}"

🔧 [SELECTION PROCESSING]
Enhanced selection handling with real products will be fully implemented in the next stage. For now, I can help you with:

• More details about specific products
• Different search queries  
• Styling advice and recommendations
• General shopping questions

What would you like to explore?"""
        
        return {
            "messages": [AIMessage(content=response)],
            "conversation_stage": "presenting",
            "next_step": "wait_for_user"
        }
    
    # ============ REMAINING MOCK NODES ============
    
   
    def _mock_checkout_handler(self, state: OutfitterState) -> Dict[str, Any]:
        """Mock checkout handler - will be implemented in Stage 4"""
        return {
            "messages": [AIMessage(content="🔧 [MOCK CHECKOUT] Checkout processing will be implemented in Stage 4 with cart management!")],
            "next_step": "wait_for_user"
        }
    
    # ============ MAIN INTERFACE ============
    
    async def run_conversation(self, message: str, history: List[Dict]) -> List[Dict]:
        """
        Run conversation with enhanced agents and real scraping integration.
        Handles the complete conversation flow with AI-powered responses and real products.
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
        
        # Build enhanced state with conversation context
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
            # Run the enhanced conversation graph with real scraping
            result = await self.graph.ainvoke(state, config=config)
            # In run_conversation method, after result = await self.graph.ainvoke(state, config=config)
            print(f"🔄 DEBUG: Graph execution result keys: {list(result.keys())}")
            print(f"🔄 DEBUG: Final state conversation_stage: {result.get('conversation_stage')}")
            print(f"🔄 DEBUG: Final state search_criteria: {result.get('search_criteria')}")
            print(f"🔄 DEBUG: Final state next_step: {result.get('next_step')}")
            print(f"✅ Real scraping integration graph execution completed")
            
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
            print(f"❌ Enhanced conversation error: {e}")
            import traceback
            traceback.print_exc()
            
            # Enhanced error handling
            user_msg = {"role": "user", "content": message}
            error_msg = {"role": "assistant", "content": "I apologize for the technical hiccup. I'm your fashion and shopping assistant - what can I help you find today?"}
            return history + [user_msg, error_msg]
    
    def cleanup(self):
        """Clean up enhanced conversation resources"""
        print("🧹 Cleaning up enhanced conversation resources...")


# ============ MAIN EXECUTION ============

def main():
    """Test the enhanced Outfitter.ai setup with real scraping"""
    print("🚀 Starting Enhanced Outfitter.ai with Real Scraping Integration...")
    
    assistant = OutfitterAssistant()
    assistant.setup_graph()
    
    print("\n✅ Real scraping integration setup complete!")
    print("🎯 Stage 2.3 Features:")
    print("   ✓ AI-powered intent classification with context awareness")
    print("   ✓ Personalized greetings that adapt to user type") 
    print("   ✓ Smart clarification questions (one at a time)")
    print("   ✓ Fashion expert general responses")
    print("   ✓ REAL Universal Store + CultureKings product search")
    print("   ✓ Professional product presentation with sale indicators")
    print("   ✓ Error handling for scraping failures")
    print("\n🛍️ Ready to provide real shopping assistance with live product data!")

if __name__ == "__main__":
    main()