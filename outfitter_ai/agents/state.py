"""
State management for Outfitter.ai shopping assistant
Enhanced for Stage 3: Selection & Cart Management
"""

from typing import Annotated, List, Dict, Any, Optional, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel
from datetime import datetime
from dataclasses import dataclass


class OutfitterState(TypedDict):
    """
    Core state for Outfitter.ai shopping assistant conversation.
    Stage 3: Added selection and cart management fields.
    """
    # Core conversation
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User intent and context
    current_intent: Optional[str]  # greeting, search, selection, checkout, general
    
    # Shopping criteria extracted from user
    search_criteria: Dict[str, Any]  # category, size, color, budget, etc.
    
    # Products and selections - UPDATED for Stage 3
    search_results: List[Dict[str, Any]]  # products from scraping
    selected_products: List[Dict[str, Any]]  # items in user's cart
    products_shown: List[Dict[str, Any]]  # products currently displayed to user
    
    # Conversation flow control
    next_step: Optional[str]  # which node to execute next
    needs_clarification: Optional[bool]  # whether we need more info from user
    
    # Selection and cart flags - NEW for Stage 3
    awaiting_selection: Optional[bool]  # waiting for user to select products
    awaiting_cart_action: Optional[bool]  # waiting for cart action (checkout, add more, etc.)
    
    # Session context
    conversation_stage: Optional[str]  # greeting, discovery, presenting, selecting, cart, checkout
    session_id: Optional[str]
    created_at: Optional[str]


@dataclass
class ProductData:
    """Individual product data from scraping"""
    name: str
    price: str
    brand: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    store_name: str = ""
    is_on_sale: bool = False
    extracted_at: Optional[datetime] = None


class SearchCriteria(BaseModel):
    """Structure for user shopping needs"""
    category: Optional[str] = None  # "shirts", "pants", "shoes", "hoodies"
    size: Optional[str] = None  # "M", "Large", "32"
    color_preference: Optional[str] = None  # "black", "blue", "red"
    budget_max: Optional[float] = None  # 100.0
    style_preference: Optional[str] = None  # "casual", "formal", "streetwear"
    brand_preference: Optional[str] = None  # "Nike", "Adidas", "Champion"
    gender: Optional[str] = None  # "mens", "womens", "unisex"


class SelectedProduct(BaseModel):
    """
    Structure for a product that user has selected for cart.
    Stage 3: Simplified without complex variant extraction.
    """
    name: str
    price: str
    brand: str
    store_name: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    
    # Simplified variant info
    selected_size: str = "M"  # Default to Medium
    selected_variant: str = "default"  # Simplified - not extracting complex variants
    quantity: int = 1
    
    # Metadata
    added_at: Optional[str] = None


# Example of how state evolves through the conversation:

"""
STAGE 1 - Greeting:
{
    "messages": [...],
    "conversation_stage": "greeting",
    "next_step": "wait_for_user"
}

STAGE 2 - Discovery & Search:
{
    "messages": [...],
    "search_criteria": {"category": "hoodies", "color_preference": "black"},
    "conversation_stage": "discovery",
    "next_step": "parallel_searcher"
}

STAGE 3 - Presenting Products:
{
    "messages": [...],
    "search_results": [product1, product2, ...],
    "products_shown": [product1, product2, ...],  # NEW
    "awaiting_selection": True,  # NEW
    "conversation_stage": "presenting",
    "next_step": "wait_for_user"
}

STAGE 4 - Selection Made:
{
    "messages": [...],
    "products_shown": [product1, product2, ...],
    "selected_products": [product2],  # User selected #2
    "awaiting_cart_action": True,  # NEW
    "conversation_stage": "cart",
    "next_step": "cart_manager"
}

STAGE 5 - Checkout:
{
    "messages": [...],
    "selected_products": [product2, product5],
    "conversation_stage": "checkout",
    "next_step": "checkout_handler"
}
"""