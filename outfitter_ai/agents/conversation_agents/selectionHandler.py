"""
Intelligent Selection Handler for Outfitter.ai
Parses user product selections and extracts variant preferences.
Uses AI to understand natural language selections like "I like #2 in black" or "show me the first hoodie".
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from agents.state import OutfitterState
from pydantic import BaseModel, Field
import re

class SelectionResult(BaseModel):
    """Structured selection result"""
    selected_indices: List[int] = Field(description="Indices of selected products (0-based)")
    variant_preferences: Dict[str, Any] = Field(default={}, description="Size, color preferences")
    selection_intent: str = Field(description="buy, compare, more_info, save_for_later")
    confidence: float = Field(description="Confidence in selection parsing 0.0-1.0")
    reasoning: str = Field(description="Why this selection was interpreted this way")

class SelectionHandler:
    """
    AI-powered selection handler that understands natural language product selections.
    
    Handles patterns like:
    - "I like #2" → selects product at index 1
    - "Show me 1 and 3" → selects products at indices 0 and 2
    - "The black hoodie" → finds hoodie by color
    - "First one in size M" → selects with size preference
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    
    def handle_selection(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Main selection handling function.
        
        Flow:
        1. Extract user's selection message
        2. Get products that were shown to user
        3. Use AI to parse selection intent
        4. Validate selections
        5. Return selected products with preferences
        """
        print("🎯 SelectionHandler: Processing user selection...")
        
        try:
            # Get context
            products_shown = state.get("products_shown", [])
            user_message = self._get_latest_user_message(state)
            
            if not products_shown:
                return self._handle_no_products_shown()
            
            if not user_message:
                return self._handle_empty_selection()
            
            # Parse selection using AI
            selection_result = self._parse_selection_with_ai(user_message, products_shown)
            
            print(f"📊 Parsed selection: {len(selection_result.selected_indices)} products")
            print(f"   Intent: {selection_result.selection_intent}")
            print(f"   Preferences: {selection_result.variant_preferences}")
            
            # Validate and extract selected products
            selected_products = self._extract_selected_products(
                selection_result.selected_indices, 
                products_shown
            )
            
            if not selected_products:
                return self._handle_invalid_selection(user_message)
            
            # Build response based on intent
            response = self._build_selection_response(
                selected_products, 
                selection_result
            )
            
            return {
                "messages": [AIMessage(content=response)],
                "selected_products": selected_products,
                "variant_preferences": selection_result.variant_preferences,
                "selection_intent": selection_result.selection_intent,
                "conversation_stage": "selection_confirmed",
                "next_step": self._determine_next_step(selection_result.selection_intent)
            }
            
        except Exception as e:
            print(f"❌ SelectionHandler error: {e}")
            return self._fallback_selection_handler(state)
    
    def _get_latest_user_message(self, state: OutfitterState) -> Optional[str]:
        """Extract latest user message"""
        messages = state.get("messages", [])
        
        for msg in reversed(messages):
            if hasattr(msg, 'content') and isinstance(msg.content, str) and not isinstance(msg, AIMessage):
                return msg.content.strip()
        
        return None
    
    def _parse_selection_with_ai(self, user_message: str, products: List[Dict]) -> SelectionResult:
        """
        Use AI to parse natural language selection into structured format.
        """
        
        # Build product reference list
        product_list = []
        for i, product in enumerate(products[:20]):  # Limit to first 20 for context
            name = product.get("name", "Unknown")
            price = product.get("price", "N/A")
            product_list.append(f"{i+1}. {name} - {price}")
        
        system_prompt = """You are a product selection parser for a shopping assistant.

Your job: Parse the user's selection message and identify which products they selected.

SELECTION PATTERNS TO RECOGNIZE:
- Numbers: "I like #2", "2 and 5", "number 3", "the first one"
- Descriptions: "the black hoodie", "show me the Nike shoes"
- Positions: "the first one", "last item", "second product"
- Multiple: "1, 3, and 5", "the first and third items"

VARIANT PREFERENCES:
- Size: "in size M", "large", "size 10"
- Color: "in black", "the red one", "blue version"

INTENT CLASSIFICATION:
- buy: "I'll take", "add to cart", "I want to buy"
- compare: "compare these", "tell me more about", "what's the difference"
- more_info: "show me details", "more info on", "tell me about"
- save_for_later: "save this", "bookmark", "remember this"

Return the product indices (1-based converted to 0-based), variant preferences, and intent.

IMPORTANT: Product indices in the list are 1-based (1, 2, 3...) but you must return 0-based indices (0, 1, 2...)."""

        user_prompt = f"""User message: "{user_message}"

Products shown to user:
{chr(10).join(product_list)}

Parse this selection and return structured data."""

        from langchain_core.output_parsers import PydanticOutputParser
        parser = PydanticOutputParser(pydantic_object=SelectionResult)
        
        full_prompt = f"""{user_prompt}

{parser.get_format_instructions()}"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=full_prompt)
            ])
            
            return parser.parse(response.content)
            
        except Exception as e:
            print(f"⚠️ AI selection parsing failed: {e}")
            # Fallback to regex parsing
            return self._regex_fallback_parsing(user_message, products)
    
    def _regex_fallback_parsing(self, user_message: str, products: List[Dict]) -> SelectionResult:
        """Fallback selection parsing using regex patterns"""
        
        selected_indices = []
        
        # Pattern 1: "#2", "number 3", etc.
        number_pattern = r'#?(\d+)|number\s+(\d+)'
        matches = re.findall(number_pattern, user_message.lower())
        
        for match in matches:
            num = int(match[0] or match[1])
            if 1 <= num <= len(products):
                selected_indices.append(num - 1)  # Convert to 0-based
        
        # Pattern 2: "first", "second", etc.
        position_words = {
            'first': 0, 'second': 1, 'third': 2, 'fourth': 3, 'fifth': 4,
            'last': len(products) - 1
        }
        
        for word, idx in position_words.items():
            if word in user_message.lower() and idx < len(products):
                selected_indices.append(idx)
        
        # Extract variant preferences
        variant_preferences = {}
        
        # Size extraction
        size_pattern = r'\b(size\s+)?([XS|S|M|L|XL|XXL]+|[2-9][0-9]?)\b'
        size_match = re.search(size_pattern, user_message, re.IGNORECASE)
        if size_match:
            variant_preferences["size"] = size_match.group(2).upper()
        
        # Color extraction
        colors = ["black", "white", "red", "blue", "green", "grey", "gray", "navy", "brown"]
        for color in colors:
            if color in user_message.lower():
                variant_preferences["color"] = color
                break
        
        # Determine intent
        intent = "more_info"  # Default
        if any(word in user_message.lower() for word in ["buy", "purchase", "take", "cart", "checkout"]):
            intent = "buy"
        elif any(word in user_message.lower() for word in ["compare", "difference", "versus"]):
            intent = "compare"
        
        return SelectionResult(
            selected_indices=selected_indices or [0],  # Default to first if none found
            variant_preferences=variant_preferences,
            selection_intent=intent,
            confidence=0.6,  # Lower confidence for regex fallback
            reasoning="Regex fallback parsing used"
        )
    
    def _extract_selected_products(self, indices: List[int], products: List[Dict]) -> List[Dict]:
        """Extract products by indices with validation"""
        selected = []
        
        for idx in indices:
            if 0 <= idx < len(products):
                selected.append(products[idx])
            else:
                print(f"⚠️ Invalid index {idx} (products count: {len(products)})")
        
        return selected
    
    def _build_selection_response(self, selected_products: List[Dict], 
                                   selection_result: SelectionResult) -> str:
        """Build response message based on selection"""
        
        if len(selected_products) == 1:
            product = selected_products[0]
            name = product.get("name", "item")
            price = product.get("price", "N/A")
            store = product.get("store_name", "store")
            
            response = f"Great choice! You've selected:\n\n"
            response += f"**{name}**\n"
            response += f"💰 {price}\n"
            response += f"🏪 {store}\n"
            
            # Add variant info if preferences specified
            if selection_result.variant_preferences:
                response += f"\n📋 Your preferences: {selection_result.variant_preferences}\n"
            
            # Next steps based on intent
            if selection_result.selection_intent == "buy":
                response += "\n✅ Ready to add this to your cart?"
            elif selection_result.selection_intent == "more_info":
                response += "\n💡 Would you like more details about this item, or ready to add it to your cart?"
            
        else:
            response = f"You've selected {len(selected_products)} items:\n\n"
            
            for i, product in enumerate(selected_products[:5], 1):
                name = product.get("name", "item")
                price = product.get("price", "N/A")
                response += f"{i}. **{name}** - {price}\n"
            
            if selection_result.selection_intent == "buy":
                response += "\n✅ Ready to add these to your cart?"
            elif selection_result.selection_intent == "compare":
                response += "\n🔍 Would you like me to compare these items for you?"
        
        return response
    
    def _determine_next_step(self, intent: str) -> str:
        """Determine next node based on selection intent"""
        intent_routing = {
            "buy": "wait_for_user",  # Stage 2 will add "cart_manager"
            "compare": "general_responder",  # Use general responder for comparison
            "more_info": "general_responder",
            "save_for_later": "wait_for_user"
        }
        
        return intent_routing.get(intent, "wait_for_user")
    
    def _handle_no_products_shown(self) -> Dict[str, Any]:
        """Handle case where no products were shown"""
        return {
            "messages": [AIMessage(content="I don't see any products that were shown for you to select from. Would you like me to search for something?")],
            "conversation_stage": "discovery",
            "next_step": "clarification_asker"
        }
    
    def _handle_empty_selection(self) -> Dict[str, Any]:
        """Handle empty selection message"""
        return {
            "messages": [AIMessage(content="I didn't catch which product you're interested in. Could you tell me the number or describe the item?")],
            "conversation_stage": "presenting",
            "next_step": "wait_for_user"
        }
    
    def _handle_invalid_selection(self, user_message: str) -> Dict[str, Any]:
        """Handle invalid selection"""
        return {
            "messages": [AIMessage(content=f"I couldn't identify which product you meant from '{user_message}'. Could you specify the product number (like #2) or describe it?")],
            "conversation_stage": "presenting",
            "next_step": "wait_for_user"
        }
    
    def _fallback_selection_handler(self, state: OutfitterState) -> Dict[str, Any]:
        """Emergency fallback"""
        return {
            "messages": [AIMessage(content="I'm having trouble processing your selection. Could you try telling me the product number?")],
            "conversation_stage": "presenting",
            "next_step": "wait_for_user"
        }