"""
Debug script to visually inspect what's happening during scraping.
Opens browser windows, takes screenshots, saves HTML, and reports findings.
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import json

async def debug_store_search(store_name: str, query: str):
    """
    Debug a single store search with visual inspection
    """
    print(f"\n{'='*70}")
    print(f"DEBUGGING: {store_name.upper()} - Query: '{query}'")
    print(f"{'='*70}\n")
    
    # Build URL based on store
    if store_name == "universalstore":
        url = f"https://www.universalstore.com/collections/mens?q={query.replace(' ', '%20')}"
    elif store_name == "culturekings":
        url = f"https://culturekings.com.au/search?q={query.replace(' ', '+')}"
    else:
        print(f"Unknown store: {store_name}")
        return
    
    print(f"URL: {url}\n")
    
    async with async_playwright() as p:
        # Launch browser - VISIBLE so you can watch
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Set viewport
        await page.set_viewport_size({'width': 1920, 'height': 1080})
        
        print("Step 1: Navigating to URL...")
        await page.goto(url, wait_until="domcontentloaded")
        print("   Page loaded")
        
        # Wait for content to render
        print("\nStep 2: Waiting 5 seconds for JavaScript to render...")
        await asyncio.sleep(5)
        
        # Take screenshot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_file = f"debug_{store_name}_{query.replace(' ', '_')}_{timestamp}.png"
        await page.screenshot(path=screenshot_file, full_page=True)
        print(f"   Screenshot saved: {screenshot_file}")
        
        # Save HTML
        html_content = await page.content()
        html_file = f"debug_{store_name}_{query.replace(' ', '_')}_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"   HTML saved: {html_file}")
        
        # Check for various product-related elements
        print("\nStep 3: Looking for product elements...")
        
        selectors_to_check = [
            ".product-card",
            ".product-item",
            "[data-product]",
            "article",
            ".grid__item",
            ".ProductHit_root__2tJkv",  # CultureKings
            "a[href*='/products/']",
            "h2", "h3",  # Product titles often in h2/h3
            ".price", "[class*='price']",
        ]
        
        findings = {}
        for selector in selectors_to_check:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    findings[selector] = count
                    print(f"   Found {count} elements: {selector}")
                    
                    # Get text from first few
                    if count > 0 and count <= 10:
                        for i in range(min(3, count)):
                            try:
                                text = await page.locator(selector).nth(i).text_content()
                                if text:
                                    text_preview = text.strip()[:100]
                                    print(f"      [{i}] {text_preview}...")
                            except:
                                pass
            except Exception as e:
                pass
        
        if not findings:
            print("   WARNING: No product elements found with common selectors!")
        
        # Check for "no results" messages
        print("\nStep 4: Checking for 'no results' messages...")
        no_results_patterns = ["no results", "no products", "nothing found", "0 results"]
        page_text = await page.text_content("body")
        page_text_lower = page_text.lower()
        
        for pattern in no_results_patterns:
            if pattern in page_text_lower:
                print(f"   FOUND: '{pattern}' in page text")
                print("   This might explain why search isn't returning products")
        
        # Check if we're on search results or somewhere else
        print("\nStep 5: Verifying page type...")
        page_url = page.url
        page_title = await page.title()
        print(f"   Current URL: {page_url}")
        print(f"   Page Title: {page_title}")
        
        if "search" not in page_url.lower() and "collection" not in page_url.lower():
            print("   WARNING: URL doesn't contain 'search' or 'collection'")
            print("   Might have been redirected")
        
        # Save findings to JSON
        report = {
            "store": store_name,
            "query": query,
            "url": url,
            "final_url": page_url,
            "page_title": page_title,
            "timestamp": timestamp,
            "elements_found": findings,
            "screenshot": screenshot_file,
            "html_file": html_file
        }
        
        report_file = f"debug_report_{store_name}_{query.replace(' ', '_')}_{timestamp}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved: {report_file}")
        
        # Keep browser open for manual inspection
        print("\n" + "="*70)
        print("BROWSER WILL STAY OPEN FOR 30 SECONDS")
        print("Inspect the page manually, then it will close automatically")
        print("="*70)
        await asyncio.sleep(30)
        
        await browser.close()

async def run_debug_suite():
    """Run debug for multiple scenarios"""
    
    scenarios = [
        ("universalstore", "red hoodies"),
        ("culturekings", "red hoodies"),
        ("universalstore", "nike"),  # Try a brand name
        ("culturekings", "hoodie"),  # Try generic term
    ]
    
    for store, query in scenarios:
        try:
            await debug_store_search(store, query)
            await asyncio.sleep(2)  # Pause between stores
        except Exception as e:
            print(f"\nERROR debugging {store} with '{query}': {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("="*70)
    print("WEB SCRAPER DEBUG TOOL")
    print("="*70)
    print("\nThis script will:")
    print("1. Open browser windows (visible)")
    print("2. Navigate to search URLs")
    print("3. Take screenshots")
    print("4. Save HTML files")
    print("5. Report findings")
    print("6. Keep browser open for 30 seconds for manual inspection")
    print("\nFiles will be saved in current directory")
    print("="*70)
    
    asyncio.run(run_debug_suite())
    
    print("\n" + "="*70)
    print("DEBUG COMPLETE")
    print("="*70)
    print("\nCheck the generated files:")
    print("- .png files (screenshots)")
    print("- .html files (page source)")
    print("- .json files (analysis reports)")