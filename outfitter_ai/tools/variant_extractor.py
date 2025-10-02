"""
Variant Extractor for Shopify Products
Extracts available sizes, colors, and other variants from product URLs.
Prepares product data for Shopify cart integration.
"""

import asyncio
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Page
import re
import json
from datetime import datetime

class VariantExtractor:
    """
    Extracts product variant information (sizes, colors) from product pages.
    Works with Shopify-based stores to get variant IDs for cart integration.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
    
    async def extract_variants(self, product_url: str, store_name: str = "") -> Dict[str, Any]:
        """
        Extract variant information from a product page.
        
        Returns:
            Dict with available sizes, colors, variant IDs, and pricing
        """
        print(f"🔍 Extracting variants from: {product_url}")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()
                
                # Navigate to product page
                await page.goto(product_url, timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=10000)
                
                # Extract variants based on store
                if "culturekings" in product_url.lower():
                    variants = await self._extract_culturekings_variants(page)
                elif "universalstore" in product_url.lower():
                    variants = await self._extract_universalstore_variants(page)
                else:
                    variants = await self._extract_generic_shopify_variants(page)
                
                await browser.close()
                
                print(f"✅ Found {len(variants.get('sizes', []))} sizes, {len(variants.get('colors', []))} colors")
                return variants
                
        except Exception as e:
            print(f"❌ Variant extraction error: {e}")
            return self._fallback_variants()
    
    async def _extract_culturekings_variants(self, page: Page) -> Dict[str, Any]:
        """Extract variants from CultureKings product page"""
        
        variants = {
            "sizes": [],
            "colors": [],
            "variant_data": [],
            "base_price": "",
            "available": True
        }
        
        try:
            # CultureKings uses Shopify - look for size selector
            size_selector = "button[name='Size'], .product-form__input button"
            size_buttons = page.locator(size_selector)
            
            count = await size_buttons.count()
            for i in range(min(count, 20)):  # Limit to 20 sizes
                button = size_buttons.nth(i)
                size_text = await button.text_content()
                is_available = not await button.is_disabled()
                
                if size_text:
                    variants["sizes"].append({
                        "size": size_text.strip(),
                        "available": is_available
                    })
            
            # Extract price
            price_selector = ".product-form__price, [data-product-price]"
            price_elem = page.locator(price_selector).first
            if await price_elem.count() > 0:
                price_text = await price_elem.text_content()
                variants["base_price"] = price_text.strip()
            
            # Try to extract Shopify variant JSON
            shopify_data = await self._extract_shopify_json(page)
            if shopify_data:
                variants["shopify_product_id"] = shopify_data.get("id")
                variants["variant_data"] = shopify_data.get("variants", [])
        
        except Exception as e:
            print(f"⚠️ CultureKings variant extraction error: {e}")
        
        return variants
    
    async def _extract_universalstore_variants(self, page: Page) -> Dict[str, Any]:
        """Extract variants from Universal Store product page"""
        
        variants = {
            "sizes": [],
            "colors": [],
            "variant_data": [],
            "base_price": "",
            "available": True
        }
        
        try:
            # Universal Store size selector
            size_selector = ".variant-input-wrap input, .product-form__option button"
            size_inputs = page.locator(size_selector)
            
            count = await size_inputs.count()
            for i in range(min(count, 20)):
                input_elem = size_inputs.nth(i)
                
                # Try to get size from value or text
                size_value = await input_elem.get_attribute("value")
                if not size_value:
                    size_value = await input_elem.text_content()
                
                if size_value:
                    variants["sizes"].append({
                        "size": size_value.strip(),
                        "available": True
                    })
            
            # Extract price
            price_selector = ".price, .product-price"
            price_elem = page.locator(price_selector).first
            if await price_elem.count() > 0:
                price_text = await price_elem.text_content()
                variants["base_price"] = price_text.strip()
            
            # Extract Shopify data
            shopify_data = await self._extract_shopify_json(page)
            if shopify_data:
                variants["shopify_product_id"] = shopify_data.get("id")
                variants["variant_data"] = shopify_data.get("variants", [])
        
        except Exception as e:
            print(f"⚠️ Universal Store variant extraction error: {e}")
        
        return variants
    
    async def _extract_generic_shopify_variants(self, page: Page) -> Dict[str, Any]:
        """Generic Shopify variant extraction"""
        
        variants = {
            "sizes": [],
            "colors": [],
            "variant_data": [],
            "base_price": "",
            "available": True
        }
        
        try:
            # Generic Shopify patterns
            shopify_data = await self._extract_shopify_json(page)
            
            if shopify_data:
                variants["shopify_product_id"] = shopify_data.get("id")
                
                # Extract variants from Shopify data
                for variant in shopify_data.get("variants", []):
                    size = variant.get("option1") or variant.get("title", "")
                    
                    if size:
                        variants["sizes"].append({
                            "size": size,
                            "available": variant.get("available", True),
                            "variant_id": variant.get("id"),
                            "price": variant.get("price")
                        })
                
                # Extract base price
                if shopify_data.get("price"):
                    variants["base_price"] = f"${shopify_data['price'] / 100:.2f}"
        
        except Exception as e:
            print(f"⚠️ Generic Shopify extraction error: {e}")
        
        return variants
    
    async def _extract_shopify_json(self, page: Page) -> Optional[Dict]:
        """
        Extract Shopify product JSON from page.
        Most Shopify stores have a product.json endpoint or embedded JSON.
        """
        try:
            # Method 1: Try product.json endpoint
            current_url = page.url
            if "/products/" in current_url:
                json_url = current_url.split('?')[0] + '.json'
                
                try:
                    response = await page.goto(json_url, timeout=5000)
                    if response and response.ok:
                        json_data = await response.json()
                        return json_data.get("product", {})
                except:
                    pass
            
            # Method 2: Look for embedded JSON in script tags
            script_content = await page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script[type="application/json"]');
                    for (let script of scripts) {
                        const content = script.textContent;
                        if (content.includes('product') || content.includes('variants')) {
                            return content;
                        }
                    }
                    return null;
                }
            """)
            
            if script_content:
                data = json.loads(script_content)
                if "product" in data:
                    return data["product"]
                return data
            
        except Exception as e:
            print(f"⚠️ Shopify JSON extraction error: {e}")
        
        return None
    
    def _fallback_variants(self) -> Dict[str, Any]:
        """Fallback variant data when extraction fails"""
        return {
            "sizes": [
                {"size": "S", "available": True},
                {"size": "M", "available": True},
                {"size": "L", "available": True},
                {"size": "XL", "available": True}
            ],
            "colors": [],
            "variant_data": [],
            "base_price": "Price TBD",
            "available": True,
            "extraction_failed": True
        }
    
    def build_cart_url(self, product_url: str, variant_id: Optional[str] = None, 
                       quantity: int = 1) -> str:
        """
        Build a Shopify cart URL for adding products.
        
        Format: https://store.com/cart/add?id=VARIANT_ID&quantity=1
        """
        
        if not variant_id:
            # If no variant ID, return product page URL
            return product_url
        
        # Extract base domain from product URL
        from urllib.parse import urlparse
        parsed = urlparse(product_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Build cart add URL
        cart_url = f"{base_url}/cart/add?id={variant_id}&quantity={quantity}"
        
        return cart_url


# Convenience function for single product variant extraction
async def get_product_variants(product_url: str) -> Dict[str, Any]:
    """Quick function to get variants for a single product"""
    extractor = VariantExtractor()
    return await extractor.extract_variants(product_url)


# Batch variant extraction
async def get_multiple_product_variants(product_urls: List[str]) -> List[Dict[str, Any]]:
    """Extract variants for multiple products in parallel"""
    extractor = VariantExtractor()
    
    tasks = [extractor.extract_variants(url) for url in product_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out errors
    valid_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"❌ Error extracting variants from {product_urls[i]}: {result}")
            valid_results.append(extractor._fallback_variants())
        else:
            valid_results.append(result)
    
    return valid_results