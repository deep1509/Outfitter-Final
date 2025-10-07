#!/usr/bin/env python3
"""
Debug Gemini API to see what's happening
"""

import os
import sys
import google.generativeai as genai
from PIL import Image
import io

def debug_gemini_api():
    """Debug the Gemini API to see why it's not working"""
    
    print("🔍 Debugging Gemini API...")
    
    # Configure API
    api_key = os.getenv("GOOGLE_API_KEY", "AIzaSyCpiM1lEbYF37uc_MxR3qnKSThvcTm4fTk")
    if not api_key:
        print("❌ No API key found")
        return False
    
    print(f"✅ API key found: {api_key[:10]}...")
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        print("✅ Gemini model configured")
    except Exception as e:
        print(f"❌ Failed to configure Gemini: {e}")
        return False
    
    # Test 1: Simple text prompt
    print("\n📝 Test 1: Simple text prompt")
    try:
        response = model.generate_content("Hello, can you respond with 'API is working'?")
        print(f"✅ Text response: {response.text}")
    except Exception as e:
        print(f"❌ Text prompt failed: {e}")
    
    # Test 2: Image analysis
    print("\n🖼️ Test 2: Image analysis")
    try:
        test_image_path = "tests/test_person_image.jpg"
        if os.path.exists(test_image_path):
            image = Image.open(test_image_path)
            print(f"✅ Test image loaded: {image.size}")
            
            response = model.generate_content([
                "What do you see in this image? Describe the person briefly.",
                image
            ])
            print(f"✅ Image analysis response: {response.text}")
        else:
            print(f"❌ Test image not found: {test_image_path}")
    except Exception as e:
        print(f"❌ Image analysis failed: {e}")
    
    # Test 3: Try image generation with simple prompt
    print("\n🎨 Test 3: Simple image generation")
    try:
        test_image_path = "tests/test_person_image.jpg"
        if os.path.exists(test_image_path):
            image = Image.open(test_image_path)
            
            # Very simple prompt
            response = model.generate_content([
                "Create a simple version of this image with a blue background",
                image
            ])
            
            print(f"📊 Response type: {type(response)}")
            print(f"📊 Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
            
            # Check candidates
            if hasattr(response, 'candidates'):
                print(f"📊 Candidates: {len(response.candidates) if response.candidates else 0}")
                if response.candidates:
                    candidate = response.candidates[0]
                    print(f"📊 Candidate finish_reason: {getattr(candidate, 'finish_reason', 'Unknown')}")
                    if hasattr(candidate, 'safety_ratings'):
                        print(f"📊 Safety ratings: {candidate.safety_ratings}")
                    if hasattr(candidate, 'content'):
                        print(f"📊 Content parts: {len(candidate.content.parts) if candidate.content else 0}")
                        if candidate.content:
                            for i, part in enumerate(candidate.content.parts):
                                print(f"📊 Part {i}: {type(part)}")
                                if hasattr(part, 'inline_data'):
                                    print(f"📊 Inline data: {part.inline_data}")
                                if hasattr(part, 'text'):
                                    print(f"📊 Text: {part.text}")
            
            # Check prompt feedback
            if hasattr(response, 'prompt_feedback'):
                print(f"📊 Prompt feedback: {response.prompt_feedback}")
            
            # Check if we got an image
            if hasattr(response, 'parts'):
                print(f"📊 Direct parts: {len(response.parts) if response.parts else 0}")
                for i, part in enumerate(response.parts):
                    print(f"📊 Direct part {i}: {type(part)}")
                    if hasattr(part, 'inline_data'):
                        print(f"📊 Direct inline data: {part.inline_data}")
                    if hasattr(part, 'text'):
                        print(f"📊 Direct text: {part.text}")
            
        else:
            print(f"❌ Test image not found: {test_image_path}")
    except Exception as e:
        print(f"❌ Image generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Check API status
    print("\n🔧 Test 4: API Status Check")
    try:
        # Try to get model info
        models = genai.list_models()
        print(f"✅ Available models: {len(list(models))}")
        for model in genai.list_models():
            if 'image' in model.name.lower():
                print(f"   📋 Image model: {model.name}")
    except Exception as e:
        print(f"❌ Model listing failed: {e}")
    
    return True

if __name__ == "__main__":
    debug_gemini_api()
