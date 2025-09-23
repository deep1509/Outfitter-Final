"""
Stage 1 Testing Script for Outfitter.ai
Tests the enhanced conversation agents with comprehensive scenarios
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import OutfitterAssistant

async def test_conversation_flow():
    """Test the enhanced conversation agents step by step"""
    
    print("🧪 Starting Stage 1 Comprehensive Tests...\n")
    
    # Initialize assistant
    assistant = OutfitterAssistant()
    assistant.setup_graph()
    
    # 15 comprehensive test cases covering all agent capabilities
    test_cases = [
        # Basic Intent Classification Tests
        {
            "message": "Hi there!",
            "expected": "Personalized greeting from Enhanced Greeter",
            "category": "Greeting"
        },
        {
            "message": "Hello, good morning!",
            "expected": "Professional greeting adapting to formal tone",
            "category": "Greeting - Formal"
        },
        
        # Fashion Expert Tests
        {
            "message": "What should I wear to a summer club party?",
            "expected": "Fashion advice from General Responder",
            "category": "Fashion Styling"
        },
        {
            "message": "What colors go with navy blue?",
            "expected": "Color coordination advice",
            "category": "Fashion - Color Theory"
        },
        {
            "message": "How should I dress for a job interview?",
            "expected": "Professional styling advice",
            "category": "Fashion - Formal Occasion"
        },
        
        # Search Intent Tests
        {
            "message": "I'm looking for black t-shirts",
            "expected": "Route to needs analyzer (mock response)",
            "category": "Product Search"
        },
        {
            "message": "I need new sneakers under $100",
            "expected": "Search intent with budget constraint",
            "category": "Product Search - Budget"
        },
        
        # Clarification Tests
        {
            "message": "I need clothes",
            "expected": "Smart clarification question",
            "category": "Clarification Required"
        },
        {
            "message": "I want something nice",
            "expected": "Clarification about occasion/style",
            "category": "Clarification - Vague Request"
        },
        
        # Complex Language Tests
        {
            "message": "I don't want anything expensive, just casual stuff",
            "expected": "Handle negation and extract preferences",
            "category": "Complex Language - Negation"
        },
        {
            "message": "My friend needs help but I also have a question about colors",
            "expected": "Multi-intent handling",
            "category": "Complex Language - Multi-Intent"
        },
        
        # Edge Cases
        {
            "message": "lookng for shrts in medim size",
            "expected": "Handle typos and informal language",
            "category": "Edge Case - Typos"
        },
        {
            "message": "What's trendy this season?",
            "expected": "Fashion trend advice",
            "category": "Fashion - Trends"
        },
        
        # Context Awareness Tests
        {
            "message": "Actually, can you help me with something else?",
            "expected": "Context-aware response offering help",
            "category": "Context Switch"
        },
        
        # Error Handling Test
        {
            "message": "",
            "expected": "Handle empty message gracefully",
            "category": "Edge Case - Empty Message"
        }
    ]
    
    history = []
    passed_tests = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"--- Test {i}: {test_case['category']} ---")
        print(f"Expected: {test_case['expected']}")
        print(f"User: '{test_case['message']}'")
        
        try:
            # Run conversation
            history = await assistant.run_conversation(test_case['message'], history)
            
            # Get latest response
            latest_response = history[-1]['content']
            print(f"Assistant: {latest_response[:100]}..." if len(latest_response) > 100 else f"Assistant: {latest_response}")
            
            # Validation logic
            test_passed = False
            
            if test_case['category'] == "Edge Case - Empty Message":
                # Empty message should get helpful fallback
                test_passed = "help" in latest_response.lower() or "assist" in latest_response.lower()
            
            elif "Fashion" in test_case['category']:
                # Fashion questions should get substantive advice
                test_passed = len(latest_response) > 50 and not "🔧 [MOCK" in latest_response
            
            elif "Greeting" in test_case['category']:
                # Greetings should welcome and offer help
                test_passed = ("welcome" in latest_response.lower() or "hello" in latest_response.lower()) and len(latest_response) > 30
            
            elif "Product Search" in test_case['category'] or "Clarification" in test_case['category']:
                # Should route to mock nodes or clarification
                test_passed = "🔧 [MOCK" in latest_response or ("?" in latest_response and len(latest_response) > 20)
            
            else:
                # General quality check
                test_passed = len(latest_response) > 20 and "error" not in latest_response.lower()
            
            if test_passed:
                print("✅ Test PASSED")
                passed_tests += 1
            else:
                print("❌ Test FAILED")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            print(f"Stack trace for debugging:")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*60 + "\n")
    
    # Final results
    print("🏁 Testing Completed!")
    print(f"📊 Results: {passed_tests}/{total_tests} tests passed ({(passed_tests/total_tests)*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Stage 1 agents are working correctly.")
    elif passed_tests >= total_tests * 0.8:
        print("👍 Most tests passed. Minor issues to investigate.")
    else:
        print("⚠️ Several tests failed. Check agent implementations and dependencies.")
    
    print("\nStage 1 Validation Complete - Ready for Stage 2 development!")

if __name__ == "__main__":
    asyncio.run(test_conversation_flow())