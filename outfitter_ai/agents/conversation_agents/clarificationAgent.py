from typing import Dict, Any, List
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from agents.state import OutfitterState
import uuid
from datetime import datetime

class ClarificationAgent:
    """
    Intelligent clarification agent that asks focused, contextual questions one at a time.
    Uses AI to understand what's missing and prioritize questions for optimal customer experience.
    Builds understanding progressively like an experienced salesperson would.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)  # Low temp for consistent questioning
        
        # Information priority for effective product search
        self.question_priority = {
            "category": 10,     # Most critical - what type of item
            "size": 8,          # Very important for filtering
            "color": 6,         # Helpful for personalization
            "budget": 7,        # Important for relevant results
            "style": 5,         # Nice to have
            "brand": 4,         # Lowest priority
            "occasion": 6       # Context-dependent importance
        }
        
        # Question fatigue indicators
        self.impatience_indicators = ["just", "any", "whatever", "anything", "don't care", "quick"]
        
    def ask_clarification(self, state: OutfitterState) -> Dict[str, Any]:
        print(f"🔍 DEBUG: ClarificationAgent received state:")
        print(f"  - search_criteria: {state.get('search_criteria', {})}")
        """
        Intelligently ask ONE focused clarification question based on context analysis.
        
        OVERCOMES THESE LIMITATIONS:
        - Question dumping → Single, prioritized question
        - Context blindness → Builds on what user already provided
        - Static approach → Adapts to user type and communication style
        - No flow intelligence → Knows when to stop and proceed to search
        - Poor user experience → Conversational, helpful questioning
        
        APPROACH:
        1. Analyze conversation context and extract known information
        2. Identify critical missing information gaps
        3. Prioritize next question by business impact and user receptiveness
        4. Generate contextual, conversational question using AI
        5. Determine if sufficient information gathered to proceed to search
        6. Update state with new information and next steps
        """
        
        try:
            # Extract and analyze current conversation context
            context_analysis = self._analyze_conversation_context(state)
            print(f"  - latest_user_input: '{context_analysis['latest_user_input']}'")
  
            
            # Determine if we have enough information to proceed
            sufficiency_check = self._assess_information_sufficiency(context_analysis)
            
            if sufficiency_check["sufficient"]:
                # We have enough info - proceed to search
                return self._transition_to_search(state, context_analysis, sufficiency_check["reason"])
            
            # Generate next strategic question
            next_question = self._generate_strategic_question(context_analysis, state)
            
            # Update search criteria with any new extracted information
            updated_criteria = self._extract_and_update_criteria(context_analysis, state)
            print(f"  - updated_criteria after extraction: {updated_criteria}")
            print(f"  - missing_critical_info: {context_analysis['missing_critical_info']}")
   
            
            return {
                "messages": [AIMessage(content=next_question)],
                "search_criteria": updated_criteria,
                "needs_clarification": True,
                "conversation_stage": "discovery",
                "clarification_context": {
                    "question_asked": next_question,
                    "missing_info": context_analysis["missing_critical_info"],
                    "user_patience_level": context_analysis["user_patience"],
                    "questions_asked_count": context_analysis["questions_asked"] + 1
                },
                "next_step": "wait_for_user"
            }
            
        except Exception as e:
            # Fallback to basic clarification
            return self._fallback_clarification(state, str(e))
    
    def _analyze_conversation_context(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Deep analysis of conversation to understand what's known vs. missing.
        Analyzes user communication patterns, patience level, and information gaps.
        """
        messages = state.get("messages", [])
        search_criteria = state.get("search_criteria", {})
        session_context = state.get("session_context", {})
        
        # Extract user messages for analysis
        user_messages = []
        for msg in messages:
            if hasattr(msg, 'content') and isinstance(msg.content, str) and not isinstance(msg, AIMessage):
                user_messages.append(msg.content.lower())
        
        latest_message = user_messages[-1] if user_messages else ""
        
        analysis = {
            "known_info": search_criteria,
            "missing_critical_info": [],
            "user_communication_style": "normal",  # brief, normal, detailed
            "user_patience": "normal",  # low, normal, high
            "apparent_urgency": session_context.get("urgency_level", "normal"),
            "questions_asked": self._count_previous_questions(messages),
            "latest_user_input": latest_message,
            "user_provided_new_info": False,
            "conversation_turn": len(user_messages)
        }
        
        # Analyze user communication style
        if latest_message:
            word_count = len(latest_message.split())
            if word_count <= 3:
                analysis["user_communication_style"] = "brief"
            elif word_count >= 15:
                analysis["user_communication_style"] = "detailed"
            
            # Detect impatience indicators
            if any(indicator in latest_message for indicator in self.impatience_indicators):
                analysis["user_patience"] = "low"
        
        # Identify missing critical information
        analysis["missing_critical_info"] = self._identify_missing_info(search_criteria)
        
        # Check if user provided new information in latest message
        analysis["user_provided_new_info"] = self._extract_new_info_from_message(latest_message, search_criteria)
        
        return analysis
    
    def _identify_missing_info(self, search_criteria: Dict[str, Any]) -> List[str]:
        """Identify what critical information is missing for effective product search"""
        missing = []
        
        # Check each critical piece of information
        if not search_criteria.get("category"):
            missing.append("category")
        
        if not search_criteria.get("size") and search_criteria.get("category") in ["shirts", "pants", "shoes", "jackets"]:
            missing.append("size")
        
        if not search_criteria.get("color_preference"):
            missing.append("color")
        
        if not search_criteria.get("budget_max"):
            missing.append("budget")
        
        return missing
    
    def _assess_information_sufficiency(self, context_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine if we have enough information to proceed to product search.
        Considers user patience, information quality, and business requirements.
        """
        missing_info = context_analysis["missing_critical_info"]
        user_patience = context_analysis["user_patience"]
        questions_asked = context_analysis["questions_asked"]
        
        # Always need category to search effectively
        if "category" in missing_info:
            return {"sufficient": False, "reason": "Category required for effective search"}
        
        # If user is impatient and we have category, proceed with partial info
        if user_patience == "low" and questions_asked >= 1:
            return {"sufficient": True, "reason": "User showing impatience - proceeding with available info"}
        
        # If we have category and size, that's usually sufficient
        if "category" not in missing_info and "size" not in missing_info:
            return {"sufficient": True, "reason": "Have category and size - sufficient for good results"}
        
        # If we've asked 3+ questions, stop regardless
        if questions_asked >= 3:
            return {"sufficient": True, "reason": "Maximum questions reached - proceeding to avoid fatigue"}
        
        # Need more information
        return {"sufficient": False, "reason": "Need more details for best results"}
    
    def _generate_strategic_question(self, context_analysis: Dict[str, Any], state: OutfitterState) -> str:
        """
        Generate the next most valuable question using AI, considering user context and patience.
        """
        # Determine highest priority missing information
        missing_info = context_analysis["missing_critical_info"]
        if not missing_info:
            return "What else can I help you find today?"
        
        # Sort by priority score
        next_info_needed = max(missing_info, key=lambda x: self.question_priority.get(x, 0))
        
        # Build context-aware system prompt
        system_prompt = f"""You are a skilled sales associate helping a customer find clothing from CultureKings.

CUSTOMER CONTEXT:
- Communication Style: {context_analysis['user_communication_style']}
- Patience Level: {context_analysis['user_patience']}
- Questions Already Asked: {context_analysis['questions_asked']}
- Urgency: {context_analysis['apparent_urgency']}

KNOWN INFORMATION: {context_analysis['known_info']}
NEED TO ASK ABOUT: {next_info_needed}

QUESTION GUIDELINES:
- Ask ONE specific question only
- Match the customer's communication style (brief for brief users, detailed for detailed users)  
- Be conversational and helpful, not interrogative
- For impatient users: Keep questions short and offer examples/options
- For detailed users: Provide more context and explanation
- Make the question feel natural and purposeful

Generate a focused question about {next_info_needed} that fits this customer's style."""

        user_prompt = self._build_question_prompt(next_info_needed, context_analysis)
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            return response.content.strip()
            
        except Exception as e:
            # Fallback to template questions
            return self._template_question_fallback(next_info_needed, context_analysis)
    
    def _build_question_prompt(self, info_needed: str, context: Dict[str, Any]) -> str:
        """Build specific prompt for the information we need to gather"""
        
        prompts = {
            "category": f"Ask what type of clothing they're looking for. Known info: {context['known_info']}",
            
            "size": f"Ask about their size preference. They're looking for {context['known_info'].get('category', 'clothing')}.",
            
            "color": f"Ask about color preferences for their {context['known_info'].get('category', 'item')}. Be helpful but not pushy.",
            
            "budget": f"Ask tactfully about their budget range. Make it feel helpful, not intrusive.",
            
            "style": f"Ask about the style they're going for (casual, formal, trendy, etc.) for their {context['known_info'].get('category', 'clothing')}.",
        }
        
        return prompts.get(info_needed, f"Ask about {info_needed} preferences.")
    
    def _template_question_fallback(self, info_needed: str, context: Dict[str, Any]) -> str:
        """Fallback template questions when AI generation fails"""
        
        user_style = context["user_communication_style"]
        
        if info_needed == "category":
            if user_style == "brief":
                return "What type of clothing are you looking for?"
            else:
                return "What type of clothing are you looking for today? Shirts, pants, shoes, or something else?"
        
        elif info_needed == "size":
            category = context["known_info"].get("category", "item")
            return f"What size {category} do you usually wear?"
        
        elif info_needed == "color":
            if user_style == "brief":
                return "Any color preferences?"
            else:
                return "Do you have any particular colors in mind, or are you open to different options?"
        
        elif info_needed == "budget":
            return "What's your budget range for this?"
        
        else:
            return "Can you tell me a bit more about what you're looking for?"
    
    def _extract_and_update_criteria(self, context_analysis: Dict[str, Any], state: OutfitterState) -> Dict[str, Any]:
        """
        Extract any new information from the user's latest message and update search criteria.
        Uses AI to parse natural language responses into structured data.
        """
        current_criteria = state.get("search_criteria", {}).copy()
        latest_message = context_analysis["latest_user_input"]
        
        if not latest_message or not context_analysis["user_provided_new_info"]:
            return current_criteria
        
        # Use AI to extract structured information from natural language
        extraction_prompt = f"""Extract shopping preferences from this customer message: "{latest_message}"

Return a JSON object with any of these fields you can identify:
- category: type of clothing (shirts, pants, shoes, etc.)
- size: clothing size (XS, S, M, L, XL, etc.)
- color_preference: preferred colors
- budget_max: maximum budget (extract numbers)
- style_preference: style description (casual, formal, trendy, etc.)
- brand_preference: any brands mentioned

Only include fields where you're confident about the information. Return empty object if no clear preferences found."""

        try:
            response = self.llm.invoke([HumanMessage(content=extraction_prompt)])
            
            # Parse AI response (simplified - in production would use structured output)
            import json
            import re
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                extracted_info = json.loads(json_match.group())
                
                # Merge extracted info with current criteria
                for key, value in extracted_info.items():
                    if value and key in ["category", "size", "color_preference", "budget_max", "style_preference", "brand_preference"]:
                        current_criteria[key] = value
            
        except Exception as e:
            # Fallback to simple keyword extraction
            current_criteria.update(self._simple_keyword_extraction(latest_message))
        
        return current_criteria
    # Replace the _simple_keyword_extraction method in your ClarificationAgent with this:

    def _simple_keyword_extraction(self, message: str) -> Dict[str, Any]:
        """Enhanced fallback extraction using keyword matching - now includes categories!"""
        extracted = {}
        message_lower = message.lower()
        
        # CATEGORY extraction (THIS WAS MISSING!)
        category_keywords = {
            "shirts": ["shirt", "tshirt", "t-shirt", "tee", "top", "blouse"],
            "hoodies": ["hoodie", "sweatshirt", "jumper", "pullover"], 
            "pants": ["pants", "trousers", "jeans", "chinos", "slacks"],
            "shorts": ["shorts", "short"],
            "shoes": ["shoes", "sneakers", "boots", "sandals", "trainers"],
            "jackets": ["jacket", "coat", "blazer", "cardigan"],
            "dresses": ["dress", "gown"],
            "accessories": ["hat", "cap", "belt", "bag", "watch", "sunglasses"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                extracted["category"] = category
                break
        
        # Size extraction
        sizes = ["xs", "s", "m", "l", "xl", "xxl", "small", "medium", "large"]
        for size in sizes:
            if f" {size} " in message_lower or message_lower.endswith(size):
                extracted["size"] = size.upper() if len(size) <= 3 else size.title()
                break
        
        # Color extraction  
        colors = ["black", "white", "red", "blue", "green", "navy", "grey", "brown", "gray", "yellow", "pink", "purple"]
        for color in colors:
            if color in message_lower:
                extracted["color_preference"] = color
                break
        
        # Budget extraction
        budget_match = re.search(r'\$(\d+)', message)
        if budget_match:
            extracted["budget_max"] = float(budget_match.group(1))
        
        return extracted

    def _count_previous_questions(self, messages: List) -> int:
        """Count how many clarification questions we've already asked"""
        question_count = 0
        for msg in messages:
            if isinstance(msg, AIMessage) and msg.content.endswith("?"):
                question_count += 1
        return question_count
    
    def _extract_new_info_from_message(self, message: str, current_criteria: Dict) -> bool:
        """Check if user's message contains new information we don't already have"""
        if not message:
            return False
        
        # Simple check for new information patterns
        info_indicators = ["size", "color", "budget", "$", "large", "small", "medium", "black", "white", "blue"]
        return any(indicator in message.lower() for indicator in info_indicators)
    
    def _transition_to_search(self, state: OutfitterState, context_analysis: Dict, reason: str) -> Dict[str, Any]:
        """
        Transition from clarification to product search with encouraging message.
        """
        search_criteria = state.get("search_criteria", {})
        
        # Generate encouraging transition message
        transition_message = self._generate_transition_message(search_criteria, reason)
        
        return {
            "messages": [AIMessage(content=transition_message)],
            "search_criteria": search_criteria,
            "needs_clarification": False,
            "conversation_stage": "searching",
            "next_step": "parallel_searcher",
            "clarification_completed": True,
            "transition_reason": reason
        }
    
    def _generate_transition_message(self, criteria: Dict[str, Any], reason: str) -> str:
        """Generate encouraging message when transitioning to search"""
        category = criteria.get("category", "items")
        
        messages = [
            f"Perfect! Let me find some great {category} options for you.",
            f"Got it! Searching for {category} that match what you're looking for.",
            f"Excellent! I'll show you some {category} that should be perfect."
        ]
        
        import random
        return random.choice(messages)
    
    def _fallback_clarification(self, state: OutfitterState, error: str) -> Dict[str, Any]:
        """Emergency fallback when AI clarification fails"""
        print(f"ClarificationAgent fallback triggered: {error}")
        
        # Simple fallback question based on what's missing
        search_criteria = state.get("search_criteria", {})
        
        if not search_criteria.get("category"):
            question = "What type of clothing are you looking for today?"
        elif not search_criteria.get("size"):
            question = "What size do you need?"
        else:
            question = "What else can you tell me about what you're looking for?"
        
        return {
            "messages": [AIMessage(content=question)],
            "search_criteria": search_criteria,
            "needs_clarification": True,
            "conversation_stage": "discovery",
            "next_step": "wait_for_user",
            "fallback_used": True,
            "error": error
        }