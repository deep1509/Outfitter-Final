"""
CultureKings category URL mappings
"""

CULTUREKINGS_CATEGORIES = {
    # Hoodies & Sweatshirts
    "hoodie": "https://www.culturekings.com.au/collections/mens-hoodies",
    "hoodies": "https://www.culturekings.com.au/collections/mens-hoodies",
    "sweatshirt": "https://www.culturekings.com.au/collections/mens-hoodies",
    
    # T-Shirts & Tops
    "tshirt": "https://www.culturekings.com.au/collections/mens-tops-ss-tees",
    "t-shirt": "https://www.culturekings.com.au/collections/mens-tops-ss-tees",
    "tee": "https://www.culturekings.com.au/collections/mens-tops-ss-tees",
    "shirt": "https://www.culturekings.com.au/collections/mens-tops-button-up",
    "top": "https://www.culturekings.com.au/collections/mens-tops",
    
    # Pants & Jeans
    "jean": "https://www.culturekings.com.au/collections/mens-bottoms-jeans",
    "jeans": "https://www.culturekings.com.au/collections/mens-bottoms-jeans",
    "pant": "https://www.culturekings.com.au/collections/mens-bottoms-pants",
    "pants": "https://www.culturekings.com.au/collections/mens-bottoms-pants",
    "trouser": "https://www.culturekings.com.au/collections/mens-bottoms-pants",
    
    # Shorts
    "short": "https://www.culturekings.com.au/collections/mens-bottoms-shorts",
    "shorts": "https://www.culturekings.com.au/collections/mens-bottoms-shorts",
    
    # Jackets
    "jacket": "https://www.culturekings.com.au/collections/mens-tops-jacket",
    "coat": "https://www.culturekings.com.au/collections/outerwear-jackets",
    
    # Shoes
    "shoe": "https://www.culturekings.com.au/collections/mens-footwear",
    "shoes": "https://www.culturekings.com.au/collections/mens-footwear",
    "sneaker": "https://www.culturekings.com.au/collections/mens-footwear",
    "sneakers": "https://www.culturekings.com.au/collections/mens-footwear",
    
    # Headwear
    "hat": "https://www.culturekings.com.au/collections/mens-headwear",
    "cap": "https://www.culturekings.com.au/collections/mens-headwear",
}

def get_culturekings_url(query: str) -> str:
    """Map query to CultureKings category URL"""
    query_lower = query.lower()
    
    for keyword, url in CULTUREKINGS_CATEGORIES.items():
        if keyword in query_lower:
            return url
    
    # Fallback to mens collection
    return "https://www.culturekings.com.au/collections/mens-new-arrivals"