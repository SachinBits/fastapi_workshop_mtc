from fastapi import FastAPI, Query, Depends, HTTPException, Header, Request, Body, Path, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import time
import asyncio
from typing import List, Optional
from models import Hotel, UserPreference, RecommendationResponse, BookingRequest
from db import get_all_hotels, supabase
from logic import filter_hotels, calculate_recommendation_score, generate_recommendation_reason, rerank_hotels

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Hotel Recommendation API",
    description="A simple API to recommend hotels based on user preferences.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware: Process Time
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    # Avoid adding header if response is already closed/errored
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Mount frontend
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Hotel Recommendation API! Visit /app to see the UI."}

# --- Dependencies ---
def pagination_parameters(
    skip: int = Query(0, description="Items to skip", ge=0),
    limit: int = Query(10, description="Items to return", le=100)
):
    return {"skip": skip, "limit": limit}

def verify_token(x_token: str = Header(...)):
    if x_token != "secret-token":
        raise HTTPException(status_code=400, detail="Invalid X-Token header")
    return x_token

# --- Core Endpoints ---

@app.get("/hotels", response_model=List[Hotel])
def search_hotels(
    location: Optional[str] = Query(None),
    min_price: float = Query(0),
    max_price: float = Query(10000),
    amenities: Optional[List[str]] = Query(None),
    pagination: dict = Depends(pagination_parameters)
):
    all_hotels = get_all_hotels()
    filtered = filter_hotels(all_hotels, location, min_price, max_price, amenities or [])
    
    start = pagination["skip"]
    end = start + pagination["limit"]
    return filtered[start:end]

@app.post("/recommendations", response_model=List[RecommendationResponse])
def get_recommendations(user_pref: UserPreference):
    all_hotels = get_all_hotels()
    filtered = filter_hotels(
        all_hotels,
        location=user_pref.location,
        min_price=user_pref.min_price,
        max_price=user_pref.max_price,
        amenities=user_pref.required_amenities
    )
    
    # AI Reranking if description provided
    if user_pref.trip_description:
        initial_scored = []
        for hotel in filtered:
             score = calculate_recommendation_score(hotel, user_pref)
             initial_scored.append((hotel, score))
        
        initial_scored.sort(key=lambda x: x[1], reverse=True)
        top_candidates = [x[0] for x in initial_scored[:5]]
        
        reranked = rerank_hotels(top_candidates, user_pref)
        if reranked:
             return [RecommendationResponse(**r) for r in reranked]

    # Fallback
    recommendations = []
    for hotel in filtered:
        score = calculate_recommendation_score(hotel, user_pref)
        reason = generate_recommendation_reason(hotel, user_pref, score)
        recommendations.append(RecommendationResponse(hotel=hotel, score=score, reasoning=reason))
    
    recommendations.sort(key=lambda x: x.score, reverse=True)
    return recommendations

# --- Admin Endpoints (New Use Case) ---

@app.post("/admin/hotels", status_code=201)
def create_hotel(hotel: Hotel, token: str = Depends(verify_token)):
    """
    Admin: Add a new hotel.
    """
    if not supabase:
         raise HTTPException(status_code=503, detail="Database unavailable")
    
    try:
        data = hotel.dict()
        response = supabase.table("hotels").insert(data).execute()
        return {"message": "Hotel created successfully", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/admin/hotels/{hotel_id}")
def delete_hotel(hotel_id: int, token: str = Depends(verify_token)):
    """
    Admin: Delete a hotel by ID.
    """
    if not supabase:
         raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        response = supabase.table("hotels").delete().eq("id", hotel_id).execute()
        return {"message": f"Hotel {hotel_id} deleted", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/admin/hotels/{hotel_id}")
def update_hotel_price(hotel_id: int, price: float = Body(...), token: str = Depends(verify_token)):
    """
    Admin: Update a hotel's price.
    """
    if not supabase:
         raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        response = supabase.table("hotels").update({"price": price}).eq("id", hotel_id).execute()
        return {"message": f"Hotel {hotel_id} price updated to {price}", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Booking System ---

def send_confirmation_email(email: str, hotel_name: str):
    time.sleep(2)
    print(f"📧 EMAIL SENT to {email}: Booking confirmed for {hotel_name}!")

@app.post("/bookings")
async def create_booking(
    booking: BookingRequest, 
    background_tasks: BackgroundTasks, 
    token: str = Depends(verify_token)
):
    background_tasks.add_task(send_confirmation_email, booking.user_email, str(booking.hotel_id))
    return {
        "status": "confirmed", 
        "message": "Booking received! Confirmation email will be sent shortly.",
        "user": booking.guest_name
    }
