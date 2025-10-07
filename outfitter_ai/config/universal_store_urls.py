"""
Universal Store category URL mappings.
Search doesn't work via URL, so we browse categories and filter client-side.
"""

UNIVERSAL_STORE_CATEGORIES = {
    # Hoodies & Sweatshirts
    "hoodie": "https://www.universalstore.com/collections/mens-hoodies-jumpers",
    "hoodies": "https://www.universalstore.com/collections/mens-hoodies-jumpers",
    "sweatshirt": "https://www.universalstore.com/collections/mens-hoodies-jumpers",
    "jumper": "https://www.universalstore.com/collections/mens-hoodies-jumpers",
    
    # T-Shirts
    "tshirt": "https://www.universalstore.com/collections/mens-t-shirts",
    "t-shirt": "https://www.universalstore.com/collections/mens-t-shirts",
    "tee": "https://www.universalstore.com/collections/mens-t-shirts",
    "shirt": "https://www.universalstore.com/collections/mens-shirts-polos",
    
    # Pants & Jeans
    "jean": "https://www.universalstore.com/collections/mens-jeans",
    "jeans": "https://www.universalstore.com/collections/mens-jeans",
    "pant": "https://www.universalstore.com/collections/mens-pants",
    "pants": "https://www.universalstore.com/collections/mens-pants",
    "trouser": "https://www.universalstore.com/collections/mens-pants",
    
    # Shorts
    "short": "https://www.universalstore.com/collections/mens-shorts",
    "shorts": "https://www.universalstore.com/collections/mens-shorts",
    
    # Jackets
    "jacket": "https://www.universalstore.com/collections/mens-jackets-coats",
    "coat": "https://www.universalstore.com/collections/mens-jackets-coats",
    
    # Shoes
    "shoe": "https://www.universalstore.com/collections/mens-shoes",
    "shoes": "https://www.universalstore.com/collections/mens-shoes",
    "sneaker": "https://www.universalstore.com/collections/mens-sneakers",
    "sneakers": "https://www.universalstore.com/collections/mens-sneakers",
    "boot": "https://www.universalstore.com/collections/mens-boots",
    "boots": "https://www.universalstore.com/collections/mens-boots",
    "sandal": "https://www.universalstore.com/collections/mens-sandals",
    
    # Accessories
    "hat": "https://www.universalstore.com/collections/mens-hats",
    "cap": "https://www.universalstore.com/collections/mens-hats",
    "bag": "https://www.universalstore.com/collections/mens-bags",
}

def get_category_url(query: str) -> str:
    """Map a search query to a Universal Store category URL"""
    query_lower = query.lower()
    
    # Try to find matching category
    for keyword, url in UNIVERSAL_STORE_CATEGORIES.items():
        if keyword in query_lower:
            return url
    
    # Fallback to general mens clothing
    return "https://www.universalstore.com/collections/mens"