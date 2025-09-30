from typing import Dict, Any
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from agents.state import OutfitterState

class GreeterAgent:
    """
    Simplified AI-powered greeter using detailed prompting.
    Maintains human-like, personalized experience without extra state fields.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)  # Higher temp for natural variety
    
    def greet_user(self, state: OutfitterState) -> Dict[str, Any]:
        """Generate personalized greeting using AI with rich context"""
        
        try:
            # Analyze user context
            user_message = self._get_user_message(state)
            context = self._analyze_context(user_message, state)
            
            # Generate personalized greeting
            greeting = self._generate_greeting(user_message, context)
            
            # Determine next step
            next_step = self._determine_next_step(context)
            
            # Log context for debugging (not in state)
            print(f"👋 Greeter Context:")
            print(f"   User Type: {context['user_type']}")
            print(f"   Urgency: {context['urgency']}")
            print(f"   Formality: {context['formality']}")
            print(f"   Next: {next_step}")
            
            # Return ONLY valid state fields
            return {
                "messages": [AIMessage(content=greeting)],
                "conversation_stage": "discovery",
                "next_step": next_step
            }
            
        except Exception as e:
            print(f"⚠️ Greeter error: {e}")
            return self._simple_fallback()
    
    def _get_user_message(self, state: OutfitterState) -> str:
        """Extract latest user message"""
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if hasattr(msg, 'content') and not isinstance(msg, AIMessage):
                return msg.content.strip()
        return ""
    
    def _analyze_context(self, user_message: str, state: OutfitterState) -> Dict[str, Any]:
        """Analyze user context from message and state"""
        msg_lower = user_message.lower()
        
        # Detect user type
        if any(word in msg_lower for word in ["urgent", "quickly", "asap", "need now"]):
            user_type = "urgent_buyer"
            urgency = "high"
        elif any(word in msg_lower for word in ["back", "again", "previous"]):
            user_type = "returning_user"
            urgency = "normal"
        elif any(word in msg_lower for word in ["browsing", "just looking"]):
            user_type = "casual_browser"
            urgency = "low"
        else:
            user_type = "new_customer"
            urgency = "normal"
        
        # Detect formality
        if any(word in msg_lower for word in ["hi", "hey", "sup", "yo"]):
            formality = "casual"
        elif any(phrase in msg_lower for phrase in ["good morning", "good afternoon", "hello"]):
            formality = "professional"
        else:
            formality = "friendly"
        
        # Detect intent strength
        if any(word in msg_lower for word in ["buy", "need", "purchase", "want", "looking for"]):
            intent_strength = "high"
        else:
            intent_strength = "low"
        
        return {
            "user_type": user_type,
            "urgency": urgency,
            "formality": formality,
            "intent_strength": intent_strength,
            "message": user_message
        }
    
    def _generate_greeting(self, user_message: str, context: Dict[str, Any]) -> str:
        """Generate personalized greeting using detailed AI prompting"""
        
        system_prompt = """You are a professional shopping assistant for Outfitter.ai, specializing in CultureKings streetwear and Universal Store fashion.

YOUR PERSONALITY:
- Warm, helpful, and genuinely excited to assist
- Knowledgeable about fashion and trends
- Natural conversationalist, not robotic
- Adaptable to different customer types

YOUR TASK:
Generate a personalized welcome message that:
1. Matches the customer's communication style and energy
2. Makes them feel valued and understood
3. Sets clear expectations about what you can help with
4. Ends with a natural invitation to share what they need

CRITICAL RULES:
- Keep it conversational and authentic
- Match their formality level exactly
- For urgent customers: be direct and efficient (1 sentence)
- For browsers: be welcoming but not pushy (2-3 sentences)
- For returners: acknowledge their return warmly
- For new customers: brief intro + invitation (2-3 sentences)
- NO generic corporate speak
- NO emojis unless customer used them
- Sound like a helpful friend, not a sales bot"""

        user_prompt = f"""Customer said: "{user_message}"

Context:
- Customer Type: {context['user_type']}
- Urgency Level: {context['urgency']}
- Preferred Tone: {context['formality']}
- Shopping Intent: {context['intent_strength']}

Generate a personalized greeting that feels natural for THIS specific customer."""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            return response.content.strip()
            
        except Exception as e:
            print(f"⚠️ AI greeting failed: {e}")
            return self._fallback_greeting(context)
    
    def _fallback_greeting(self, context: Dict[str, Any]) -> str:
        """Smart fallback based on context"""
        templates = {
            "urgent_buyer": "Hi! I'll help you find what you need quickly. What are you looking for?",
            "returning_user": "Welcome back! Ready to find something great?",
            "casual_browser": "Hey! Feel free to browse, or let me know if you need help finding anything.",
            "new_customer": "Hello! I'm here to help you find the perfect clothing from CultureKings and Universal Store. What brings you here today?"
        }
        return templates.get(context['user_type'], templates['new_customer'])
    
    def _determine_next_step(self, context: Dict[str, Any]) -> str:
        """Determine routing based on context"""
        
        # Urgent or high intent → fast-track to needs analysis
        if context['urgency'] == "high" or context['intent_strength'] == "high":
            return "needs_analyzer"
        
        # Otherwise wait for user to respond
        return "END"
    
    def _simple_fallback(self) -> Dict[str, Any]:
        """Emergency fallback"""
        return {
            "messages": [AIMessage(content="Hello! I'm here to help you find great clothing. What are you looking for today?")],
            "conversation_stage": "discovery",
            "next_step": "END"
        }