# 🏨 Smart Hotel Recommendation API - Workshop Script

This is your **complete guide** for the workshop. It contains **every single line of code** you need. Follow the steps sequentially.

---

## **Part 1: Setup & Initialization**

### 1.1 Create Project Structure
Run these commands in your terminal:
```bash
mkdir hotel_recommendation
cd hotel_recommendation
python3 -m venv .venv
# Activate Virtual Environment
# Mac/Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate
```

### 1.2 Install Dependencies
```bash
pip install fastapi uvicorn pydantic python-dotenv google-generativeai supabase
```

### 1.3 Configure Environment (`.env`)
Create a file named `.env` in the root folder and paste this:
```env
GEMINI_API_KEY=your_gemini_key_here
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here
```

---

## **Part 2: Data & Models**

### 2.1 File: `models.py`
This defines the structure of our data.

```python
from pydantic import BaseModel, Field
from typing import List, Optional

# Defines the shape of a single Hotel object
class Hotel(BaseModel):
    id: int                     # Unique identifier
    name: str                   # Name of the hotel
    location: str               # City/Area
    price: float                # Nightly rate
    rating: float               # 0.0 to 5.0
    amenities: List[str]        # List like ["WiFi", "Pool"]
    description: str            # Short bio for AI analysis

# Defines what users can search for
class UserPreference(BaseModel):
    location: Optional[str] = None  # Optional: User might just want "anywhere"
    min_price: float = 0            # Default to 0
    max_price: float = 10000        # Default to high number
    required_amenities: List[str] = [] # Empty list by default
    trip_description: Optional[str] = None # For AI ranking (e.g. "romantic trip")

# What the API sends back to the frontend
class RecommendationResponse(BaseModel):
    hotel: Hotel    # Nested model: The full hotel details
    score: float    # 0-100 match score
    reasoning: str  # AI or rule-based explanation

# Incoming data for a booking
class BookingRequest(BaseModel):
    hotel_id: int
    user_email: str
    guest_name: str
```

### 2.2 File: `db.py`
This handles the connection to Supabase.

```python
import os
from typing import List
from dotenv import load_dotenv
from supabase import create_client, Client
from models import Hotel

# Load environment variables from .env file
load_dotenv()

# Get credentials
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Initialize Client safely (won't crash if keys are missing, just warns)
supabase: Client = None
if url and key and "your_supabase_url" not in url:
    supabase = create_client(url, key)
else:
    print("Warning: Supabase credentials not found. DB connection will fail.")

def get_all_hotels() -> List[Hotel]:
    """
    Fetch all hotels from Supabase 'hotels' table.
    """
    if not supabase:
        return []

    try:
        # SQL equivalent: SELECT * FROM hotels;
        response = supabase.table("hotels").select("*").execute()
        
        # response.data is a list of Python dictionaries
        data = response.data 
        
        # Convert list of dicts -> list of Hotel objects (Pydantic validation running here)
        return [Hotel(**hotel) for hotel in data]
    except Exception as e:
        print(f"Error fetching hotels from Supabase: {e}")
        return []
```

### 2.3 File: `seed_db.py` (One-time setup)
Run this file `python3 seed_db.py` to populate your database.

```python
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import random

load_dotenv()

# Setup Supabase client again for this script
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or "your_supabase_url" in url:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    exit(1)

supabase: Client = create_client(url, key)

# Lists for random generation
cities = [
    "New York", "London", "Miami", "Denver", "Berlin", "Paris", "Tokyo", 
    "Sydney", "Dubai", "Rome", "Barcelona", "Amsterdam", "San Francisco", 
    "Los Angeles", "Chicago", "Bangkok", "Singapore", "Istanbul"
]

adjectives = [
    "Grand", "Cozy", "Royal", "Urban", "Seaside", "Mountain", "Hidden", 
    "Luxury", "Modern", "Vintage", "Golden", "Silver", "Crystal", "Sunset", "Sunrise"
]

nouns = [
    "Plaza", "Hotel", "Inn", "Resort", "Lodge", "Retreat", "Suites", 
    "Palace", "Hostel", "Motel", "Sanctuary", "Haven", "Stay"
]

amenities_pool = [
    "WiFi", "Pool", "Gym", "Spa", "Beach Access", "Bar", "Breakfast", 
    "Parking", "Restaurant", "Room Service", "Conference Room", "Pet Friendly"
]

def generate_hotels(count=100):
    hotels = []
    use_existing_names = set()
    
    for _ in range(count):
        # Ensure unique names
        while True:
            name = f"{random.choice(adjectives)} {random.choice(nouns)}"
            if name not in use_existing_names:
                use_existing_names.add(name)
                break
        
        # create random data
        location = random.choice(cities)
        price = random.randint(50, 800)
        rating = round(random.uniform(3.0, 5.0), 1)
        
        # Pick 3 to 8 random amenities from the pool
        num_amenities = random.randint(3, 8)
        amenities = random.sample(amenities_pool, num_amenities)
        
        description = f"Experience the {name} in {location}. {random.choice(['Perfect for relaxation.', 'Ideal for business.', 'Great for families.', 'A romantic getaway.', 'Budget friendly choice.'])}"

        # Prepare dict for DB insertion
        hotels.append({
            "name": name,
            "location": location,
            "price": float(price),
            "rating": rating,
            "amenities": amenities,
            "description": description
        })
    return hotels

def seed_data():
    print("Generating 100 hotels...")
    hotels_data = generate_hotels(100)
    
    print("Seeding data to Supabase...")
    # Supabase has limits on request size, so we insert in batches of 20
    batch_size = 20
    for i in range(0, len(hotels_data), batch_size):
        batch = hotels_data[i:i+batch_size]
        try:
            data, count = supabase.table("hotels").insert(batch).execute()
            print(f"Inserted batch {i//batch_size + 1}/{len(hotels_data)//batch_size}")
        except Exception as e:
            print(f"Failed to insert batch: {e}")
            
    print("Seeding complete!")

if __name__ == "__main__":
    seed_data()
```

---

## **Part 3: Logic Module**

### 3.1 File: `logic.py`
Separating business logic from API code (`main.py`) makes the app cleaner.

```python
from typing import List, Optional
import os
import google.generativeai as genai
from models import Hotel, UserPreference

# Configure Gemini API using key from environment
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

def filter_hotels(hotels: List[Hotel], 
                 location: Optional[str] = None, 
                 min_price: float = 0, 
                 max_price: float = 10000, 
                 amenities: List[str] = []) -> List[Hotel]:
    """
    Hard filtering logic. Hides hotels that don't match criteria.
    """
    filtered_hotels = []
    
    for hotel in hotels:
        # 1. Flexible Location Check (substring match)
        if location and location.lower() not in hotel.location.lower():
            continue
            
        # 2. Price Range Check
        if not (min_price <= hotel.price <= max_price):
            continue
            
        # 3. Amenities Check (Must have ALL requested items)
        if amenities:
            hotel_amenities_lower = [a.lower() for a in hotel.amenities]
            missing_amenity = False
            for required_amenity in amenities:
                if required_amenity.lower() not in hotel_amenities_lower:
                    missing_amenity = True
                    break
            if missing_amenity:
                continue
                
        filtered_hotels.append(hotel)
        
    return filtered_hotels

def calculate_recommendation_score(hotel: Hotel, user_pref: UserPreference) -> float:
    """
    Scoring algorithm to rank filtered hotels.
    Returns 0-100.
    """
    score = 0.0
    
    # Rule 1: Budget (40% weight) - If it fits budget, give points
    if user_pref.max_price > 0:
        score += 40.0
        
    # Rule 2: Rating (30% weight) - Normalize 5 stars to 30 points
    score += (hotel.rating / 5.0) * 30.0
    
    # Rule 3: Amenities Quantity (30% weight) - More amenities = better
    amenity_count = len(hotel.amenities)
    score += min(amenity_count * 6.0, 30.0) # Cap at 5 amenities
    
    return round(score, 1)

def generate_recommendation_reason(hotel: Hotel, user_pref: UserPreference, score: float) -> str:
    """
    Generates a natural language explanation.
    Uses LLM if available, otherwise a template.
    """
    # Fallback template
    fallback_reason = f"This hotel is a great match located in {hotel.location} with a rating of {hotel.rating}."
    
    if API_KEY:
        try:
            model = genai.GenerativeModel('gemini-pro')
            # Prompt Engineering: Giving context to the AI
            prompt = (
                f"Explain why '{hotel.name}' is a good recommendation for a traveler "
                f"looking for a hotel in {user_pref.location} with a budget of ${user_pref.max_price}. "
                f"The hotel costs ${hotel.price}, has a {hotel.rating} star rating. "
                f"Keep it persuasive but short (under 50 words)."
            )
            response = model.generate_content(prompt)
            if response.text:
                return response.text.replace("\n", " ").strip()
        except:
            pass # Fail silently to fallback
            
    return fallback_reason

def rerank_hotels(hotels: List[Hotel], user_pref: UserPreference) -> List[dict]:
    """
    Uses Gemini AI to re-sort the 'top 5' candidates based on free text.
    User asks for "Vibes", AI understands "Vibes".
    """
    if not user_pref.trip_description or not API_KEY:
        return []

    # Format the list of hotels into a string for the LLM to read
    candidates_text = ""
    for i, h in enumerate(hotels):
        candidates_text += f"Hotel {i}: {h.name} (${h.price}, {h.rating} stars). Amenities: {', '.join(h.amenities)}. Loc: {h.location}.\n"

    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = (
            f"User is looking for: '{user_pref.trip_description}'.\n"
            f"Here are the candidates:\n{candidates_text}\n"
            "Task: Rank these hotels from best to worst match. "
            "Return a JSON array where each object has: 'index' (int), 'score' (0-100), and 'reasoning' (max 20 words). "
            "The JSON should be the only output."
        )
        
        response = model.generate_content(prompt)
        
        # Basic JSON parsing from LLM response
        import json
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3] # Remove markdown code blocks
        
        rankings = json.loads(text)
        
        # Reconstruct the results
        results = []
        for rank in rankings:
            idx = rank.get('index')
            if idx is not None and 0 <= idx < len(hotels):
                results.append({
                    "hotel": hotels[idx],
                    "score": rank.get('score', 0),
                    "reasoning": rank.get('reasoning', "AI Recommended")
                })
        return results
    except Exception as e:
        print(f"Reranking failed: {e}")
        return []
```

---

## **Part 4: The Main Application**

### 4.1 File: `main.py`
The API entry point.

```python
# Import FastAPI and tools
from fastapi import FastAPI, Query, Depends, HTTPException, Header, Request, Body, Path, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import time
import asyncio
from typing import List, Optional

# Import our custom modules
from models import Hotel, UserPreference, RecommendationResponse, BookingRequest
from db import get_all_hotels, supabase
from logic import filter_hotels, calculate_recommendation_score, generate_recommendation_reason, rerank_hotels

load_dotenv()

# Initialize App
app = FastAPI(
    title="Hotel Recommendation API",
    description="A simple API to recommend hotels based on user preferences.",
    version="1.0.0"
)

# CORS: Allow frontend (running on browser) to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Middleware ---
# This runs on EVERY request. Good for logging/metrics.
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    # Pass request to the endpoint...
    response = await call_next(request)
    # ... calculates time after it returns
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Serve Frontend Files (HTML/JS/CSS) at /app
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Hotel Recommendation API! Visit /app to see the UI."}

# --- Reusable Dependencies ---
# Logic that can be injected into multiple endpoints

def pagination_parameters(
    # 'Query' grabs values from URL ?skip=0&limit=10
    skip: int = Query(0, description="Items to skip", ge=0),
    limit: int = Query(10, description="Items to return", le=100)
):
    return {"skip": skip, "limit": limit}

def verify_token(x_token: str = Header(...)):
    # Simple check for a specific header key
    if x_token != "secret-token":
        raise HTTPException(status_code=400, detail="Invalid X-Token header")
    return x_token

# --- Core Endpoints ---

@app.get("/hotels", response_model=List[Hotel])
def search_hotels(
    # Query parameters for filtering
    location: Optional[str] = Query(None),
    min_price: float = Query(0),
    max_price: float = Query(10000),
    amenities: Optional[List[str]] = Query(None),
    # Inject Pagination Logic
    pagination: dict = Depends(pagination_parameters)
):
    all_hotels = get_all_hotels()
    # Filter
    filtered = filter_hotels(all_hotels, location, min_price, max_price, amenities or [])
    
    # Paginate
    start = pagination["skip"]
    end = start + pagination["limit"]
    return filtered[start:end]

@app.post("/recommendations", response_model=List[RecommendationResponse])
def get_recommendations(user_pref: UserPreference):
    """
    Complex endpoint: Filters -> Scores -> Reranks (AI)
    """
    all_hotels = get_all_hotels()
    filtered = filter_hotels(
        all_hotels,
        location=user_pref.location,
        min_price=user_pref.min_price,
        max_price=user_pref.max_price,
        amenities=user_pref.required_amenities
    )
    
    # AI Reranking (Contextual) - Only if description is provided
    if user_pref.trip_description:
        # 1. Pre-score items to get top candidates to send to LLM
        initial_scored = []
        for hotel in filtered:
             score = calculate_recommendation_score(hotel, user_pref)
             initial_scored.append((hotel, score))
        
        # Sort and take Top 5
        initial_scored.sort(key=lambda x: x[1], reverse=True)
        top_candidates = [x[0] for x in initial_scored[:5]]
        
        # 2. Ask Gemini to re-order them based on meaning
        reranked = rerank_hotels(top_candidates, user_pref)
        if reranked:
             return [RecommendationResponse(**r) for r in reranked]

    # Fallback (Standard Math Scoring)
    recommendations = []
    for hotel in filtered:
        score = calculate_recommendation_score(hotel, user_pref)
        reason = generate_recommendation_reason(hotel, user_pref, score)
        recommendations.append(RecommendationResponse(hotel=hotel, score=score, reasoning=reason))
    
    recommendations.sort(key=lambda x: x.score, reverse=True)
    return recommendations

# --- Admin Endpoints ---

@app.post("/admin/hotels", status_code=201)
def create_hotel(hotel: Hotel, token: str = Depends(verify_token)):
    # Requires 'x-token' header
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
    # 'hotel_id' comes from URL path
    if not supabase:
         raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        response = supabase.table("hotels").delete().eq("id", hotel_id).execute()
        return {"message": f"Hotel {hotel_id} deleted", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/admin/hotels/{hotel_id}")
def update_hotel_price(hotel_id: int, price: float = Body(...), token: str = Depends(verify_token)):
    """Admin: Update a hotel's price."""
    if not supabase:
         raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        response = supabase.table("hotels").update({"price": price}).eq("id", hotel_id).execute()
        return {"message": f"Hotel {hotel_id} price updated to {price}", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Booking System (Async Tasks) ---

def send_confirmation_email(email: str, hotel_name: str):
    """
    Simulates a slow active (sending email).
    """
    time.sleep(2) # Fake delay
    print(f"📧 EMAIL SENT to {email}: Booking confirmed for {hotel_name}!")

@app.post("/bookings")
async def create_booking(
    booking: BookingRequest, 
    background_tasks: BackgroundTasks, # Tool to run things *after* response
    token: str = Depends(verify_token)
):
    # Schedule the task. It runs in background.
    background_tasks.add_task(send_confirmation_email, booking.user_email, str(booking.hotel_id))
    
    # Return immediately to user
    return {
        "status": "confirmed", 
        "message": "Booking received! Confirmation email will be sent shortly.",
        "user": booking.guest_name
    }
```

---

## **Part 5: Frontend**

### 5.1 File: `frontend/index.html`
Structure of the page.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DreamStay - Smart Hotel Finder</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="background-blobs">
        <div class="blob blob-1"></div>
        <div class="blob blob-2"></div>
        <div class="blob blob-3"></div>
    </div>

    <main class="container">
        <!-- Header -->
        <header class="glass-panel header">
            <h1>DreamStay <span class="accent">AI</span></h1>
            <p>Find your perfect getaway with smart recommendations.</p>
        </header>

        <!-- Search Form -->
        <section class="glass-panel search-section">
            <form id="recommendation-form" class="search-form">
                <div class="form-group">
                    <label for="location">Destination</label>
                    <input type="text" id="location" placeholder="e.g. New York, Miami" required>
                </div>
                <!-- ... other inputs ... -->
                <div class="form-group full-width">
                    <label for="trip-desc">Describe your dream trip (AI)</label>
                    <textarea id="trip-desc" rows="3" placeholder="e.g. Romantic honeymoon..."></textarea>
                </div>
                <button type="submit" class="cta-button">Find Hotels</button>
            </form>
        </section>

        <!-- Results Display -->
        <section id="results-section" class="results-section hidden">
            <div id="results-grid" class="results-grid"></div>
        </section>
    </main>
    <script src="script.js"></script>
</body>
</html>
```

### 5.2 File: `frontend/script.js`
Connecting the UI to the API.

```javascript
document.addEventListener('DOMContentLoaded', () => {
    // Select DOM elements
    const form = document.getElementById('recommendation-form');
    const resultsSection = document.getElementById('results-section');
    const resultsGrid = document.getElementById('results-grid');

    // Handle Form Submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault(); // Stop page reload

        // Gather values from inputs
        const location = document.getElementById('location').value;
        const maxPrice = document.getElementById('max-price').value;
        const tripDesc = document.getElementById('trip-desc').value;
        // Get all checked checkboxes
        const amenitiesNodes = document.querySelectorAll('input[name="amenities"]:checked');
        const amenities = Array.from(amenitiesNodes).map(node => node.value);

        // Construct JSON Payload
        const payload = {
            location: location || undefined,
            min_price: 0,
            max_price: maxPrice ? parseFloat(maxPrice) : 10000,
            required_amenities: amenities,
            trip_description: tripDesc || undefined
        };

        // UI Feedback
        resultsSection.classList.remove('hidden');
        resultsGrid.innerHTML = `<div class="glass-panel" style="text-align:center">🤖 AI is thinking...</div>`;

        try {
            // Call the API endpoint
            const response = await fetch('/recommendations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error('Failed to fetch recommendations');

            const recommendations = await response.json();
            renderResults(recommendations);

        } catch (error) {
            console.error('Error:', error);
            resultsGrid.innerHTML = `<div class="glass-panel" style="color:#ef4444;text-align:center">Something went wrong.</div>`;
        }
    });

    // Helper to draw Hotel Cards
    function renderResults(recommendations) {
        resultsGrid.innerHTML = '';
        if (recommendations.length === 0) {
            resultsGrid.innerHTML = '<div class="glass-panel">No hotels found.</div>';
            return;
        }

        recommendations.forEach((item, index) => {
            const hotel = item.hotel;
            // First item gets 'top-pick' styling
            const card = document.createElement('div');
            card.className = `hotel-card ${index === 0 ? 'top-pick' : ''}`;
            
            // Injects HTML template literals
            card.innerHTML = `
                <div class="card-header">
                    <div class="hotel-name">${hotel.name}</div>
                    <div class="hotel-price">$${hotel.price}</div>
                </div>
                <div class="hotel-location">📍 ${hotel.location} | ★ ${hotel.rating}</div>
                <div class="ai-reason"><strong>Why we picked this:</strong> ${item.reasoning}</div>
                <button class="cta-button" onclick="bookHotel(${hotel.id}, '${hotel.name}')">Book Now</button>
            `;
            resultsGrid.appendChild(card);
        });
    }

    // Connects to /bookings endpoint
    window.bookHotel = async (hotelId, hotelName) => {
        const email = prompt(`Enter your email to book ${hotelName}:`, "user@example.com");
        if (!email) return;

        try {
            const response = await fetch('/bookings', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'x-token': 'secret-token' // Auth Header
                },
                body: JSON.stringify({
                    hotel_id: hotelId,
                    user_email: email,
                    guest_name: "Workshop Guest"
                })
            });

            if (response.ok) {
                const data = await response.json();
                alert(`✅ ${data.message}`);
            } else {
                alert("❌ Booking failed!");
            }
        } catch (error) {
            alert("Error connecting to server.");
        }
    };
});
```
