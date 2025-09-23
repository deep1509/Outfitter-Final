"""
Outfitter.ai - LangGraph Shopping Assistant
Stage 1: Enhanced conversation agents with AI-powered responses
"""

import os
import uuid
from typing import Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.state import OutfitterState
from agents.intent_classifier import RobustIntentClassifier
from agents.conversation_agents.greeterAgent import GreeterAgent
from agents.conversation_agents.clarificationAgent import ClarificationAgent
from agents.conversation_agents.generalResponderAgent import SimpleGeneralResponder

# Load environment variables
load_dotenv()

class OutfitterAssistant:
    """
    Main Outfitter.ai shopping assistant using LangGraph with enhanced conversation agents.
    Stage 1: AI-powered conversation flow with mock search capabilities.
    """
    
    def __init__(self):
        # Initialize all conversation agents
        self.intent_classifier = RobustIntentClassifier()
        self.greeter = GreeterAgent()
        self.clarification_agent = ClarificationAgent()
        self.general_responder = SimpleGeneralResponder()
        
        # Memory for conversation persistence
        self.memory = MemorySaver()
        self.graph = None
        self.session_id = str(uuid.uuid4())
        
    def setup_graph(self):
        """Build the LangGraph workflow with enhanced agents"""
        print("Setting up Outfitter.ai LangGraph with enhanced agents...")
        
        # Create the graph
        workflow = StateGraph(OutfitterState)
        
        # Add enhanced conversation nodes
        workflow.add_node("intent_classifier", self._intent_classifier_node)
        workflow.add_node("greeter", self._greeter_node)
        workflow.add_node("clarification_asker", self._clarification_node)
        workflow.add_node("general_responder", self._general_responder_node)
        
        # Mock nodes for Stage 1 (will be implemented in later stages)
        workflow.add_node("needs_analyzer", self._mock_needs_analyzer)
        workflow.add_node("selection_handler", self._mock_selection_handler)
        workflow.add_node("checkout_handler", self._mock_checkout_handler)
        workflow.add_node("parallel_searcher", self._mock_parallel_searcher)
        
        # Set up the enhanced routing flow
        workflow.add_edge(START, "intent_classifier")
        
        # Intent classifier routes to appropriate enhanced agents
        workflow.add_conditional_edges(
            "intent_classifier",
            self._route_after_intent_classification,
            {
                "greeter": "greeter",
                "needs_analyzer": "needs_analyzer",
                "selection_handler": "selection_handler", 
                "checkout_handler": "checkout_handler",
                "general_responder": "general_responder",
                "clarification_asker": "clarification_asker",
                "parallel_searcher": "parallel_searcher"
            }
        )
        
        # Enhanced conversation flow routing
        workflow.add_conditional_edges(
            "greeter",
            self._route_after_greeting,
            {
                "needs_analyzer": "needs_analyzer",
                "wait_for_user": END
            }
        )
        
        workflow.add_conditional_edges(
            "clarification_asker", 
            self._route_after_clarification,
            {
                "parallel_searcher": "parallel_searcher",
                "clarification_asker": "clarification_asker",
                "wait_for_user": END
            }
        )
        
        # All other nodes end for user input
        workflow.add_edge("general_responder", END)
        workflow.add_edge("needs_analyzer", END)
        workflow.add_edge("selection_handler", END)
        workflow.add_edge("checkout_handler", END)
        workflow.add_edge("parallel_searcher", END)
        
        # Compile the graph with memory
        self.graph = workflow.compile(checkpointer=self.memory)
        print("✅ Enhanced Outfitter.ai LangGraph setup complete!")
        
    # ============ ENHANCED AGENT NODE WRAPPERS ============
    
    def _intent_classifier_node(self, state: OutfitterState) -> Dict[str, Any]:
        """Enhanced AI-powered intent classification node"""
        return self.intent_classifier.classify_intent(state)
    
    def _greeter_node(self, state: OutfitterState) -> Dict[str, Any]:
        """Enhanced personalized greeting node"""
        return self.greeter.greet_user(state)
    
    def _clarification_node(self, state: OutfitterState) -> Dict[str, Any]:
        """Enhanced smart clarification questioning node"""  
        return self.clarification_agent.ask_clarification(state)
    
    def _general_responder_node(self, state: OutfitterState) -> Dict[str, Any]:
        """Enhanced AI-powered general response node"""
        return self.general_responder.respond_to_general_query(state)
    
    # ============ ENHANCED ROUTING LOGIC ============
    
    def _route_after_intent_classification(self, state: OutfitterState) -> str:
        """Route based on enhanced intent classification results"""
        next_step = state.get("next_step", "general_responder")
        
        # Handle special routing cases
        if state.get("needs_clarification", False):
            return "clarification_asker"
        
        if state.get("urgency_flag", False):
            # High urgency routes directly to appropriate handler
            return next_step
        
        return next_step
    
    def _route_after_greeting(self, state: OutfitterState) -> str:
        """Route after enhanced greeting based on user context"""
        next_step = state.get("next_step", "wait_for_user")
        
        # Enhanced greeter might fast-track urgent users
        if next_step == "needs_analyzer":
            return "needs_analyzer"
        
        return "wait_for_user"
    
    def _route_after_clarification(self, state: OutfitterState) -> str:
        """Route after enhanced clarification questioning"""
        
        # Check if clarification is complete
        if not state.get("needs_clarification", True):
            return "parallel_searcher"
        
        # Check if we should continue clarifying or transition
        next_step = state.get("next_step", "wait_for_user")
        
        if next_step == "parallel_searcher":
            return "parallel_searcher"
        elif next_step == "clarification_asker":
            return "clarification_asker"
        
        return "wait_for_user"
    
    # ============ MOCK NODES FOR STAGE 1 ============
    
    def _mock_needs_analyzer(self, state: OutfitterState) -> Dict[str, Any]:
        """Mock needs analyzer - enhanced for Stage 1 demonstration"""
        from langchain_core.messages import AIMessage
        
        # Get user message for context
        messages = state.get("messages", [])
        user_input = ""
        for msg in reversed(messages):
            if hasattr(msg, 'content') and isinstance(msg.content, str) and not isinstance(msg, AIMessage):
                user_input = msg.content
                break
        
        response = f"""🔧 [MOCK NEEDS ANALYZER]

I can see you're interested in: "{user_input}"

In Stage 2, I'll analyze your needs and search CultureKings for:
- Product category detection
- Size and color preferences  
- Style and budget analysis
- Real product recommendations

Ready to move to the next stage of development!"""
        
        return {
            "messages": [AIMessage(content=response)],
            "search_criteria": {"mock": True, "user_input": user_input},
            "next_step": "wait_for_user"
        }
    
    def _mock_selection_handler(self, state: OutfitterState) -> Dict[str, Any]:
        """Mock selection handler - will be implemented in Stage 3"""
        from langchain_core.messages import AIMessage
        return {
            "messages": [AIMessage(content="🔧 [MOCK SELECTION] Product selection handling will be implemented in Stage 3 with real CultureKings integration!")],
            "next_step": "wait_for_user"
        }
    
    def _mock_checkout_handler(self, state: OutfitterState) -> Dict[str, Any]:
        """Mock checkout handler - will be implemented in Stage 4"""
        from langchain_core.messages import AIMessage
        return {
            "messages": [AIMessage(content="🔧 [MOCK CHECKOUT] Checkout processing will be implemented in Stage 4 with cart management!")],
            "next_step": "wait_for_user"
        }
    
    def _mock_parallel_searcher(self, state: OutfitterState) -> Dict[str, Any]:
        """Mock parallel searcher - will be implemented in Stage 2"""
        from langchain_core.messages import AIMessage
        
        search_criteria = state.get("search_criteria", {})
        
        response = f"""🔧 [MOCK PARALLEL SEARCHER]

Based on your preferences: {search_criteria}

In Stage 2, this will:
✓ Search CultureKings in real-time
✓ Scrape product listings with Playwright  
✓ Find matching items with prices and images
✓ Present curated recommendations

The enhanced conversation agents are working! Ready for Stage 2 implementation."""
        
        return {
            "messages": [AIMessage(content=response)],
            "search_results": [{"mock": True}],
            "next_step": "wait_for_user"
        }
    
    # ============ MAIN INTERFACE ============
    
    async def run_conversation(self, message: str, history: List[Dict]) -> List[Dict]:
        """
        Run conversation with enhanced agents and full memory.
        Handles the complete conversation flow with AI-powered responses.
        """
        print(f"🤖 Processing: '{message}' with {len(history)} history items")
        
        config = {"configurable": {"thread_id": self.session_id}}
        
        # Convert history to proper message format
        from langchain_core.messages import HumanMessage, AIMessage
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Add new user message
        messages.append(HumanMessage(content=message))
        
        # Build enhanced state with conversation context
        user_message_count = len([msg for msg in messages if isinstance(msg, HumanMessage)])
        
        state = {
            "messages": messages,
            "current_intent": None,
            "search_criteria": {},
            "search_results": [],
            "selected_products": [],
            "next_step": None,
            "needs_clarification": False,
            "conversation_stage": "greeting" if user_message_count == 1 else "discovery",
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat() if user_message_count == 1 else None
        }
        
        try:
            # Run the enhanced conversation graph
            result = await self.graph.ainvoke(state, config=config)
            print(f"✅ Enhanced graph execution completed")
            
            # Extract the latest assistant message
            assistant_messages = [msg for msg in result.get("messages", []) if isinstance(msg, AIMessage)]
            if assistant_messages:
                latest_response = assistant_messages[-1].content
            else:
                latest_response = "I'm here to help you find great clothing! What are you looking for today?"
            
            # Format response for interface
            user_msg = {"role": "user", "content": message}
            assistant_msg = {"role": "assistant", "content": latest_response}
            
            return history + [user_msg, assistant_msg]
            
        except Exception as e:
            print(f"❌ Enhanced conversation error: {e}")
            import traceback
            traceback.print_exc()
            
            # Enhanced error handling
            user_msg = {"role": "user", "content": message}
            error_msg = {"role": "assistant", "content": "I apologize for the technical hiccup. I'm your fashion and shopping assistant - what can I help you find today?"}
            return history + [user_msg, error_msg]
    
    def cleanup(self):
        """Clean up enhanced conversation resources"""
        print("🧹 Cleaning up enhanced conversation resources...")


# ============ MAIN EXECUTION ============

def main():
    """Test the enhanced Outfitter.ai setup"""
    print("🚀 Starting Enhanced Outfitter.ai...")
    
    assistant = OutfitterAssistant()
    assistant.setup_graph()
    
    print("\n✅ Enhanced setup complete!")
    print("🎯 Stage 1 Enhanced Features:")
    print("   ✓ AI-powered intent classification with context awareness")
    print("   ✓ Personalized greetings that adapt to user type") 
    print("   ✓ Smart clarification questions (one at a time)")
    print("   ✓ Fashion expert general responses")
    print("   ✓ Mock nodes ready for Stage 2 implementation")
    print("\n🛍️ Ready to provide professional shopping assistance!")

if __name__ == "__main__":
    import asyncio
    
    asyncio.run(main())