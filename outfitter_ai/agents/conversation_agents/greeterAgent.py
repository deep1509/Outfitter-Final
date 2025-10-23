from typing import Dict, Any
from langchain_core.messages import AIMessage
from agents.state import OutfitterState
import random
from datetime import datetime

class GreeterAgent:
    """
    Simple, exciting, and personalized greeter that actually works!
    No complex AI - just smart, engaging responses that make users feel welcome.
    """
    
    def __init__(self):
        # Exciting greeting templates with personality
        self.greeting_templates = [
            "Hey there! 👋 Welcome to Outfitter.ai - your personal streetwear shopping assistant! I'm here to help you find the sickest pieces from top Australian stores. What's your vibe today?",
            
            "What's up! 🔥 Ready to discover some fire streetwear? I've got access to the latest drops from premium Australian retailers. Just tell me what you're looking for and I'll hook you up!",
            
            "Yo! 🛍️ Welcome to Outfitter.ai - where we find you the dopest fits! I can search through thousands of pieces from Australia's best stores. What's on your shopping list today?",
            
            "Hey! ✨ Welcome to your personal shopping experience! I'm here to help you find the perfect pieces from leading Australian fashion retailers. Whether you're looking for hoodies, tees, pants, or shoes - I've got you covered!",
            
            "What's good! 🎯 Ready to upgrade your wardrobe? I've got the inside track on all the latest streetwear from Australia's top fashion stores. What are you feeling today?"
        ]
        
        # Time-based greetings
        self.time_greetings = {
            "morning": "Good morning! ☀️",
            "afternoon": "Good afternoon! 🌤️", 
            "evening": "Good evening! 🌙",
            "night": "Hey night owl! 🦉"
        }
        
    def greet_user(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Generate an exciting, personalized greeting that gets users pumped to shop!
        """
        try:
            # Get current time for personalized greeting
            current_hour = datetime.now().hour
            time_of_day = self._get_time_of_day(current_hour)
            
            # Check if user has any previous context
            messages = state.get("messages", [])
            is_returning = len(messages) > 1
            
            # Generate personalized greeting
            greeting = self._generate_exciting_greeting(time_of_day, is_returning)
            
            return {
                "messages": [AIMessage(content=greeting)],
                "conversation_stage": "discovery",
                "user_profile": "new_shopper",
                "session_context": {
                    "greeting_time": time_of_day,
                    "is_returning": is_returning,
                    "session_start": datetime.now().isoformat()
                },
                "next_step": "wait_for_user"
            }
            
        except Exception as e:
            # Simple fallback that still works
            return self._simple_fallback_greeting()
    
    def _get_time_of_day(self, hour: int) -> str:
        """Get time-based greeting"""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def _generate_exciting_greeting(self, time_of_day: str, is_returning: bool) -> str:
        """Generate an exciting, personalized greeting"""
        
        # Time-based opening
        time_opening = self.time_greetings.get(time_of_day, "Hey! 👋")
        
        if is_returning:
            # Returning user - acknowledge them
            return f"{time_opening} Welcome back to Outfitter.ai! Ready to find some more fire pieces? 🔥 What's on your mind today?"
        else:
            # New user - exciting welcome
            base_greeting = random.choice(self.greeting_templates)
            return f"{time_opening} {base_greeting}"
    
    def _simple_fallback_greeting(self) -> Dict[str, Any]:
        """Simple fallback that always works"""
        return {
            "messages": [AIMessage(content="Hey! 👋 Welcome to Outfitter.ai! I'm your personal shopping assistant for Australia's best fashion retailers. What are you looking for today?")],
            "conversation_stage": "discovery",
            "user_profile": "new_shopper",
            "session_context": {
                "fallback_used": True,
                "session_start": datetime.now().isoformat()
            },
            "next_step": "wait_for_user"
        }