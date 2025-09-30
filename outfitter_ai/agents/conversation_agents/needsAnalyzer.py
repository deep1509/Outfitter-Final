"""
AI-Powered Needs Analyzer for Outfitter.ai
Extracts user shopping criteria and determines if sufficient info exists to search.
REQUIRES: Category + Size + Gender for effective search.
"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from agents.state import OutfitterState
import json
import re

class NeedsAnalyzer:
    """
    AI-powered needs analyzer that extracts shopping criteria and decides next step.
    Uses GPT-4o to understand natural language and make intelligent routing decisions.
    
    MANDATORY REQUIREMENTS:
    1. Category (hoodies, shirts, pants, etc.)
    2. Size (M, L, 10, etc.) - for sized items
    3. Gender (mens, womens, unisex)
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        
        # Categories that require size
        self.SIZED_CATEGORIES = [
            "shirts", "pants", "hoodies", "jackets", 
            "shoes", "shorts", "dresses", "sweaters"
        ]
    
    def analyze_needs(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Analyze user needs and determine if we can search or need clarification.
        REQUIRES: Category + Size (for clothing) + Gender
        """
        print("🔍 NeedsAnalyzer: Starting analysis...")
        
        try:
            # Get conversation context
            conversation_text = self._extract_conversation_text(state)
            current_criteria = state.get("search_criteria", {})
            
            # Use AI to extract AND assess in one call
            analysis = self._ai_extract_and_assess(conversation_text, current_criteria)
            
            # Validate AI decision with hard rules (backup safety check)
            validated_analysis = self._validate_and_enhance(analysis)
            
            # Log results
            print(f"📋 Extracted: {validated_analysis['criteria']}")
            print(f"🎯 Decision: {validated_analysis['decision']} - {validated_analysis['reasoning']}")
            
            # Return valid state update
            return self._build_state_update(validated_analysis)
            
        except Exception as e:
            print(f"❌ NeedsAnalyzer error: {e}")
            return self._fallback_analysis(state)
    
    def _extract_conversation_text(self, state: OutfitterState) -> str:
        """Extract recent conversation messages"""
        messages = state.get("messages", [])
        conversation_parts = []
        
        # Get last 6 messages for context
        recent_messages = messages[-6:] if len(messages) > 6 else messages
        
        from langchain_core.messages import AIMessage
        for msg in recent_messages:
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                role = "User" if not isinstance(msg, AIMessage) else "Assistant"
                conversation_parts.append(f"{role}: {msg.content}")
        
        return "\n".join(conversation_parts)
    
    def _ai_extract_and_assess(self, conversation_text: str, current_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to extract criteria AND assess sufficiency in one call.
        REQUIRES: Category + Size + Gender for sufficiency.
        """
        system_prompt = """You are an expert shopping assistant analyzing customer needs.

Your job: Extract shopping criteria AND decide if you have enough info to search.

MANDATORY INFORMATION (Need ALL 3 for clothing):
1. **Category** - What type of clothing
2. **Size** - What size they wear (for clothing items)
3. **Gender** - Mens or womens department

CLOTHING CATEGORIES:
- shirts, t-shirts, tees, tops → "shirts"
- hoodies, sweatshirts, jumpers → "hoodies"
- pants, jeans, trousers, chinos → "pants"
- shorts → "shorts"
- shoes, sneakers, boots, trainers → "shoes"
- jackets, coats, blazers → "jackets"
- dresses, gowns → "dresses"
- sweaters, cardigans → "sweaters"

GENDER EXTRACTION:
- "mens", "men", "for men", "guys", "male" → "mens"
- "womens", "women", "for women", "ladies", "girls", "female" → "womens"
- "unisex", "anyone", "gender neutral" → "unisex"

SIZE EXTRACTION:
- Letter sizes: XS, S, M, L, XL, XXL
- Numeric sizes: 28, 30, 32 (pants), 6, 8, 10 (shoes/womens), etc.
- Always capture as string (e.g., "M", "32", "10")

OPTIONAL INFORMATION (Improves Results):
- color_preference: black, white, blue, red, etc.
- budget_max: maximum price (number)
- style_preference: casual, formal, streetwear, athletic
- brand_preference: Nike, Adidas, etc.

SUFFICIENCY RULES:
✅ SUFFICIENT if:
   - Has category AND
   - Has size (for clothing items) AND
   - Has gender (mens/womens/unisex)

❌ INSUFFICIENT if:
   - Missing category OR
   - Missing size (for sized items) OR
   - Missing gender

EXAMPLES:
"mens black hoodies size L" 
  → SUFFICIENT ✅ (has category + size + gender)

"show me hoodies size M" 
  → INSUFFICIENT ❌ (missing gender)

"womens shirts" 
  → INSUFFICIENT ❌ (missing size)

"mens shoes size 10" 
  → SUFFICIENT ✅ (has all 3)

"I need something nice" 
  → INSUFFICIENT ❌ (missing everything)

Return JSON:
{
  "criteria": {
    "category": "hoodies",
    "size": "M",
    "gender": "mens",
    "color_preference": "black",
    ...
  },
  "decision": "sufficient" or "insufficient",
  "reasoning": "brief explanation of what's missing or why sufficient",
  "confidence": 0.0-1.0
}"""

        user_prompt = f"""Previous criteria: {current_criteria}

Conversation:
{conversation_text}

Extract shopping criteria and assess if we have enough to search. Return JSON:"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            # Parse JSON from response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                
                # Merge criteria with existing (new info takes precedence)
                merged_criteria = current_criteria.copy()
                merged_criteria.update(analysis.get("criteria", {}))
                analysis["criteria"] = merged_criteria
                
                return analysis
            else:
                print("⚠️ No JSON in AI response, using fallback")
                return self._simple_fallback_analysis(current_criteria)
                
        except Exception as e:
            print(f"⚠️ AI analysis error: {e}")
            return self._simple_fallback_analysis(current_criteria)
    
    def _validate_and_enhance(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate AI decision with hard rules as backup.
        Ensures we truly have Category + Size + Gender before saying "sufficient".
        """
        criteria = analysis["criteria"]
        ai_decision = analysis["decision"]
        
        # Run validation check
        validation_result = self._validate_sufficiency(criteria)
        
        if validation_result["sufficient"] != (ai_decision == "sufficient"):
            # AI and validation disagree - use validation (safer)
            print(f"⚠️ Overriding AI decision: '{ai_decision}' → '{validation_result['status']}'")
            print(f"   Reason: {validation_result['reason']}")
            
            analysis["decision"] = validation_result["status"]
            analysis["reasoning"] = f"{validation_result['reason']} (validation override)"
            analysis["validation_override"] = True
        
        return analysis
    
    def _validate_sufficiency(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hard validation rules to check Category + Size + Gender.
        This is the backup safety check if AI makes a mistake.
        """
        category = criteria.get("category")
        size = criteria.get("size")
        gender = criteria.get("gender")
        
        # Rule 1: Must have category
        if not category:
            return {
                "sufficient": False,
                "status": "insufficient",
                "reason": "Missing category (what type of clothing?)"
            }
        
        # Rule 2: Sized items must have size
        if category in self.SIZED_CATEGORIES and not size:
            return {
                "sufficient": False,
                "status": "insufficient",
                "reason": f"Missing size for {category}"
            }
        
        # Rule 3: Must have gender (CRITICAL!)
        if not gender:
            return {
                "sufficient": False,
                "status": "insufficient",
                "reason": "Missing gender (mens or womens?)"
            }
        
        # All checks passed!
        return {
            "sufficient": True,
            "status": "sufficient",
            "reason": "Has category, size, and gender - ready to search!"
        }
    
    def _simple_fallback_analysis(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Simple rule-based fallback when AI fails"""
        validation = self._validate_sufficiency(criteria)
        
        return {
            "criteria": criteria,
            "decision": validation["status"],
            "reasoning": f"Fallback: {validation['reason']}",
            "confidence": 0.6 if validation["sufficient"] else 0.5
        }
    
    def _build_state_update(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Build state update with ONLY valid OutfitterState fields"""
        
        criteria = analysis["criteria"]
        is_sufficient = analysis["decision"] == "sufficient"
        
        # Log the analysis details (not stored in state)
        print(f"📊 Analysis Summary:")
        print(f"   Category: {criteria.get('category', 'None')}")
        print(f"   Size: {criteria.get('size', 'None')}")
        print(f"   Gender: {criteria.get('gender', 'None')}")
        print(f"   Color: {criteria.get('color_preference', 'Any')}")
        print(f"   Confidence: {analysis.get('confidence', 0.0):.2f}")
        print(f"   Next: {'🔍 Search' if is_sufficient else '❓ Clarification'}")
        
        if is_sufficient:
            return {
                "search_criteria": criteria,
                "needs_clarification": False,
                "conversation_stage": "searching",
                "next_step": "parallel_searcher"
            }
        else:
            return {
                "search_criteria": criteria,
                "needs_clarification": True,
                "conversation_stage": "discovery",
                "next_step": "clarification_asker"
            }
    
    def _fallback_analysis(self, state: OutfitterState) -> Dict[str, Any]:
        """Emergency fallback when everything fails"""
        print("🚨 Using emergency fallback")
        
        current_criteria = state.get("search_criteria", {})
        validation = self._validate_sufficiency(current_criteria)
        
        if validation["sufficient"]:
            return {
                "search_criteria": current_criteria,
                "needs_clarification": False,
                "conversation_stage": "searching",
                "next_step": "parallel_searcher"
            }
        else:
            return {
                "search_criteria": current_criteria,
                "needs_clarification": True,
                "conversation_stage": "discovery",
                "next_step": "clarification_asker"
            }