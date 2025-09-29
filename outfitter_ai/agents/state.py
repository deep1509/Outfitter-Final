# Annotated, List, Dict, Any, Optional, Literal: Python type hints for better code safety
# TypedDict: Creates a dictionary with predefined structure and types
# add_messages: Special LangGraph function that merges message lists intelligently
# BaseMessage: LangChain's base class for all conversation messages
# BaseModel: Pydantic's base class for data validation
# datetime: For timestamps

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
    Keeps track of messages, user needs, and conversation flow.
    """
    # Core conversation
    # Stores the entire conversation history
    # Annotated tells LangGraph how to handle this field
    # add_messages is a special reducer function
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User intent and context
    # Helps route to correct agent
    # Optional[str] means it can be None initially
    current_intent: Optional[str]  # greeting, search, selection, checkout, general
    
    # Shopping criteria extracted from user
    search_criteria: Dict[str, Any]  # category, size, color, budget, etc.
    
    # Products and selections
    search_results: List[Dict[str, Any]]  # products from scraping
    selected_products: List[Dict[str, Any]]  # user selections
    
    # Conversation flow control
    next_step: Optional[str]  # which node to execute next
    needs_clarification: bool  # whether we need more info from user
    
    # Session context
    conversation_stage: str  # greeting, discovery, presenting, selecting, checkout
    session_id: str
    created_at: str

@dataclass
class ProductData:
    """Individual product data"""
    name: str
    price: str
    brand: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    store_name: str = ""
    is_on_sale: bool = False
    extracted_at: Optional[datetime] = None

class SearchCriteria(BaseModel):
    """Structure for user shopping needs in Outfitter.ai"""
    category: Optional[str] = None  # "shirts", "pants", "shoes"
    size: Optional[str] = None  # "M", "Large", "32"
    color_preference: Optional[str] = None  # "black", "blue"
    budget_max: Optional[float] = None  # 100.0
    style_preference: Optional[str] = None  # "casual", "formal"
    brand_preference: Optional[str] = None  # "Nike", "Adidas"