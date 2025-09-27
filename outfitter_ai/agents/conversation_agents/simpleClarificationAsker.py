"""
Simple Clarification Asker - Pure Question Generation
Only asks focused questions based on missing information.
Works with NeedsAnalyzer output.
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from agents.state import OutfitterState

class SimpleClarificationAsker:
    """
    Pure clarification question generator.
    Takes missing info from NeedsAnalyzer and asks focused questions.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    
    def ask_clarification(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Generate a focused clarification question based on what's missing.
        Simple responsibility: Ask one good question, return to user.
        """
        print("❓ ClarificationAsker: Generating clarification question...")
        
        try:
            # Get context from needs analysis
            search_criteria = state.get("search_criteria", {})
            needs_analysis = state.get("needs_analysis", {})
            
            # Generate appropriate question using AI
            question = self._generate_contextual_question(search_criteria, state)
            
            return {
                "messages": [AIMessage(content=question)],
                "search_criteria": search_criteria,  # Keep existing criteria
                "needs_clarification": True,
                "conversation_stage": "discovery",
                "next_step": "wait_for_user"  # Always wait for user after asking
            }
            
        except Exception as e:
            print(f"❌ ClarificationAsker error: {e}")
            return self._fallback_question(state)
    
    def _generate_contextual_question(self, criteria: Dict[str, Any], state: OutfitterState) -> str:
        """Generate contextual clarification question using AI"""
        
        # Get conversation context
        messages = state.get("messages", [])
        latest_user_message = ""
        for msg in reversed(messages):
            if hasattr(msg, 'content') and isinstance(msg.content, str) and not isinstance(msg, AIMessage):
                latest_user_message = msg.content
                break
        
        system_prompt = """You are a helpful shopping assistant asking clarification questions.

Generate ONE focused, conversational question to help understand what the customer is looking for.

QUESTION GUIDELINES:
- Ask about the most important missing information first
- Be natural and conversational, not robotic
- Provide examples when helpful
- Keep questions short and focused
- Match the customer's communication style

PRIORITY ORDER:
1. Product category (if missing) - "What type of clothing are you looking for?"
2. Specific details (if category exists) - size, color, style preferences  
3. Context/occasion - "What's this for?" or "Any particular style in mind?"

Examples:
- Missing everything: "What type of clothing are you looking for today?"
- Have category, missing details: "Any particular size or color you prefer for the [category]?"
- Very specific: "I can help you find that! Any size preference?"
"""

        user_prompt = f"""Customer's latest message: "{latest_user_message}"
Current criteria we have: {criteria}

Generate a helpful clarification question:"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            return response.content.strip()
            
        except Exception as e:
            print(f"⚠️ Question generation error: {e}")
            return self._template_fallback_question(criteria)
    
    def _template_fallback_question(self, criteria: Dict[str, Any]) -> str:
        """Simple template-based fallback questions"""
        
        if not criteria.get("category"):
            return "What type of clothing are you looking for today?"
        
        elif criteria.get("category") and not criteria.get("color_preference"):
            category = criteria["category"]
            return f"Any particular colors you prefer for {category}?"
        
        elif criteria.get("category") and not criteria.get("size"):
            category = criteria["category"]
            return f"What size {category} do you usually wear?"
        
        else:
            return "Can you tell me a bit more about what you're looking for?"
    
    def _fallback_question(self, state: OutfitterState) -> Dict[str, Any]:
        """Emergency fallback question"""
        return {
            "messages": [AIMessage(content="What type of clothing are you looking for today?")],
            "search_criteria": state.get("search_criteria", {}),
            "needs_clarification": True,
            "conversation_stage": "discovery",
            "next_step": "wait_for_user",
            "fallback_used": True
        }