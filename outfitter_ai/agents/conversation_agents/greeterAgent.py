from typing import Dict, Any
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from agents.state import OutfitterState
import uuid
from datetime import datetime

class GreeterAgent:
    """
    AI-powered greeting agent that provides personalized, context-aware welcomes.
    Overcomes static template limitations with dynamic, intelligent responses that
    adapt to user context, conversation history, and apparent intent.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)  # Slight creativity for personalization
        
        # Quick user type detection patterns
        self.urgent_indicators = ["need now", "urgent", "quickly", "asap", "today"]
        self.returning_user_indicators = ["back", "again", "previous", "earlier"]
        self.browser_indicators = ["just looking", "browsing", "checking out"]
        
    def greet_user(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Generate personalized greeting based on user context and conversation state.
        
        OVERCOMES THESE LIMITATIONS:
        - Static one-size-fits-all greetings → Dynamic, context-aware responses
        - No returning user recognition → Detects and adapts to user history
        - Information overload → Tailored guidance based on user type
        - Generic tone → Personalized brand voice and appropriate formality
        - No user segmentation → Adapts to browsers, buyers, urgent users, etc.
        
        APPROACH:
        1. Extract conversation context (new vs returning, urgency, previous interactions)
        2. Classify user type (browser, urgent buyer, casual shopper)
        3. Use AI to generate appropriate personalized greeting
        4. Set conversation expectations and next steps appropriately
        5. Initialize session with proper context for downstream agents
        """
        
        try:
            # Extract rich context for personalization
            context = self._analyze_user_context(state)
            
            # Generate AI-powered personalized greeting
            greeting_response = self._generate_personalized_greeting(context, state)
            
            # Set up session context for other agents
            session_setup = self._initialize_session_context(context)
            
            return {
                "messages": [AIMessage(content=greeting_response)],
                "conversation_stage": "discovery",
                "user_profile": context["user_type"],
                "session_context": session_setup,
                "next_step": self._determine_optimal_next_step(context),
                "greeting_personalization": context  # For analytics
            }
            
        except Exception as e:
            # Fallback to intelligent default greeting
            return self._fallback_greeting(state, str(e))
    
    def _analyze_user_context(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Extract rich context about the user for personalization.
        Analyzes conversation history, timing, and behavioral indicators.
        """
        messages = state.get("messages", [])
        
        context = {
            "is_returning_user": False,
            "urgency_level": "normal",  # low, normal, high
            "user_type": "new_browser",  # new_browser, returning_user, urgent_buyer, casual_shopper
            "conversation_length": len(messages),
            "apparent_intent_strength": "medium",  # low, medium, high
            "formality_preference": "friendly",  # casual, friendly, professional
            "previous_session_data": state.get("session_context", {})
        }
        
        # Analyze latest user message for context clues
        if messages:
            latest_message = None
            for msg in reversed(messages):
                if hasattr(msg, 'content') and isinstance(msg.content, str):
                    latest_message = msg.content.lower()
                    break
            
            if latest_message:
                # Detect urgency
                if any(indicator in latest_message for indicator in self.urgent_indicators):
                    context["urgency_level"] = "high"
                    context["user_type"] = "urgent_buyer"
                
                # Detect returning user
                if any(indicator in latest_message for indicator in self.returning_user_indicators):
                    context["is_returning_user"] = True
                    context["user_type"] = "returning_user"
                
                # Detect browsing vs buying intent
                if any(indicator in latest_message for indicator in self.browser_indicators):
                    context["user_type"] = "casual_browser"
                    context["apparent_intent_strength"] = "low"
                elif any(word in latest_message for word in ["buy", "need", "purchase", "want"]):
                    context["apparent_intent_strength"] = "high"
                
                # Detect formality preference
                if any(word in latest_message for word in ["hi", "hey", "sup"]):
                    context["formality_preference"] = "casual"
                elif any(phrase in latest_message for phrase in ["good morning", "good afternoon", "hello"]):
                    context["formality_preference"] = "professional"
        
        return context
    
    def _generate_personalized_greeting(self, context: Dict[str, Any], state: OutfitterState) -> str:
        """
        Use AI to generate contextually appropriate greeting response.
        Adapts tone, length, and content based on user context analysis.
        """
        
        # Build context-aware system prompt
        system_prompt = f"""You are a professional yet friendly shopping assistant for Outfitter.ai, specializing in CultureKings streetwear and fashion.

CUSTOMER CONTEXT:
- User Type: {context['user_type']}
- Urgency: {context['urgency_level']} 
- Intent Strength: {context['apparent_intent_strength']}
- Returning User: {context['is_returning_user']}
- Preferred Tone: {context['formality_preference']}

GREETING GUIDELINES:
- Match the user's energy and formality level
- For urgent users: Be direct and action-oriented  
- For browsers: Be welcoming but not pushy
- For returning users: Acknowledge their return warmly
- Keep greetings concise but informative
- Always end with a clear, easy next step
- Use emojis sparingly and appropriately
- Maintain Outfitter.ai's helpful, knowledgeable brand voice

RESPONSE LENGTH:
- Urgent users: 1-2 sentences max
- Casual browsers: 2-3 sentences  
- New users: 2-4 sentences with brief guidance
- Returning users: 1-2 sentences acknowledging return

Generate a personalized greeting that matches this customer's context and gets them excited to shop."""

        # Create user-specific greeting prompt
        user_prompt = self._build_greeting_prompt(context, state)
        
        try:
            # Generate AI response
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            return response.content.strip()
            
        except Exception as e:
            # Fallback to template-based response
            return self._template_fallback_greeting(context)
    
    def _build_greeting_prompt(self, context: Dict[str, Any], state: OutfitterState) -> str:
        """Build specific prompt for greeting generation based on context"""
        
        if context["user_type"] == "urgent_buyer":
            return "Generate a direct, helpful greeting for someone who needs to find something quickly. Focus on efficiency and immediate assistance."
        
        elif context["user_type"] == "returning_user":
            return "Generate a warm welcome back message for a returning customer. Acknowledge their return and offer to help them continue where they left off."
        
        elif context["user_type"] == "casual_browser":
            return "Generate a welcoming but low-pressure greeting for someone who's just browsing. Make them feel comfortable to explore without obligation."
        
        else:  # new_browser
            return "Generate a friendly welcome for a new customer to Outfitter.ai. Briefly explain what you can help with and invite them to share what they're looking for."
    
    def _template_fallback_greeting(self, context: Dict[str, Any]) -> str:
        """
        Intelligent template fallback when AI generation fails.
        Still personalizes based on context but uses predefined responses.
        """
        
        if context["user_type"] == "urgent_buyer":
            return "Hi! I can help you find what you need quickly. What are you looking for today?"
        
        elif context["is_returning_user"]:
            return "Welcome back to Outfitter.ai! Ready to find some great pieces from CultureKings?"
        
        elif context["user_type"] == "casual_browser":
            return "Hey! Welcome to Outfitter.ai. Feel free to browse or let me know if you'd like help finding anything specific."
        
        else:
            return "Hello! I'm your personal shopping assistant for CultureKings. What brings you here today?"
    
    def _initialize_session_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set up session context for other agents to use.
        Provides downstream agents with user type and preference insights.
        """
        return {
            "user_type": context["user_type"],
            "urgency_level": context["urgency_level"],
            "formality_preference": context["formality_preference"],
            "intent_strength": context["apparent_intent_strength"],
            "session_start": datetime.now().isoformat(),
            "personalization_applied": True,
            "greeting_context": context
        }
    
    def _determine_optimal_next_step(self, context: Dict[str, Any]) -> str:
        """
        Determine the best next step based on user context.
        Optimizes conversation flow for different user types.
        """
        
        # Urgent users should skip to needs analysis immediately
        if context["urgency_level"] == "high":
            return "needs_analyzer"
        
        # High intent users can go straight to search
        elif context["apparent_intent_strength"] == "high":
            return "needs_analyzer"
        
        # Everyone else waits for user response
        else:
            return "wait_for_user"
    
    def _fallback_greeting(self, state: OutfitterState, error: str) -> Dict[str, Any]:
        """
        Emergency fallback when everything fails.
        Provides safe, generic but still helpful greeting.
        """
        print(f"GreeterAgent fallback triggered: {error}")
        
        return {
            "messages": [AIMessage(content="Hello! Welcome to Outfitter.ai. I'm here to help you find great clothing from CultureKings. What are you looking for today?")],
            "conversation_stage": "discovery",
            "user_profile": "unknown",
            "session_context": {
                "fallback_used": True,
                "error": error,
                "session_start": datetime.now().isoformat()
            },
            "next_step": "wait_for_user"
        }
        

