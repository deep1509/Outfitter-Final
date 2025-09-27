"""
Simple command line interface to test the end-to-end conversation flow
Create this as test_conversation.py in your project root
"""

import asyncio
import sys
from main import OutfitterAssistant

class ConversationTester:
    """Simple CLI interface to test the Outfitter.ai assistant"""
    
    def __init__(self):
        self.assistant = OutfitterAssistant()
        self.conversation_history = []
        
    async def start_testing(self):
        """Start the interactive testing session"""
        print("🛍️  OUTFITTER.AI CONVERSATION TESTER")
        print("="*50)
        print("This will test your real scraping integration end-to-end.")
        print("Type 'quit' or 'exit' to stop testing.")
        print("="*50)
        
        # Setup the assistant
        self.assistant.setup_graph()
        print("\n✅ Assistant ready for testing!")
        
        print("\n💡 Suggested test flow:")
        print("1. Start with: 'Hello'")
        print("2. Search request: 'I'm looking for black hoodies'")
        print("3. Answer clarification questions")
        print("4. See real products from Universal Store + CultureKings")
        print("\n" + "="*50)
        
        # Start conversation loop
        while True:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['quit', 'exit', 'stop']:
                    print("\n👋 Ending test session. Goodbye!")
                    break
                
                # Show processing
                print("\n🤖 Assistant (processing...)...")
                
                # Get response from assistant
                response_history = await self.assistant.run_conversation(
                    message=user_input, 
                    history=self.conversation_history
                )
                
                # Update conversation history
                self.conversation_history = response_history
                
                # Display assistant response
                if response_history:
                    latest_response = response_history[-1]
                    if latest_response.get("role") == "assistant":
                        print(f"\n🤖 Assistant: {latest_response['content']}")
                        
                        # Show debug info if useful
                        self._show_debug_info()
                
            except KeyboardInterrupt:
                print("\n\n⏹️  Test interrupted. Goodbye!")
                break
                
            except Exception as e:
                print(f"\n❌ Error during testing: {e}")
                print("Continuing test session...")
                
        # Cleanup
        self.assistant.cleanup()
    
    def _show_debug_info(self):
        """Show helpful debugging information"""
        total_messages = len(self.conversation_history)
        user_messages = len([m for m in self.conversation_history if m.get("role") == "user"])
        
        print(f"\n📊 Debug: {user_messages} user messages, {total_messages} total messages")

async def main():
    """Run the conversation tester"""
    tester = ConversationTester()
    await tester.start_testing()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test session ended.")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)