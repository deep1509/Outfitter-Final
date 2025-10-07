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
    UPDATED: Added cart management fields
    """
    # Core conversation
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User intent and context
    current_intent: Optional[str]
    
    # Shopping criteria extracted from user
    search_criteria: Dict[str, Any]
    
    # Products and selections
    search_results: List[Dict[str, Any]]
    selected_products: List[Dict[str, Any]]  # MAIN CART - persists across turns
    products_shown: List[Dict[str, Any]]
    
    # Cart-specific fields (ADD THESE)
    pending_cart_additions: Optional[List[Dict[str, Any]]]  # Items waiting to be added
    cart_operation: Optional[str]  # "add", "remove", "view", "clear"
    cart_removal_indices: Optional[List[int]]  # Indices to remove from cart
    
    # Conversation flow control
    next_step: Optional[str]
    needs_clarification: Optional[bool]
    
    # Selection and cart flags
    awaiting_selection: Optional[bool]
    awaiting_cart_action: Optional[bool]
    
    # Session context
    conversation_stage: Optional[str]
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


# ============================================================================
# EXAMPLE STATE EVOLUTION WITH CART
# ============================================================================

"""
INITIAL STATE (Empty Cart):
{
    "messages": [...],
    "selected_products": [],
    "conversation_stage": "greeting"
}

AFTER FIRST SELECTION:
{
    "messages": [...],
    "products_shown": [product1, product2, product3],
    "pending_cart_additions": [product2],  # User selected #2
    "selected_products": [],  # Not yet in cart
    "next_step": "cart_manager"
}

AFTER CART_MANAGER PROCESSES:
{
    "messages": [...],
    "products_shown": [product1, product2, product3],
    "pending_cart_additions": [],  # Cleared after processing
    "selected_products": [product2],  # NOW in cart
    "conversation_stage": "cart",
    "awaiting_cart_action": True
}

AFTER USER ASKS QUESTION (Cart Persists):
{
    "messages": [...user question, assistant answer...],
    "products_shown": [product1, product2, product3],
    "selected_products": [product2],  # CART STILL HAS PRODUCT2
    "conversation_stage": "cart"
}

AFTER USER ADDS ANOTHER ITEM:
{
    "messages": [...],
    "products_shown": [product1, product2, product3],
    "pending_cart_additions": [product3],  # User selected #3
    "selected_products": [product2],  # Existing cart unchanged yet
    "next_step": "cart_manager"
}

AFTER CART_MANAGER MERGES:
{
    "messages": [...],
    "pending_cart_additions": [],
    "selected_products": [product2, product3],  # BOTH products now in cart
    "conversation_stage": "cart"
}
"""