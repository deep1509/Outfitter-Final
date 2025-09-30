"""
Simple Clarification Asker - Gets Category + Gender + Size
Asks focused questions to gather the 3 essential pieces of information.
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from agents.state import OutfitterState

class SimpleClarificationAsker:
    """
    Clarification question generator focused on getting:
    1. Category (what type of clothing)
    2. Gender (mens or womens)
    3. Size (what size they wear)
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        
        # Categories that need size
        self.SIZED_CATEGORIES = [
            "shirts", "pants", "hoodies", "jackets", 
            "shoes", "shorts", "dresses", "sweaters"
        ]
    
    def ask_clarification(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Generate focused question for missing information.
        Priority: Category → Gender → Size
        """
        print("❓ ClarificationAsker: Generating clarification question...")
        
        try:
            # Get current criteria
            search_criteria = state.get("search_criteria", {})
            
            # Determine what's missing and what to ask about
            missing_info = self._identify_missing_info(search_criteria)
            
            print(f"   Missing: {missing_info}")
            
            # Generate appropriate question
            question = self._generate_targeted_question(missing_info, search_criteria, state)
            
            return {
                "messages": [AIMessage(content=question)],
                "search_criteria": search_criteria,
                "needs_clarification": True,
                "conversation_stage": "discovery",
                "next_step": "End"
            }
            
        except Exception as e:
            print(f"❌ ClarificationAsker error: {e}")
            return self._fallback_question(state)
    
    def _identify_missing_info(self, criteria: Dict[str, Any]) -> str:
        """
        Identify what's missing in priority order.
        Returns: "category", "gender", or "size"
        """
        category = criteria.get("category")
        gender = criteria.get("gender")
        size = criteria.get("size")
        
        # Priority 1: Category (most important)
        if not category:
            return "category"
        
        # Priority 2: Gender (critical for correct department)
        if not gender:
            return "gender"
        
        # Priority 3: Size (for sized items)
        if category in self.SIZED_CATEGORIES and not size:
            return "size"
        
        # If we have everything, shouldn't be here
        return "complete"
    
    def _generate_targeted_question(self, missing_info: str, criteria: Dict[str, Any], state: OutfitterState) -> str:
        """
        Generate specific question for the missing information.
        Uses AI for natural phrasing.
        """
        
        # Get user's latest message for context
        latest_user_message = self._get_latest_user_message(state)
        
        # Build targeted prompt based on what's missing
        if missing_info == "category":
            context = "The user hasn't specified what type of clothing they want."
            ask_for = "what type of clothing they're looking for (shirts, hoodies, pants, shoes, etc.)"
            
        elif missing_info == "gender":
            category = criteria.get("category", "clothing")
            context = f"The user wants {category}, but we need to know if they want mens or womens."
            ask_for = f"whether they're looking for mens or womens {category}"
            
        elif missing_info == "size":
            category = criteria.get("category", "clothing")
            gender = criteria.get("gender", "")
            context = f"The user wants {gender} {category}, but we need their size."
            ask_for = f"what size {category} they wear"
            
        else:
            # Shouldn't happen, but fallback
            return "What else can I help you find?"
        
        system_prompt = f"""You are a helpful shopping assistant asking a clarification question.

CONTEXT: {context}
TASK: Ask the user {ask_for}

GUIDELINES:
- Be conversational and natural
- Keep it short (1-2 sentences max)
- Match the user's casual/formal tone
- Provide examples if helpful

EXAMPLES:
Category question: "What type of clothing are you looking for today? (hoodies, shirts, pants, shoes, etc.)"
Gender question: "Are you looking for mens or womens hoodies?"
Size question: "What size do you usually wear in shirts?"

Generate a natural question:"""

        user_prompt = f"""User's latest message: "{latest_user_message}"
Current criteria: {criteria}

Ask for {missing_info}:"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            return response.content.strip()
            
        except Exception as e:
            print(f"⚠️ AI question generation error: {e}")
            return self._template_question_for_missing(missing_info, criteria)
    
    def _template_question_for_missing(self, missing_info: str, criteria: Dict[str, Any]) -> str:
        """Template-based questions when AI fails"""
        
        if missing_info == "category":
            return "What type of clothing are you looking for today? (hoodies, shirts, pants, shoes, etc.)"
        
        elif missing_info == "gender":
            category = criteria.get("category", "clothing")
            return f"Are you looking for mens or womens {category}?"
        
        elif missing_info == "size":
            category = criteria.get("category", "clothing")
            return f"What size {category} do you usually wear?"
        
        else:
            return "What can I help you find today?"
    
    def _get_latest_user_message(self, state: OutfitterState) -> str:
        """Extract latest user message for context"""
        messages = state.get("messages", [])
        
        for msg in reversed(messages):
            if hasattr(msg, 'content') and isinstance(msg.content, str) and not isinstance(msg, AIMessage):
                return msg.content
        
        return ""
    
    def _fallback_question(self, state: OutfitterState) -> Dict[str, Any]:
        """Emergency fallback when everything fails"""
        return {
            "messages": [AIMessage(content="What type of clothing are you looking for today?")],
            "search_criteria": state.get("search_criteria", {}),
            "needs_clarification": True,
            "conversation_stage": "discovery",
            "next_step": "End",
            "fallback_used": True
        }