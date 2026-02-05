from pydantic import BaseModel, Field
from typing import List, Optional

class Hotel(BaseModel):
    id: int
    name: str
    location: str
    price: float
    rating: float
    amenities: List[str]
    description: str

class UserPreference(BaseModel):
    location: Optional[str] = None
    min_price: float = 0
    max_price: float = 10000
    required_amenities: List[str] = []
    trip_description: Optional[str] = None

class RecommendationResponse(BaseModel):
    hotel: Hotel
    score: float
    reasoning: str

class BookingRequest(BaseModel):
    hotel_id: int
    user_email: str
    guest_name: str
