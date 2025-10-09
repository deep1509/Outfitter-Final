"""
Simple AI-Powered Upsell Agent

Acts like a natural, helpful salesperson. No complex rules - just good prompting.
Suggests Universal Store items to complete the look, respects when user says no.
"""

from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.state import OutfitterState
from tools.database_manager import ProductDatabaseManager, ProductQuery


class UpsellAgent:
    """
    Natural AI salesperson that suggests complementary items from Universal Store.
    Keeps it conversational and respectful.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)  # Higher temp for personality
        self.db = ProductDatabaseManager()
    
    def suggest_upsell(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Main upsell function - creates conversational, personalized suggestions.
        """
        print("🎁 UpsellAgent: Creating personalized suggestions...")
        
        # Get what they selected
        selected_products = state.get("selected_products", [])
        
        if not selected_products:
            return self._skip_upsell()
        
        # CRITICAL FIX: Get the most recently added item, not the first item
        # Check if there are pending additions (most recent items)
        pending_additions = state.get("pending_cart_additions", [])
        if pending_additions:
            # Use the most recently added items for upsell suggestions
            recent_products = pending_additions
        else:
            # Fallback to the last item in the cart
            recent_products = selected_products[-1:] if selected_products else []
        
        if not recent_products:
            return self._skip_upsell()
        
        # Check if they already declined upsell
        if self._user_declined_upsell(state):
            return self._skip_upsell()
        
        # Check if we're in the middle of an upsell conversation
        upsell_stage = state.get("upsell_stage", "initial")
        
        # Check if user is responding to upsell question
        if self._is_responding_to_upsell(state):
            # User is responding to our upsell question
            if self._user_wants_upsell(state):
                # User said yes, show products
                return self._show_complementary_products(recent_products, state)
            else:
                # User said no, skip upsell
                return self._skip_upsell()
        elif upsell_stage == "initial":
            # Step 1: Ask if they want to complete the look
            return self._create_initial_upsell_question(recent_products, state)
        else:
            # Default: skip upsell
            return self._skip_upsell()
    
    def _get_universal_store_suggestions(self, selected_products: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Get smart complementary items from Universal Store based on what they selected.
        Uses product knowledge to suggest specific, appealing items.
        """
        
        # Analyze what they selected (most recent item)
        main_item = selected_products[0]
        item_name = main_item.get("name", "").lower()
        item_color = self._extract_color_from_name(item_name)
        
        suggestions = {}
        
        # Smart suggestions based on what they have
        if "hoodie" in item_name or "jacket" in item_name:
            # They have a top - suggest bottoms and shoes
            if not self._has_bottoms(selected_products):
                # Suggest jeans that complement the color
                jeans_color = self._get_complementary_jeans_color(item_color)
                suggestions["bottoms"] = self._get_specific_products("jeans", jeans_color, 2)
            
            if not self._has_shoes(selected_products):
                # Suggest sneakers that complement the color
                sneaker_color = self._get_complementary_sneaker_color(item_color)
                suggestions["shoes"] = self._get_specific_products("sneakers", sneaker_color, 2)
            
            # Always suggest accessories
            cap_color = self._get_complementary_cap_color(item_color)
            suggestions["accessories"] = self._get_specific_products("caps", cap_color, 1)
        
        elif "jean" in item_name or "pant" in item_name:
            # They have bottoms - suggest tops and shoes
            if not self._has_tops(selected_products):
                top_color = self._get_complementary_top_color(item_color)
                suggestions["tops"] = self._get_specific_products("hoodies", top_color, 2)
            
            if not self._has_shoes(selected_products):
                sneaker_color = self._get_complementary_sneaker_color(item_color)
                suggestions["shoes"] = self._get_specific_products("sneakers", sneaker_color, 2)
        
        return suggestions
    
    def _extract_color_from_name(self, name: str) -> str:
        """Extract color from product name"""
        colors = ["black", "white", "blue", "red", "green", "brown", "grey", "navy", "beige"]
        for color in colors:
            if color in name.lower():
                return color
        return "unknown"
    
    def _get_complementary_jeans_color(self, item_color: str) -> str:
        """Get complementary jeans color"""
        color_map = {
            "black": "black",
            "white": "black", 
            "blue": "black",
            "red": "black",
            "green": "black",
            "brown": "black",
            "grey": "black",
            "navy": "black",
            "beige": "black"
        }
        return color_map.get(item_color, "black")
    
    def _get_complementary_sneaker_color(self, item_color: str) -> str:
        """Get complementary sneaker color"""
        color_map = {
            "black": "white",
            "white": "black",
            "blue": "white", 
            "red": "white",
            "green": "white",
            "brown": "white",
            "grey": "white",
            "navy": "white",
            "beige": "white"
        }
        return color_map.get(item_color, "white")
    
    def _get_complementary_cap_color(self, item_color: str) -> str:
        """Get complementary cap color"""
        color_map = {
            "black": "black",
            "white": "brown",
            "blue": "black",
            "red": "black", 
            "green": "black",
            "brown": "brown",
            "grey": "black",
            "navy": "black",
            "beige": "brown"
        }
        return color_map.get(item_color, "black")
    
    def _get_complementary_top_color(self, item_color: str) -> str:
        """Get complementary top color"""
        color_map = {
            "black": "white",
            "white": "black",
            "blue": "white",
            "red": "white",
            "green": "white", 
            "brown": "white",
            "grey": "white",
            "navy": "white",
            "beige": "black"
        }
        return color_map.get(item_color, "white")
    
    def _get_specific_products(self, category: str, color: str, limit: int) -> List[Dict]:
        """Get specific products by category and color"""
        try:
            if category == "jeans":
                return self.db.get_products(ProductQuery(
                    category="bottoms",
                    store="universalstore",
                    limit=limit
                ))
            elif category == "sneakers":
                return self.db.get_products(ProductQuery(
                    category="shoes", 
                    store="universalstore",
                    limit=limit
                ))
            elif category == "caps":
                return self.db.get_products(ProductQuery(
                    category="accessories",
                    store="universalstore", 
                    limit=limit
                ))
            elif category == "hoodies":
                return self.db.get_products(ProductQuery(
                    category="outerwear",
                    store="universalstore",
                    limit=limit
                ))
        except Exception as e:
            print(f"Error getting products: {e}")
            return []
    
    def _has_tops(self, products: List[Dict]) -> bool:
        """Check if they have tops"""
        return any("hoodie" in p.get("name", "").lower() or "shirt" in p.get("name", "").lower() for p in products)
    
    def _has_bottoms(self, products: List[Dict]) -> bool:
        """Check if they have bottoms"""
        return any("jean" in p.get("name", "").lower() or "pant" in p.get("name", "").lower() for p in products)
    
    def _has_shoes(self, products: List[Dict]) -> bool:
        """Check if they have shoes"""
        return any("shoe" in p.get("name", "").lower() or "sneaker" in p.get("name", "").lower() for p in products)
    
    def _is_responding_to_upsell(self, state: OutfitterState) -> bool:
        """Check if user is responding to an upsell question."""
        conversation_stage = state.get("conversation_stage", "")
        upsell_stage = state.get("upsell_stage", "")
        
        # If we're in upselling stage, user is likely responding
        return conversation_stage == "upselling" and upsell_stage == "initial"
    
    def _user_wants_upsell(self, state: OutfitterState) -> bool:
        """Check if user wants to see complementary products."""
        messages = state.get("messages", [])
        if not messages:
            return False
        
        # Get the latest user message
        user_message = ""
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'human':
                user_message = msg.content.lower()
                break
            elif isinstance(msg, dict) and msg.get('role') == 'user':
                user_message = msg.get('content', '').lower()
                break
        
        if not user_message:
            return False
        
        # Check for positive responses
        positive_indicators = [
            "yes", "yeah", "sure", "ok", "okay", "show me", "let's see", 
            "interested", "sounds good", "why not", "sure thing"
        ]
        
        negative_indicators = [
            "no", "nope", "not interested", "pass", "skip", "maybe later",
            "not now", "no thanks", "don't need"
        ]
        
        # Check for negative first
        if any(neg in user_message for neg in negative_indicators):
            return False
        
        # Check for positive
        if any(pos in user_message for pos in positive_indicators):
            return True
        
        # Default to positive if unclear
        return True
    
    def _create_initial_upsell_question(self, recent_products: List[Dict], state: OutfitterState) -> str:
        """
        Step 1: Ask a personalized question about completing the look.
        """
        # Get the main item they selected (most recent)
        main_item = recent_products[0]
        item_name = main_item.get('name', 'item')
        item_color = self._extract_color_from_name(item_name)
        
        # Create specific, appealing suggestions based on what they have
        suggestions = self._get_smart_suggestions(recent_products)
        
        # Create a personalized, conversational question
        system_prompt = """You are a friendly, helpful salesperson at a streetwear store.
        
Your customer just added an item to their cart. You want to help them complete their look.

GUIDELINES:
- Be enthusiastic but not pushy
- Reference their specific item
- Suggest specific complementary items (e.g., "blue jeans", "white sneakers")
- Keep it conversational (2-3 sentences max)
- End with a question
- Be specific about what you can show them

EXAMPLES:
- "That black Jordan hoodie is 🔥! Want me to show you some blue jeans that would look amazing with it?"
- "Great choice on the hoodie! I have some perfect white sneakers that would complete this look - interested?"
- "That's a solid pick! Want to see how it would look with some matching pieces?"

Be natural and helpful, not salesy."""

        user_prompt = f"""Customer just added: {item_name}
Available suggestions: {suggestions}
        
Create a natural, conversational question asking if they want to complete their look with specific items."""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            return {
                "messages": [AIMessage(content=response.content)],
                "conversation_stage": "upselling",
                "upsell_stage": "initial",
                "showed_upsell": True,
                "next_step": "wait_for_user"
            }
        except Exception as e:
            print(f"Error creating upsell question: {e}")
            return self._skip_upsell()
    
    def _get_smart_suggestions(self, recent_products: List[Dict]) -> str:
        """Get smart suggestions based on what they selected"""
        main_item = recent_products[0]
        item_name = main_item.get("name", "").lower()
        item_color = self._extract_color_from_name(item_name)
        
        suggestions = []
        
        if "hoodie" in item_name or "jacket" in item_name:
            # They have a top - suggest bottoms and shoes
            if not self._has_bottoms(recent_products):
                jeans_color = self._get_complementary_jeans_color(item_color)
                suggestions.append(f"{jeans_color} jeans")
            
            if not self._has_shoes(recent_products):
                sneaker_color = self._get_complementary_sneaker_color(item_color)
                suggestions.append(f"{sneaker_color} sneakers")
            
            # Always suggest accessories
            cap_color = self._get_complementary_cap_color(item_color)
            suggestions.append(f"{cap_color} caps")
        
        return ", ".join(suggestions) if suggestions else "complementary pieces"
    
    def _show_complementary_products(self, recent_products: List[Dict], state: OutfitterState) -> str:
        """
        Step 2: Route to needs_analyzer for real-time scraping of complementary products.
        """
        # Get the main item for context (most recent)
        main_item = recent_products[0]
        item_name = main_item.get('name', 'item')
        item_color = self._extract_color_from_name(item_name)
        
        # Create specific search criteria based on what they have
        search_criteria = self._build_upsell_search_criteria(recent_products)
        
        print(f"🎁 UpsellAgent: Routing to needs_analyzer for real-time scraping")
        print(f"   Search criteria: {search_criteria}")
        
        # Create a message explaining what we're doing
        message = f"Perfect! Let me search for some {search_criteria.get('category', 'complementary items')} that would look amazing with your {item_name}..."
        
        return {
            "messages": [AIMessage(content=message)],
            "search_criteria": search_criteria,
            "conversation_stage": "discovery",
            "next_step": "needs_analyzer",  # Route to needs_analyzer for real-time scraping
            "upsell_search": True  # Mark this as an upsell search
        }
    
    def _build_upsell_search_criteria(self, recent_products: List[Dict]) -> Dict[str, Any]:
        """Build search criteria for upsell products"""
        main_item = recent_products[0]
        item_name = main_item.get("name", "").lower()
        item_color = self._extract_color_from_name(item_name)
        
        criteria = {}
        
        if "hoodie" in item_name or "jacket" in item_name:
            # They have a top - suggest bottoms and shoes
            if not self._has_bottoms(recent_products):
                jeans_color = self._get_complementary_jeans_color(item_color)
                criteria = {
                    "category": "jeans",
                    "color_preference": jeans_color,
                    "size": "M",  # Default size
                    "style_preference": "casual"
                }
            elif not self._has_shoes(recent_products):
                sneaker_color = self._get_complementary_sneaker_color(item_color)
                criteria = {
                    "category": "sneakers", 
                    "color_preference": sneaker_color,
                    "size": "M",  # Default size
                    "style_preference": "casual"
                }
            else:
                # Suggest accessories
                cap_color = self._get_complementary_cap_color(item_color)
                criteria = {
                    "category": "caps",
                    "color_preference": cap_color,
                    "style_preference": "casual"
                }
        
        elif "jean" in item_name or "pant" in item_name:
            # They have bottoms - suggest tops
            if not self._has_tops(recent_products):
                top_color = self._get_complementary_top_color(item_color)
                criteria = {
                    "category": "hoodies",
                    "color_preference": top_color,
                    "size": "M",  # Default size
                    "style_preference": "casual"
                }
        
        return criteria
    
    def _create_natural_upsell(self, selected_products: List[Dict], 
                              suggestions: Dict[str, List[Dict]],
                              state: OutfitterState) -> str:
        """
        Let AI create a natural, conversational upsell like a real salesperson.
        """
        
        # Build context about what they selected
        cart_summary = "\n".join([
            f"- {p.get('name', 'Item')} ({p.get('price', 'N/A')})"
            for p in selected_products
        ])
        
        # Build available suggestions
        suggestions_text = ""
        for category, items in suggestions.items():
            suggestions_text += f"\n{category.upper()}:\n"
            for i, item in enumerate(items, 1):
                suggestions_text += f"{i}. {item.get('name')} - {item.get('price')}"
                if item.get('is_on_sale'):
                    suggestions_text += " (ON SALE!)"
                suggestions_text += f"\n   Store: Universal Store\n"
        
        system_prompt = """You are a friendly, helpful salesperson at a streetwear store. 

Your job is to naturally suggest items from Universal Store to complete the customer's look.

GUIDELINES:
- Be conversational and enthusiastic (use emojis sparingly)
- Explain WHY items would complete their look
- Keep it brief (3-4 sentences max)
- Suggest 2-3 items MAX from what's available
- Make it feel helpful, not pushy
- End with an open question like "Want to add any of these?" or "What do you think?"
- If they have tops, suggest bottoms and shoes
- If they have bottoms, suggest tops and shoes
- Always keep it natural like a real conversation

RESPECT BOUNDARIES:
- This is just a suggestion
- They can say no and that's totally fine
- Don't be pushy or use high-pressure sales tactics

TONE: Helpful friend who knows fashion, not aggressive salesperson."""

        user_prompt = f"""Customer's current cart:
{cart_summary}

Available items from Universal Store to suggest:
{suggestions_text}

Create a natural, friendly suggestion to complete their look. Keep it conversational!"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            return response.content
            
        except Exception as e:
            print(f"   Error: {e}")
            # Simple fallback
            return "Want to complete the look? I have some great items from Universal Store that would match!"
    
    def _user_declined_upsell(self, state: OutfitterState) -> bool:
        """
        Simple check: did user say no to previous upsell?
        """
        messages = state.get("messages", [])
        showed_upsell = state.get("showed_upsell", False)
        
        if not showed_upsell:
            return False
        
        # Check last user message for decline signals
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'human':
                content = msg.content.lower()
                decline_words = ["no thanks", "no thank", "not interested", "nah", "skip", 
                               "just checkout", "no need", "that's all", "i'm good"]
                
                if any(word in content for word in decline_words):
                    print("   User declined upsell - respecting their decision")
                    return True
                break
        
        return False
    
    def _skip_upsell(self) -> Dict[str, Any]:
        """
        Skip upsell - go straight to next step.
        """
        return {
            "messages": [],  # No message
            "skip_upsell": True,
            "next_step": "wait_for_user"
        }


# Simple node wrapper for LangGraph
def create_upsell_node(state: OutfitterState) -> Dict[str, Any]:
    """Node wrapper for LangGraph integration"""
    agent = UpsellAgent()
    return agent.suggest_upsell(state)