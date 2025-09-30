import os
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from main import OutfitterAssistant
import asyncio

async def test_direct_search():
    assistant = OutfitterAssistant()
    assistant.setup_graph()
    
    history = []
    
    # Test 1: Complete information
    print("\n" + "="*60)
    print("TEST 1: Complete search - 'show me black hoodies size M'")
    print("="*60)
    history = await assistant.run_conversation(
        "show me black hoodies size M", 
        history
    )
    print(f"Response: {history[-1]['content'][:200]}...")
    
    # Test 2: Partial information (skip size)
    print("\n" + "="*60)
    print("TEST 2: Partial search - 'find red t-shirts'")
    print("="*60)
    history = []
    history = await assistant.run_conversation(
        "find red t-shirts",
        history
    )
    print(f"Response: {history[-1]['content'][:200]}...")

if __name__ == "__main__":
    asyncio.run(test_direct_search())