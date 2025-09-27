"""
AI-Powered Needs Analyzer for Outfitter.ai
Extracts user shopping criteria and determines if sufficient info exists to search.
Uses GPT-4o for intelligent extraction and decision making.
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from agents.state import OutfitterState
import json

class NeedsAnalyzer:
    """
    AI-powered needs analyzer that extracts shopping criteria from conversation
    and determines if we have enough information to proceed to product search.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.1)  # Low temp for consistent analysis
    
    def analyze_needs(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Main function: Analyze user needs and determine next step.
        
        Flow:
        1. Extract search criteria from conversation using AI
        2. Assess if criteria is sufficient for effective search
        3. Determine next routing step (search or clarification)
        4. Return state update with decision
        """
        print("🔍 NeedsAnalyzer: Starting needs analysis...")
        
        try:
            # Get conversation context
            conversation_text = self._extract_conversation_text(state)
            current_criteria = state.get("search_criteria", {})
            
            # Step 1: AI-powered extraction of search criteria
            extracted_criteria = self._extract_search_criteria(conversation_text, current_criteria)
            print(f"📋 Extracted criteria: {extracted_criteria}")
            
            # Step 2: AI-powered sufficiency assessment
            sufficiency_result = self._assess_sufficiency(extracted_criteria, conversation_text)
            print(f"🎯 Sufficiency assessment: {sufficiency_result['decision']} - {sufficiency_result['reasoning']}")
            
            # Step 3: Determine routing decision
            next_step = self._determine_next_step(sufficiency_result, extracted_criteria)
            
            # Step 4: Build state update
            return self._build_state_update(extracted_criteria, sufficiency_result, next_step)
            
        except Exception as e:
            print(f"❌ NeedsAnalyzer error: {e}")
            return self._fallback_analysis(state)
    
    def _extract_conversation_text(self, state: OutfitterState) -> str:
        """Extract recent conversation for AI analysis"""
        messages = state.get("messages", [])
        conversation_parts = []
        
        # Get last 6 messages for context
        recent_messages = messages[-6:] if len(messages) > 6 else messages
        
        for msg in recent_messages:
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                role = "User" if not isinstance(msg, AIMessage) else "Assistant"
                conversation_parts.append(f"{role}: {msg.content}")
        
        return "\n".join(conversation_parts)
    
    def _extract_search_criteria(self, conversation_text: str, current_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to extract shopping criteria from conversation.
        Handles complex language, multiple intents, and context.
        """
        system_prompt = """You are an expert at understanding customer shopping needs from conversation.

Extract shopping criteria from the conversation. Look for:

CLOTHING CATEGORIES:
- shirts, t-shirts, tees, tops, blouses → "shirts"
- hoodies, sweatshirts, jumpers, pullovers → "hoodies"  
- pants, trousers, jeans, chinos, slacks → "pants"
- shorts → "shorts"
- shoes, sneakers, boots, sandals, trainers → "shoes"
- jackets, coats, blazers, cardigans → "jackets"
- dresses, gowns → "dresses"
- accessories (hats, bags, watches) → "accessories"

OTHER CRITERIA:
- Colors: black, white, red, blue, green, etc.
- Sizes: XS, S, M, L, XL, XXL, or numeric sizes
- Budget: any mentioned price ranges or limits
- Style: casual, formal, streetwear, vintage, etc.
- Brand: Nike, Adidas, CultureKings, etc.

Return ONLY a JSON object with extracted criteria. Only include fields where you're confident.

EXAMPLES:
"show me red t-shirts" → {"category": "shirts", "color_preference": "red"}
"I need black hoodies under $50" → {"category": "hoodies", "color_preference": "black", "budget_max": 50}
"looking for size M casual shirts" → {"category": "shirts", "size": "M", "style_preference": "casual"}
"I want something nice" → {"intent": "shopping", "specificity": "vague"}"""

        user_prompt = f"""Current criteria from previous conversation: {current_criteria}

Recent conversation:
{conversation_text}

Extract shopping criteria as JSON:"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            # Parse JSON from response
            response_text = response.content.strip()
            
            # Find JSON in response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                extracted = json.loads(json_match.group())
                
                # Merge with current criteria (new info takes precedence)
                merged_criteria = current_criteria.copy()
                merged_criteria.update(extracted)
                
                return merged_criteria
            else:
                print("⚠️ No JSON found in AI response, using current criteria")
                return current_criteria
                
        except Exception as e:
            print(f"⚠️ Extraction error: {e}, using current criteria")
            return current_criteria
    
    def _assess_sufficiency(self, criteria: Dict[str, Any], conversation_text: str) -> Dict[str, Any]:
        """
        Use AI to assess if we have enough information for effective product search.
        """
        system_prompt = """You are an expert shopping assistant determining if you have enough information to search for products effectively.

SUFFICIENCY RULES:
- SUFFICIENT: If you have a clear product category (shirts, hoodies, pants, shoes, etc.) 
- SUFFICIENT: If you have specific product mentions ("red t-shirts", "black jeans", etc.)
- INSUFFICIENT: If request is too vague ("I need something", "show me clothes", "help me shop")
- INSUFFICIENT: If user asks questions without specifying products ("what do you have?", "what's popular?")

Consider the customer experience - it's better to search with partial info than over-question.

Return JSON with:
- "decision": "sufficient" or "insufficient"  
- "reasoning": brief explanation of why
- "confidence": 0.0-1.0 confidence score"""

        user_prompt = f"""Extracted criteria: {criteria}

Recent conversation: {conversation_text}

Can we search effectively with this information? Return JSON assessment:"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback decision
                has_category = criteria.get("category") is not None
                return {
                    "decision": "sufficient" if has_category else "insufficient",
                    "reasoning": "Fallback decision based on category presence",
                    "confidence": 0.7
                }
                
        except Exception as e:
            print(f"⚠️ Assessment error: {e}")
            # Safe fallback - proceed if we have any meaningful criteria
            has_info = any(key in criteria for key in ["category", "color_preference", "brand_preference"])
            return {
                "decision": "sufficient" if has_info else "insufficient", 
                "reasoning": f"Fallback assessment due to error: {e}",
                "confidence": 0.5
            }
    
    def _determine_next_step(self, sufficiency_result: Dict[str, Any], criteria: Dict[str, Any]) -> str:
        """Determine routing based on sufficiency assessment"""
        
        if sufficiency_result["decision"] == "sufficient":
            return "parallel_searcher"
        else:
            return "clarification_asker"
    
    def _build_state_update(self, criteria: Dict[str, Any], sufficiency_result: Dict[str, Any], next_step: str) -> Dict[str, Any]:
        """Build the state update for LangGraph"""
        
        if next_step == "parallel_searcher":
            # Ready to search
            return {
                "search_criteria": criteria,
                "needs_clarification": False,
                "conversation_stage": "searching",
                "next_step": next_step,
                "needs_analysis": {
                    "completed": True,
                    "sufficiency": sufficiency_result,
                    "extracted_criteria": criteria
                }
            }
        else:
            # Need clarification
            return {
                "search_criteria": criteria, 
                "needs_clarification": True,
                "conversation_stage": "discovery",
                "next_step": next_step,
                "needs_analysis": {
                    "completed": True,
                    "sufficiency": sufficiency_result,
                    "extracted_criteria": criteria,
                    "clarification_needed": True
                }
            }
    
    def _fallback_analysis(self, state: OutfitterState) -> Dict[str, Any]:
        """Emergency fallback when AI analysis fails completely"""
        print("🚨 Using fallback needs analysis")
        
        current_criteria = state.get("search_criteria", {})
        
        # Simple rule-based fallback
        if current_criteria.get("category"):
            # Have category - can search
            return {
                "search_criteria": current_criteria,
                "needs_clarification": False, 
                "conversation_stage": "searching",
                "next_step": "parallel_searcher",
                "fallback_used": True
            }
        else:
            # No category - need clarification
            return {
                "search_criteria": current_criteria,
                "needs_clarification": True,
                "conversation_stage": "discovery", 
                "next_step": "clarification_asker",
                "fallback_used": True
            }