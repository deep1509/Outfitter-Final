"""
Google Custom Search Scraper
Integrates with Google Custom Search API to find products from any store in Australia.
"""

import os
import re
import json
import time
import tldextract
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

# =========================
# Config
# =========================
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
CX = os.getenv("GOOGLE_CSE_CX")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

TIMEOUT = 20
REQUEST_DELAY_SEC = 0.7         # polite delay between product-page requests
API_REQUEST_DELAY_SEC = 0.3     # tiny delay between API retries
MAX_API_RETRIES = 2             # simple retry for transient errors

# =========================
# Utilities
# =========================
def _clean_text(s: str | None) -> str | None:
    if not s:
        return None
    return re.sub(r"\s+", " ", s).strip()

def _find_first_price_like(text: str) -> str | None:
    # matches $, A$, £, €, with optional decimals and thousands sep
    m = re.search(r"(?:A\$|USD?\$|£|€)?\s?\d[\d,]*(?:\.\d{2})?", text)
    return m.group(0).strip() if m else None

def _get_soup(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code >= 400:
            return None
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException:
        return None

def _guess_store_name(url: str, soup: BeautifulSoup | None) -> str | None:
    if soup:
        og_site = soup.find("meta", attrs={"property": "og:site_name"})
        if og_site and og_site.get("content"):
            return og_site["content"].strip()
        app_name = soup.find("meta", attrs={"name": "application-name"})
        if app_name and app_name.get("content"):
            return app_name["content"].strip()
    ext = tldextract.extract(url)
    store = ext.domain
    return store.capitalize() if store else None

# =========================
# Google Custom Search (Images)
# =========================
def google_image_search(query: str, num: int = 10, start: int = 1) -> List[Dict[str, Any]]:
    """
    Calls the official Google Custom Search JSON API for image results.
    Returns a list of dicts with api_title, api_image_url, product_url.
    Includes robust error printouts for debugging (403s etc.).
    """
    if not API_KEY or not CX:
        raise RuntimeError("Missing GOOGLE_API_KEY or GOOGLE_CSE_CX in .env")

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": API_KEY,
        "cx": CX,
        "q": query,
        "searchType": "image",
        "num": max(1, min(num, 10)),
        "start": max(1, min(start, 91)),
        "safe": "active",
        "gl": "au",   # geo-bias to AU (optional)
        "hl": "en",   # language (optional)
    }

    last_err_text = None
    for attempt in range(1, MAX_API_RETRIES + 2):  # e.g., 1 try + 2 retries
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT)
            if not r.ok:
                # ---- Detailed diagnostics (this is what you asked to add) ----
                print("\n[Google CSE API] HTTP", r.status_code)
                try:
                    print("[Google CSE API] ERROR BODY:", r.json())
                except Exception:
                    print("[Google CSE API] ERROR BODY (raw):", r.text)
                last_err_text = r.text
                # Common causes of 403:
                # - Key is restricted by HTTP referrers/IP/app type
                # - API not enabled on this project
                # - Daily quota exceeded
                # - CX not set to 'Search the entire web' or Image search disabled
                time.sleep(API_REQUEST_DELAY_SEC)
                r.raise_for_status()
            data = r.json()
            results = []
            for item in data.get("items", []):
                img = item.get("image", {}) or {}
                results.append({
                    "api_title": item.get("title"),
                    "api_image_url": item.get("link"),
                    "product_url": img.get("contextLink") or item.get("link"),
                })
            return results
        except requests.HTTPError:
            if attempt <= MAX_API_RETRIES:
                time.sleep(API_REQUEST_DELAY_SEC * attempt)
                continue
            # After retries, bubble up with context
            raise
        except requests.RequestException as e:
            if attempt <= MAX_API_RETRIES:
                time.sleep(API_REQUEST_DELAY_SEC * attempt)
                continue
            raise RuntimeError(f"Network error calling Custom Search API: {e}\n{last_err_text or ''}")

# =========================
# Product Page Extraction
# =========================
def _parse_ld_json_products(soup: BeautifulSoup) -> Optional[Dict]:
    """Return best schema.org Product object from JSON-LD if available."""
    products = []
    if not soup:
        return None
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string) if tag.string else None
        except Exception:
            continue
        if not data:
            continue
        objs = data if isinstance(data, list) else [data]
        for obj in objs:
            types = obj.get("@type")
            if not types:
                continue
            if (isinstance(types, str) and types.lower() == "product") or \
               (isinstance(types, list) and any((isinstance(t, str) and t.lower() == "product") for t in types)):
                products.append(obj)
    return products[0] if products else None

def _extract_from_product_ld(product_ld: dict) -> Dict[str, Any]:
    """Extract name, brand, price, image_url, url from JSON-LD Product."""
    name = product_ld.get("name")
    # image can be a list or string
    img_val = product_ld.get("image")
    if isinstance(img_val, list) and img_val:
        image_url = img_val[0]
    elif isinstance(img_val, str):
        image_url = img_val
    else:
        image_url = None

    brand = None
    b = product_ld.get("brand")
    if isinstance(b, dict):
        brand = b.get("name") or b.get("@id") or b.get("brand")
    elif isinstance(b, str):
        brand = b

    price = None
    offers = product_ld.get("offers")
    if isinstance(offers, dict):
        price = offers.get("price") or (offers.get("priceSpecification", {}) or {}).get("price")
    elif isinstance(offers, list):
        for off in offers:
            if isinstance(off, dict):
                price = off.get("price") or (off.get("priceSpecification", {}) or {}).get("price")
                if price:
                    break

    url = product_ld.get("url")

    return {
        "name": _clean_text(name),
        "brand": _clean_text(brand),
        "price": _clean_text(str(price)) if price is not None else None,
        "image_url": _clean_text(image_url),
        "url": _clean_text(url),
    }

def _extract_fallbacks(url: str, soup: BeautifulSoup | None) -> Dict[str, Any]:
    """Fallback extraction using generic HTML signals."""
    title = None
    image_url = None
    price = None
    brand = None

    if soup:
        if soup.title and soup.title.string:
            title = _clean_text(soup.title.string)

        og_img = soup.find("meta", attrs={"property": "og:image"})
        if og_img and og_img.get("content"):
            image_url = _clean_text(og_img["content"])

        brand_meta = soup.find("meta", attrs={"name": "brand"})
        if brand_meta and brand_meta.get("content"):
            brand = _clean_text(brand_meta["content"])

        # Candidates for visible price
        candidates = [
            *soup.select("meta[itemprop='price']"),
            *soup.select("[itemprop='price']"),
            *soup.select("span.price, div.price, p.price"),
            *soup.select("[class*=price], [id*=price]"),
        ]
        for el in candidates:
            txt = el.get("content") or el.get_text(" ", strip=True)
            if not txt:
                continue
            p = _find_first_price_like(txt)
            if p:
                price = p
                break

    return {
        "name": title,
        "brand": brand,
        "price": price,
        "image_url": image_url,
        "url": url,
    }

def _merge(primary: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k in ("name", "price", "brand", "image_url", "url"):
        out[k] = primary.get(k) or fallback.get(k)
    return out

def _enrich_one(product_url: str, api_title: str | None, api_image_url: str | None) -> Dict[str, Any]:
    soup = _get_soup(product_url)
    product_ld = _parse_ld_json_products(soup)
    from_ld = _extract_from_product_ld(product_ld) if product_ld else {}
    fallbacks = _extract_fallbacks(product_url, soup)
    merged = _merge(from_ld, fallbacks)

    if not merged.get("url"):
        merged["url"] = product_url
    if not merged.get("image_url") and api_image_url:
        merged["image_url"] = api_image_url
    if not merged.get("name") and api_title:
        merged["name"] = api_title

    merged["store_name"] = _guess_store_name(product_url, soup)
    merged["extracted_at"] = datetime.now(timezone.utc).isoformat()

    # Normalize some price notations
    if merged.get("price"):
        merged["price"] = merged["price"].replace("USD$", "$").replace("US$", "$")

    return merged

# =========================
# Main Scraper Function
# =========================
def scrape_products_from_google_images(query: str, num: int = 5, start: int = 1) -> List[Dict[str, Any]]:
    """
    Main function to scrape products using Google Custom Search.
    
    Args:
        query: Search query (should include "australia" for geo-targeting)
        num: Number of results to return (max 10)
        start: Starting index for pagination
    
    Returns:
        List of product dictionaries with name, price, brand, image_url, url, store_name
    """
    # Ensure query includes Australia for geo-targeting
    if "australia" not in query.lower():
        query = f"{query} australia"
    
    print(f"🔍 Searching Google for: '{query}'")
    
    image_results = google_image_search(query, num=num, start=start)
    out = []
    
    for i, item in enumerate(image_results, 1):
        url = item.get("product_url")
        if not url:
            continue
            
        print(f"   📦 Processing item {i}/{len(image_results)}: {url[:50]}...")
        
        try:
            rec = _enrich_one(url, item.get("api_title"), item.get("api_image_url"))
            if rec.get("name"):  # Only add if we got a valid product
                out.append(rec)
                print(f"      ✅ Found: {rec.get('name', 'Unknown')} - {rec.get('price', 'N/A')}")
            else:
                print(f"      ❌ No valid product data extracted")
        except Exception as e:
            print(f"      ❌ Error processing: {e}")
        
        time.sleep(REQUEST_DELAY_SEC)
    
    print(f"🎯 Successfully scraped {len(out)} products")
    return out

# =========================
# Integration Helper
# =========================
def format_for_outfitter(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format scraped products to match Outfitter.ai's expected format.
    """
    formatted = []
    for product in products:
        formatted.append({
            "name": product.get("name", "Unknown Product"),
            "price": product.get("price", "Price not available"),
            "brand": product.get("brand", "Unknown Brand"),
            "store_name": product.get("store_name", "Unknown Store"),
            "url": product.get("url", ""),
            "image_url": product.get("image_url", ""),
            "is_on_sale": False,  # Could be enhanced to detect sales
            "extracted_at": product.get("extracted_at", datetime.now(timezone.utc).isoformat()),
            "selected_variant": "default",
            "selected_size": "M"
        })
    return formatted

# =========================
# CLI Test
# =========================
if __name__ == "__main__":
    # Test the scraper
    query = "blue denim jacket men australia"
    try:
        results = scrape_products_from_google_images(query, num=5)
        print(f"\n📊 Results ({len(results)} products):")
        for i, product in enumerate(results, 1):
            print(f"{i}. {product.get('name', 'Unknown')} - {product.get('price', 'N/A')} ({product.get('store_name', 'Unknown Store')})")
        
        # Save to file
        out_path = "google_search_results.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Saved {len(results)} items to {out_path}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(
            "\nTroubleshooting tips:\n"
            "- If you saw a 403 with an error body above:\n"
            "  * Credentials → API key: remove HTTP referrer restriction for server-side use, or use IP restriction to your public IP.\n"
            "  * Ensure 'Custom Search API' is ENABLED for this key's project.\n"
            "  * In Programmable Search Engine (cx): 'Search the entire web' ON and 'Image search' ON.\n"
            "  * Check quota/billing if you exceeded 100 free queries/day.\n"
        )
