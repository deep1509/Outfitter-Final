"""
Virtual Try-On Agent - AI-powered clothing visualization
Uses Google Gemini's specialized image-to-image model to overlay clothing items onto user photos.
This version does NOT include a fallback composite method.
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage
from agents.state import OutfitterState
import os
import io
import time
import random
import base64
from PIL import Image
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

class VirtualTryOnAgent:
    """
    AI-powered virtual try-on agent using a specialized Google Gemini image-to-image model.
    """
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("CRITICAL: GOOGLE_API_KEY environment variable not set.")
        
        genai.configure(api_key=self.api_key)
        self.model_name = "gemini-2.5-flash-image-preview"
        
        self.category_mapping = {
            "top": ["shirts", "t-shirts", "hoodies", "sweaters", "jackets", "blouses", "tops", "shirt", "tee", "tank", "blouse", "sweater", "cardigan", "vest"],
            "bottom": ["pants", "jeans", "shorts", "trousers", "skirts", "leggings", "joggers", "jogger", "pant", "trouser", "short", "skirt", "legging", "chino", "cargo", "denim"],
            "shoes": ["shoes", "sneakers", "boots", "sandals", "heels", "flats", "sneaker", "boot", "sandal", "heel", "flat", "loafers", "oxfords"],
            "accessories": ["hats", "bags", "belts", "watches", "jewelry", "scarves", "hat", "bag", "belt", "watch", "scarf", "necklace", "bracelet", "ring"]
        }
    
    def process_virtual_tryon(self, state: OutfitterState) -> Dict[str, Any]:
        """
        Main entry point for virtual try-on processing.
        """
        try:
            print("🎭 VirtualTryOnAgent: Processing virtual try-on...")
            
            cart_items = state.get("selected_products", [])
            user_photo = state.get("user_photo", None)
            
            if not cart_items:
                return self._no_items_response()
            
            if not user_photo:
                return self._no_photo_response()
            
            categorized_items = self._categorize_clothing_items(cart_items)
            print(f"   📦 Categorized items: {categorized_items}")
            
            tryon_results = self._generate_tryon_images(user_photo, categorized_items)
            
            return {
                "messages": [AIMessage(content="🎭 Virtual try-on complete! Check the sidebar to see how the items look on you!")],
                "virtual_tryon_results": tryon_results,
                "categorized_items": categorized_items,
                "conversation_stage": "cart",
                "next_step": "wait_for_user"
            }
            
        except Exception as e:
            logger.error(f"Virtual try-on error: {e}")
            return self._error_response(str(e))

    def _categorize_clothing_items(self, cart_items: List[Dict]) -> Dict[str, List[Dict]]:
        categorized = {"top": [], "bottom": [], "shoes": [], "accessories": []}
        for item in cart_items:
            item_name = item.get("name", "").lower()
            item_category = item.get("category", "").lower()
            detected_category = self._detect_item_category(item_name, item_category)
            if detected_category in categorized:
                categorized[detected_category].append(item)
        return categorized
    
    def _detect_item_category(self, item_name: str, item_category: str) -> str:
        # Convert to lowercase for case-insensitive matching
        item_name_lower = item_name.lower()
        item_category_lower = item_category.lower()
        
        for category, keywords in self.category_mapping.items():
            for keyword in keywords:
                if keyword in item_name_lower or keyword in item_category_lower:
                    return category
        return "top"

    def _generate_tryon_images(self, user_photo: str, categorized_items: Dict[str, List[Dict]]) -> Dict[str, Any]:
        try:
            # Collect one item from each category for the complete outfit
            outfit_items = {}
            for category, items in categorized_items.items():
                if items:
                    outfit_items[category] = items[0]  # Take the first item from each category
                    print(f"   📦 Selected {category}: {items[0]['name']}")
            
            if not outfit_items:
                return {"error": "No items found for virtual try-on"}
            
            print(f"   🎨 Generating complete outfit try-on with {len(outfit_items)} items")
            
            # Generate single composite image with all items
            tryon_image = self._create_complete_outfit_tryon(user_photo, outfit_items)
            
            if tryon_image:
                return {
                    "complete_outfit": {
                        "items": outfit_items,
                        "tryon_image": tryon_image,
                        "success": True
                    }
                }
            else:
                return {
                    "complete_outfit": {
                        "items": outfit_items,
                        "error": "AI failed to generate complete outfit try-on image.",
                        "success": False
                    }
                }
            
        except Exception as e:
            logger.error(f"Error generating try-on images: {e}")
            return {"error": str(e)}

    def _create_complete_outfit_tryon(self, user_photo: str, outfit_items: Dict[str, Dict]) -> Optional[str]:
        """
        Create a complete outfit try-on image with all selected items.
        """
        try:
            # Download all item images
            item_images = {}
            for category, item in outfit_items.items():
                item_image_url = item.get("image_url", "")
                if item_image_url:
                    item_bytes = self._download_item_image(item_image_url)
                    if item_bytes:
                        item_images[category] = item_bytes
                        print(f"   ✅ Downloaded {category} image: {item['name']}")
                    else:
                        print(f"   ❌ Failed to download {category} image: {item['name']}")
            
            if not item_images:
                logger.warning("No item images could be downloaded")
                return None
            
            # Process user photo
            user_bytes = self._process_user_photo(user_photo)
            if not user_bytes:
                logger.warning("Could not process user photo")
                return None
            
            # Create comprehensive prompt for complete outfit
            outfit_description = self._build_outfit_description(outfit_items)
            prompt = f"""
CRITICAL INSTRUCTIONS - READ CAREFULLY:

1. PERSON IDENTITY:
   - The FIRST image is the person who MUST appear in the final result
   - USE ONLY THIS PERSON'S FACE AND BODY
   - PRESERVE their face, skin tone, hair, body shape, pose, and background exactly as shown
   - IGNORE any models or people in the clothing product images

2. CLOTHING PRODUCTS:
The following images show clothing items to overlay onto the first person:
{outfit_description}

3. PRODUCT ACCURACY - EXTREMELY IMPORTANT:
   - Show each clothing item EXACTLY as it appears in its product image
   - DO NOT add logos, text, patterns, or designs that are not in the original product image
   - DO NOT remove logos, text, patterns, or designs that ARE in the original product image
   - If a product is plain/solid color, keep it plain - DO NOT add any branding or decorations
   - If a product has logos/graphics, keep them exactly as shown - DO NOT alter or remove them
   - PRESERVE the exact color, texture, style, and all visual details of each product
   - DO NOT modify, enhance, or "improve" the products in any way

4. FINAL OUTPUT:
   - Show the person wearing ALL items as a complete outfit
   - Ensure proper fit and realistic appearance
   - Maintain natural lighting and shadows
   - Return only the final edited image with no text or annotations

REMEMBER: Show products EXACTLY as they are - no additions, no removals, no modifications.
"""
            
            # Convert bytes to PIL Images
            user_image = Image.open(io.BytesIO(user_bytes))
            
            # Prepare all item images for the API
            item_pil_images = []
            for category, item_bytes in item_images.items():
                item_pil_images.append(Image.open(io.BytesIO(item_bytes)))
            
            model = genai.GenerativeModel(self.model_name)
            
            print(f"   🚀 Calling Gemini for complete outfit with {len(item_pil_images)} items")
            print(f"   👤 User image will be prioritized as the primary person")
            
            # Create content list with user image FIRST and emphasized, then item images
            content_list = [prompt, user_image] + item_pil_images
            response = self._call_gemini_with_retries(model, content_list)
            
            if not response:
                logger.warning("Gemini response was empty.")
                return None

            # Check if response has image data
            if hasattr(response, 'parts') and response.parts:
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        print("   ✅ Complete outfit image generated!")
                        image_data = part.inline_data.data
                        return base64.b64encode(image_data).decode('utf-8')
            
            logger.warning("No image data found in Gemini response.")
            return None

        except Exception as e:
            logger.error(f"Error creating complete outfit try-on: {e}")
            return None

    def _build_outfit_description(self, outfit_items: Dict[str, Dict]) -> str:
        """Build a description of the complete outfit"""
        description_parts = []
        image_num = 2  # First image is user, so clothing starts at 2
        for category, item in outfit_items.items():
            description_parts.append(f"- Image {image_num} ({category.title()}): {item['name']}")
            image_num += 1
        return "\n".join(description_parts)

    # --- MODIFIED ---
    # This function now only attempts the Gemini generation and returns None on failure.
    def _create_tryon_image(self, user_photo: str, item_image_url: str, category: str) -> Optional[str]:
        """
        Processes images and attempts to create a virtual try-on image using Gemini.
        Returns the base64 encoded image on success, or None on failure.
        """
        try:
            user_bytes = self._process_user_photo(user_photo)
            item_bytes = self._download_item_image(item_image_url)
            
            if not user_bytes or not item_bytes:
                return None
            
            # Directly call the Gemini method and return its result.
            tryon_image_b64 = self._create_gemini_tryon(user_bytes, item_bytes, category)
            
            if tryon_image_b64:
                return tryon_image_b64
            else:
                logger.warning("Gemini AI generation failed. No fallback method configured.")
                return None
            
        except Exception as e:
            logger.error(f"Error creating try-on image: {e}")
            return None
    
    def _create_gemini_tryon(self, user_bytes: bytes, item_bytes: bytes, category: str) -> Optional[str]:
        """
        Create realistic virtual try-on using the special Gemini image-to-image preview model.
        """
        try:
            prompt = (
                "CRITICAL INSTRUCTIONS:\n\n"
                "1. PERSON IDENTITY:\n"
                "   - The FIRST image shows the person who MUST appear in the final result\n"
                "   - PRESERVE their exact face, skin tone, hair, body shape, pose, and background\n"
                "   - IGNORE any model or person shown in the clothing image\n\n"
                "2. CLOTHING PRODUCT:\n"
                "   - The SECOND image shows a clothing item to overlay onto the person\n"
                "   - Show this clothing item EXACTLY as it appears in the product image\n"
                "   - DO NOT add logos, text, patterns, or designs that are not in the original\n"
                "   - DO NOT remove logos, text, patterns, or designs that ARE in the original\n"
                "   - If the product is plain, keep it plain - DO NOT add branding\n"
                "   - If the product has graphics, keep them exactly as shown\n"
                "   - PRESERVE the exact color, texture, and all visual details\n\n"
                "3. FINAL OUTPUT:\n"
                "   - Overlay ONLY the clothing item onto the person from the first image\n"
                "   - Make the clothing fit naturally and realistically\n"
                "   - Maintain the person's original pose, lighting, and background\n"
                "   - Return only the final edited image with no text\n\n"
                "REMEMBER: Show the product EXACTLY as it is - no modifications whatsoever."
            )
            
            # Convert bytes to PIL Images for the API
            user_image = Image.open(io.BytesIO(user_bytes))
            item_image = Image.open(io.BytesIO(item_bytes))
            
            model = genai.GenerativeModel(self.model_name)
            
            print(f"   🚀 Calling Gemini image preview model: {self.model_name}")
            print(f"   👤 Preserving user's face from uploaded photo")
            response = self._call_gemini_with_retries(model, [prompt, user_image, item_image])

            if not response:
                logger.warning("Gemini response was empty.")
                return None

            # Check if response has image data
            if hasattr(response, 'parts') and response.parts:
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        print("   ✅ Image data received from Gemini!")
                        image_data = part.inline_data.data
                        return base64.b64encode(image_data).decode('utf-8')
            
            logger.warning("No image data found in Gemini response. It may have been blocked.")
            return None

        except Exception as e:
            logger.error(f"Error creating Gemini try-on with image preview model: {e}")
            return None

    def _call_gemini_with_retries(self, model, content_list, max_attempts: int = 4, base_delay: float = 2.0):
        for attempt in range(1, max_attempts + 1):
            try:
                time.sleep(1.0)
                response = model.generate_content(content_list)
                return response
            except Exception as e:
                logger.warning(f"Gemini call attempt {attempt} failed: {e}")
                if attempt == max_attempts:
                    raise
                sleep_s = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                time.sleep(sleep_s)

    def _process_user_photo(self, photo_data: str) -> Optional[bytes]:
        try:
            if photo_data and not photo_data.startswith('data:image'):
                return self._to_jpeg_bytes_from_path(photo_data)
            elif photo_data.startswith('data:image'):
                photo_data = photo_data.split(',')[1]
                image_bytes = base64.b64decode(photo_data)
                image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                return self._to_jpeg_bytes(image)
            else:
                return None
        except Exception as e:
            logger.error(f"Error processing user photo: {e}")
            return None

    def _to_jpeg_bytes_from_path(self, path: str, max_side: int = 1024, quality: int = 82) -> bytes:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        s = min(1.0, max_side / max(w, h))
        if s < 1.0:
            img = img.resize((int(w*s), int(h*s)), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()

    def _download_item_image(self, image_url: str) -> Optional[bytes]:
        try:
            import requests
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            return self._to_jpeg_bytes(image)
        except Exception as e:
            logger.error(f"Error downloading item image {image_url}: {e}")
            return None

    def _to_jpeg_bytes(self, image: Image.Image, max_side: int = 1024, quality: int = 82) -> bytes:
        w, h = image.size
        s = min(1.0, max_side / max(w, h))
        if s < 1.0:
            image = image.resize((int(w*s), int(h*s)), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    
    # --- REMOVED ---
    # The _create_composite_image method has been completely removed.
    
    def _no_items_response(self) -> Dict[str, Any]:
        return {"messages": [AIMessage(content="🛒 Your cart is empty! Add some items first to try them on virtually.")], "conversation_stage": "cart", "next_step": "wait_for_user"}
    
    def _no_photo_response(self) -> Dict[str, Any]:
        return {"messages": [AIMessage(content="📸 Please upload your photo first to try on items virtually!")], "conversation_stage": "cart", "next_step": "wait_for_user"}
    
    def _error_response(self, error: str) -> Dict[str, Any]:
        return {"messages": [AIMessage(content=f"❌ Sorry, there was an issue with virtual try-on: {error}")], "conversation_stage": "cart", "next_step": "wait_for_user"}