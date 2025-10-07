import os
import sys
import base64
import shutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- THE ONLY CHANGE IS ON THIS LINE ---
# Correcting the import path to match your confirmed directory structure.
import sys
import os

# Add the current directory to Python path to enable relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    # Try direct import first
    from agents.conversation_agents.virtualTryOnAgent import VirtualTryOnAgent
except ImportError:
    try:
        # Try importing the module directly
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "virtualTryOnAgent", 
            os.path.join(current_dir, "agents", "conversation_agents", "virtualTryOnAgent.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        VirtualTryOnAgent = module.VirtualTryOnAgent
    except Exception as e:
        print("Error: Could not import VirtualTryOnAgent.")
        print("Please make sure you run this script from the root of the 'outfitter_ai' project directory,")
        print("and that your agent file is located at 'agents/conversation_agents/virtualTryOnAgent.py'.")
        print(f"Current directory: {current_dir}")
        print(f"Python path: {sys.path}")
        print(f"Import error: {e}")
        sys.exit(1)

def run_test():
    """
    Runs a test case for the VirtualTryOnAgent, generating try-on images
    for a predefined t-shirt and joggers.
    """
    print("🚀 Initializing Virtual Try-On Agent Test...")

    # --- 1. SETUP ---
    try:
        agent = VirtualTryOnAgent()
        print("✅ Agent initialized successfully.")
    except ValueError as e:
        print(f"❌ CRITICAL ERROR: {e}")
        print("   Please ensure you have set the GOOGLE_API_KEY environment variable.")
        sys.exit(1)

    person_image_path = "tests/test_person_image.jpg"
    if not os.path.exists(person_image_path):
        print(f"❌ ERROR: Person image not found at '{person_image_path}'")
        return

    cart_items = [
        {
          "name": "Nike Dri-FIT T-Shirt Black",
          "image_url": "https://cdn.shopify.com/s/files/1/1023/3455/files/02055503-YB001_mens_0010.jpg?v=1759363326",
        },
        {
          "name": "Adidas Track Pants Navy Blue",
          "image_url": "https://cdn.shopify.com/s/files/1/1023/3455/files/03001797-YL200_mens_006_470e1889-a639-48a0-b933-cd04896c96a9.jpg?v=1723680848",
        }
    ]

    output_dir = "test_output"
    if os.path.exists(output_dir):
        print(f"   🧹 Clearing old results from '{output_dir}' directory...")
        shutil.rmtree(output_dir)

    os.makedirs(output_dir, exist_ok=True)
    print(f"   Results will be saved in the '{output_dir}' directory.")

    # --- 2. CATEGORIZATION TEST ---
    print(f"\n🔍 Testing categorization for {len(cart_items)} items:")
    categorized_items = agent._categorize_clothing_items(cart_items)
    
    for category, items in categorized_items.items():
        if items:
            print(f"   📦 {category.upper()}: {len(items)} items")
            for item in items:
                print(f"      - {item['name']}")
    
    # --- 3. EXECUTION ---
    print(f"\n--- Testing Complete Outfit Try-On ---")
    
    # Simulate the state that would come from the UI
    state = {
        "selected_products": cart_items,
        "user_photo": person_image_path
    }
    
    # Process virtual try-on using the main method
    result = agent.process_virtual_tryon(state)
    
    # Check if we got results
    tryon_results = result.get("virtual_tryon_results", {})
    
    if tryon_results and "complete_outfit" in tryon_results:
        complete_outfit = tryon_results["complete_outfit"]
        
        if complete_outfit.get("success") and complete_outfit.get("tryon_image"):
            print(f"   ✅ SUCCESS: AI generated complete outfit try-on!")
            
            try:
                image_data = base64.b64decode(complete_outfit["tryon_image"])
                output_path = os.path.join(output_dir, "complete_outfit_tryon.png")
                
                with open(output_path, "wb") as f:
                    f.write(image_data)
                print(f"   💾 Complete outfit image saved to: {output_path}")
                
                # Show what items were included
                items = complete_outfit.get("items", {})
                print(f"   📦 Outfit includes:")
                for category, item in items.items():
                    print(f"      - {category.title()}: {item['name']}")
                    
            except Exception as e:
                print(f"   ❌ FAILED to decode or save the image: {e}")
        else:
            print(f"   ❌ FAILED: {complete_outfit.get('error', 'Unknown error')}")
    else:
        print(f"   ❌ FAILED: No complete outfit results generated")

    print("\n🚀 Test finished.")


if __name__ == "__main__":
    run_test()

