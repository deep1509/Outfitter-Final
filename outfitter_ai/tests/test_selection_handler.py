"""
Test the Selection Handler independently
"""

import sys
from datetime import datetime
from agents.conversation_agents.selectionHandler import SelectionHandler


def create_mock_products():
    """Create mock products for testing"""
    return [
        {
            "name": "Black Hoodie Classic",
            "price": "$68.00",
            "brand": "Universal Store",
            "url": "https://universalstore.com/products/black-hoodie",
            "image_url": "https://example.com/image1.jpg",
            "store_name": "Universal Store",
            "is_on_sale": False
        },
        {
            "name": "Red Nike Hoodie",
            "price": "$89.00",
            "brand": "CultureKings",
            "url": "https://culturekings.com.au/products/red-nike-hoodie",
            "image_url": "https://example.com/image2.jpg",
            "store_name": "CultureKings",
            "is_on_sale": True
        },
        {
            "name": "Grey Pullover",
            "price": "$75.00",
            "brand": "Universal Store",
            "url": "https://universalstore.com/products/grey-pullover",
            "image_url": "https://example.com/image3.jpg",
            "store_name": "Universal Store",
            "is_on_sale": False
        }
    ]


def create_mock_state(user_message, products=None):
    """Create mock state for testing"""
    if products is None:
        products = create_mock_products()
    
    return {
        "messages": [
            {"role": "user", "content": user_message}
        ],
        "products_shown": products,
        "conversation_stage": "presenting",
        "awaiting_selection": True
    }


def test_selection(test_name, user_input, expected_count=None):
    """Test a single selection scenario"""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    print(f"User says: '{user_input}'")
    print("-" * 70)
    
    handler = SelectionHandler()
    state = create_mock_state(user_input)
    
    result = handler.handle_selection(state)
    
    selected = result.get("selected_products", [])
    message = result.get("messages", [{}])[0].get("content", "")
    
    print(f"✓ Selected {len(selected)} products")
    
    if expected_count is not None:
        if len(selected) == expected_count:
            print(f"✅ PASS: Expected {expected_count}, got {len(selected)}")
        else:
            print(f"❌ FAIL: Expected {expected_count}, got {len(selected)}")
            return False
    
    if selected:
        print("\nSelected products:")
        for i, product in enumerate(selected, 1):
            print(f"  {i}. {product['name']} - {product['price']}")
            print(f"     Size: {product.get('selected_size', 'N/A')}")
    
    print(f"\nAssistant response (first 200 chars):")
    print(f"{message[:200]}...")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("SELECTION HANDLER TEST SUITE")
    print("="*70)
    
    tests = [
        ("Single number selection", "I want #2", 1),
        ("Multiple numbers", "I like #1 and #3", 2),
        ("Numbered list", "add 1, 2, and 3", 3),
        ("Ordinal reference", "I'll take the first one", 1),
        ("Natural language", "I like the red hoodie", 1),
        ("Just a number", "2", 1),
        ("Multiple with 'and'", "show me 1 and 2", 2),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, user_input, expected_count in tests:
        try:
            if test_selection(test_name, user_input, expected_count):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)