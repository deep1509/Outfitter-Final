from typing import Dict, Any
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from agents.state import OutfitterState

class SimpleGeneralResponder:
    """
    Simple AI-powered general responder that handles fashion advice and general questions
    using GPT-4o's built-in knowledge. Clean, maintainable, and effective.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
    def respond_to_general_query(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Handle general questions using AI expertise. Covers fashion advice, styling,
        and general shopping assistance with natural conversation flow.
        """
        
        # Build context-aware system prompt
        system_prompt = """You are a knowledgeable fashion expert and shopping assistant for Outfitter.ai, specializing in CultureKings streetwear and menswear.

EXPERTISE:
- Fashion styling advice for any occasion (summer parties, work, dates, casual outings)
- Color coordination, fit advice, and outfit recommendations
- Current fashion trends and seasonal styling
- General shopping guidance and product advice
- CultureKings brand knowledge and streetwear expertise

APPROACH:
- Provide specific, actionable fashion advice
- Be conversational and helpful, not robotic
- Give practical styling tips with reasoning
- Suggest complete outfit ideas when relevant
- After fashion advice, offer to help find specific products
- Keep responses focused and useful

For store policies, shipping, or returns - acknowledge you can help but suggest checking the store directly for the most current information."""

        # Get user's question
        user_message = self._get_latest_user_message(state)
        
        # Add conversation context if relevant
        context_info = self._get_conversation_context(state)
        user_prompt = f"Customer question: {user_message}"
        
        if context_info:
            user_prompt += f"\n\nConversation context: {context_info}"
        
        try:
            # Generate response
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            return {
                "messages": [AIMessage(content=response.content.strip())],
                "conversation_stage": state.get("conversation_stage", "general"),
                "next_step": "wait_for_user"
            }
            
        except Exception as e:
            # Simple fallback
            return self._simple_fallback(state, str(e))
    
    def _get_latest_user_message(self, state: OutfitterState) -> str:
        """Extract the latest user message"""
        messages = state.get("messages", [])
        
        for msg in reversed(messages):
            if hasattr(msg, 'content') and isinstance(msg.content, str) and not isinstance(msg, AIMessage):
                return msg.content.strip()
        
        return "How can I help you today?"
    
    def _get_conversation_context(self, state: OutfitterState) -> str:
        """Get minimal context if user is mid-shopping"""
        search_criteria = state.get("search_criteria", {})
        products_shown = len(state.get("search_results", []))
        
        context = []
        
        if search_criteria:
            context.append(f"User is looking for: {search_criteria}")
        
        if products_shown > 0:
            context.append(f"User has been shown {products_shown} products")
        
        return ". ".join(context) if context else ""
    
    def _simple_fallback(self, state: OutfitterState, error: str) -> Dict[str, Any]:
        """Simple fallback response"""
        return {
            "messages": [AIMessage(content="I'm here to help with fashion advice and general shopping questions. What would you like to know?")],
            "conversation_stage": state.get("conversation_stage", "general"),
            "next_step": "wait_for_user"
        }