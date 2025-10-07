"""
Routing Examples and General Responder Updates for Stage 3
Shows what routes where and how to update general_responder
"""

from typing import Dict, Any
from agents.state import OutfitterState
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

# ============================================================================
# ROUTING EXAMPLES - What Goes Where
# ============================================================================

"""
SCENARIO: Products are shown, user can either ask questions OR select

USER INPUT → ROUTES TO
---------------------------------------------------------------------------
"I want #2"                          → selection_handler
"add 1 and 3"                        → selection_handler  
"I'll take the first one"            → selection_handler
"2"                                  → selection_handler
"option 2 and 5"                     → selection_handler

"how do I style this?"               → general_responder
"what would match with this?"        → general_responder
"tell me about streetwear"           → general_responder
"which one should I get?"            → general_responder
"can you help me decide?"            → general_responder
"show me more options"               → general_responder (then can trigger new search)
"""

# ============================================================================
# UPDATE GENERAL RESPONDER TO PRESERVE PRODUCT STATE
# ============================================================================

def _general_responder_node(self, state: OutfitterState) -> Dict[str, Any]:
    """
    Enhanced general responder that maintains product context.
    UPDATED for Stage 3.
    """
    print("💬 GeneralResponder: Handling general query...")
    
    result = self.general_responder.respond_to_general_query(state)
    
    # CRITICAL: Preserve products_shown and awaiting_selection
    # So user can still select after asking questions
    products_shown = state.get("products_shown", [])
    awaiting_selection = state.get("awaiting_selection", False)
    
    if products_shown and awaiting_selection:
        print(f"   Preserving {len(products_shown)} shown products for selection")
        result["products_shown"] = products_shown
        result["awaiting_selection"] = True
        result["conversation_stage"] = "presenting"  # Stay in presenting mode
    
    return result


# ============================================================================
# ENHANCED GENERAL RESPONDER SYSTEM PROMPT
# ============================================================================

"""
Update the system prompt in SimpleGeneralResponder to be context-aware:

ORIGINAL PROMPT:
"You are a fashion expert..."

UPDATED PROMPT FOR STAGE 3:
"You are a fashion expert and shopping assistant.

CONTEXT AWARENESS:
- If products are currently shown to the user, reference them naturally
- Help users make decisions about the products they're viewing
- Answer styling questions about specific products when relevant
- Remind users they can select products by number when ready

EXAMPLES:
User: "how do I style this?"
Response: "Great question! The products I'm showing you can be styled in many ways. 
The black hoodie (#1) pairs perfectly with jeans for a casual look, while the red one (#2)
makes a bold statement. What's your usual style?"

User: "which one should I get?"
Response: "It depends on your needs! If you want versatility, go with #1 (the black hoodie).
If you want to stand out, #2 (the red Nike hoodie) is eye-catching. What occasions 
will you wear it for?"
"
"""

# ============================================================================
# COMPLETE UPDATED GENERAL RESPONDER CLASS
# ============================================================================

class SimpleGeneralResponder:
    """
    Enhanced general responder with product context awareness.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    def respond_to_general_query(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Respond to general queries with product context awareness.
        """
        messages = state.get("messages", [])
        products_shown = state.get("products_shown", [])
        
        # Get user's question
        user_query = ""
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'human':
                user_query = msg.content
                break
            elif isinstance(msg, dict) and msg.get('role') == 'user':
                user_query = msg.get('content', '')
                break
        
        # Build context-aware system prompt
        if products_shown:
            product_context = f"\n\nCURRENT CONTEXT: You are currently showing {len(products_shown)} products to the user:\n"
            for i, product in enumerate(products_shown[:5], 1):
                product_context += f"{i}. {product.get('name', 'Unknown')} - {product.get('price', 'N/A')}\n"
            
            product_context += "\nReference these products naturally when answering. Remind user they can select by number when ready."
        else:
            product_context = ""
        
        system_prompt = f"""You are a knowledgeable fashion expert and shopping assistant at Outfitter.ai.

Your expertise includes:
- Streetwear fashion trends and styling
- Color coordination and outfit matching
- Seasonal fashion advice
- Brand knowledge (especially Australian streetwear)
- Helping customers make confident purchase decisions

CONVERSATION STYLE:
- Friendly, enthusiastic, but not pushy
- Give specific, actionable advice
- Reference products by number when relevant (e.g., "#1 would look great with...")
- Ask follow-up questions to understand their style better{product_context}

Respond naturally and helpfully to their question."""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_query)
            ])
            
            response_text = response.content
            
            return {
                "messages": [AIMessage(content=response_text)],
                "conversation_stage": "presenting" if products_shown else "general",
                "next_step": "wait_for_user"
            }
            
        except Exception as e:
            print(f"   Error: {e}")
            return {
                "messages": [AIMessage(content="I'd be happy to help with that! What would you like to know?")],
                "conversation_stage": "general",
                "next_step": "wait_for_user"
            }


# ============================================================================
# TESTING EXAMPLES
# ============================================================================

"""
TEST FLOW:

1. User: "show me black hoodies"
   → System shows 5 products

2. User: "how do I style these?"
   → Routes to general_responder
   → Response references products: "The hoodie in #1 pairs well with..."
   → products_shown preserved, still awaiting_selection=True

3. User: "I'll take #2"
   → Routes to selection_handler
   → Adds product #2 to cart

4. User: "what goes with this?"
   → Routes to general_responder (question about selected item)
   → Gives styling advice

5. User: "add #4 too"
   → Routes to selection_handler
   → Adds product #4 to cart
"""