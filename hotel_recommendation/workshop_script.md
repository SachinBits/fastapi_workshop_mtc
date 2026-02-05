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
# 'pydantic' is a library that enforces data types.
# Why? We want to ensure 'price' is always a number, not text like "ten dollars".
from pydantic import BaseModel, Field
from typing import List, Optional

# Defines the shape of a single Hotel object
# 'BaseModel' allows this class to automatically validate data for us.
class Hotel(BaseModel):
    id: int                     # Unique identifier
    name: str                   # Name of the hotel
    location: str               # City/Area
    price: float                # Nightly rate
    rating: float               # 0.0 to 5.0
    # List[str]: Tells Python this is a list containing ONLY strings.
    amenities: List[str]        # List like ["WiFi", "Pool"]
    description: str            # Short bio for AI analysis

# Defines what users can search for
class UserPreference(BaseModel):
    # Optional[str]: Means this field can be a String OR None (null).
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

# REQUIRED: This function abstracts the database logic.
# Why? So the rest of our app doesn't need to know we are using Supabase. 
# If we switch to SQL or Firebase later, we only change this one function.
def get_all_hotels() -> List[Hotel]:
    """
    Fetch all hotels from Supabase 'hotels' table.
    """
    if not supabase:
        return []

    try:
        # SQL equivalent: SELECT * FROM hotels;
        # .execute(): Sends the request over the internet to Supabase.
        response = supabase.table("hotels").select("*").execute()
        
        # response.data is a list of Python dictionaries (raw data)
        data = response.data 
        
        # '**hotel' (kwargs unpacking): Takes a dict like {"name": "X", "id": 1} 
        # and explodes it into arguments: Hotel(name="X", id=1).
        # We do this to convert raw data into safe, validated 'Hotel' objects.
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

# REQUIRED: Generates fake data for testing.
# Why? We need hundreds of hotels to test our filter logic, and manually typing them is too slow.
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

# REQUIRED: Orchestrates the seeding process.
# Why? It handles batching (Supabase limits size of inserts) and error handling during upload.
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

# REQUIRED: Applies hard filters.
# Why? We must filter out invalid options (wrong city, too expensive) BEFORE sending data to AI.
# This saves money (fewer AI tokens) and ensures correctness.
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

# REQUIRED: Rule-based Initial Scoring.
# Why? We need a way to sort "good" hotels to the top instantly, without waiting for slow AI.
# This gives us a baseline ranking.
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

# REQUIRED: Explains the recommendation.
# Why? Users trust recommendations more if you tell them WHY you picked it.
# We try to use AI for a custom reason, but fallback to a template if AI fails.
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
                # .strip(): Removes extra spaces/newlines from start/end of the string
                return response.text.replace("\n", " ").strip()
        except:
            pass # Fail silently to fallback
            
    return fallback_reason

# REQUIRED: Intelligent Reranking.
# Why? Standard math can't understand "romantic vibes" or "near downtown". 
# The LLM understands the semantic meaning of the user's description and re-orders the list logic missed.
def rerank_hotels(hotels: List[Hotel], user_pref: UserPreference) -> List[dict]:
    """
    Uses Gemini AI to re-sort the 'top 5' candidates based on free text.
    User asks for "Vibes", AI understands "Vibes".
    """
    if not user_pref.trip_description or not API_KEY:
        return []

    # Format the list of hotels into a single string for the LLM to read.
    # Why? The LLM needs text input. It can't read our Python 'list of objects' directly.
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
            text = text[7:-3] # Remove markdown code blocks if the AI added them
        
        # json.loads: Converts the text string back into a Python list/dictionary.
        # Why? We can't work with a text blob; we need structured data to loop over.
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
    allow_origins=["*"], # In production, replace with specific domain, '*' means allow everyone
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Middleware ---

# REQUIRED: Global Performance Timing.
# Why? This intercepts every request to calculate execution time. 
# It helps us monitor if our API is running slow.
# @app.middleware("http"): Decorator that registers this function to run on every HTTP request.
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    # 'await': Pauses this function here, waits for the request to be processed by the endpoint, then continues.
    # Why? If we didn't 'await', we wouldn't know when the request finished.
    response = await call_next(request)
    # ... calculates time after it returns
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Serve Frontend Files (HTML/JS/CSS) at /app
# 'mount': Attaches a folder of static files to a specific URL path.
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Hotel Recommendation API! Visit /app to see the UI."}

# --- Reusable Dependencies ---
# Logic that can be injected into multiple endpoints

# REQUIRED: Pagination Logic.
# Why? When we have thousands of hotels, we can't send them all. 
# This standardizes how all endpoints handle "skip" and "limit".
def pagination_parameters(
    # 'Query': Tells FastAPI to look for these values in the URL (e.g., ?skip=0&limit=10)
    skip: int = Query(0, description="Items to skip", ge=0),
    limit: int = Query(10, description="Items to return", le=100)
):
    return {"skip": skip, "limit": limit}

# REQUIRED: Authentication Dependency.
# Why? We need to protect sensitive actions (like Deleting hotels).
# This checks if the user provided the correct 'x-token'.
def verify_token(x_token: str = Header(...)):
    # Simple check for a specific header key
    if x_token != "secret-token":
        raise HTTPException(status_code=400, detail="Invalid X-Token header")
    return x_token

# --- Core Endpoints ---

# REQUIRED: Search Endpoint.
# Why? This provides a direct, filtered view of hotels without AI scoring.
# Useful for simply browsing.
@app.get("/hotels", response_model=List[Hotel])
def search_hotels(
    # Query parameters for filtering
    location: Optional[str] = Query(None),
    min_price: float = Query(0),
    max_price: float = Query(10000),
    amenities: Optional[List[str]] = Query(None),
    # Depends(): This ensures 'pagination_parameters' is called and its result is passed here.
    # Why? It keeps this function clean and reuses the logic defined above.
    pagination: dict = Depends(pagination_parameters)
):
    all_hotels = get_all_hotels()
    # Filter
    filtered = filter_hotels(all_hotels, location, min_price, max_price, amenities or [])
    
    # Paginate
    start = pagination["skip"]
    end = start + pagination["limit"]
    return filtered[start:end]

# REQUIRED: Recommendation Endpoint (The Core Feature).
# Why? This connects all our logic pieces together: 
# Filter -> Score -> Rerank with AI.
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
             # **r: Unpacks dictionary keys/values into the Pydantic model constructor
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

# REQUIRED: Create Hotel.
# Why? Allows Administrators to add new inventory to the system.
@app.post("/admin/hotels", status_code=201)
def create_hotel(hotel: Hotel, token: str = Depends(verify_token)):
    # Requires 'x-token' header
    if not supabase:
         raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        # .dict(): Converts the Pydantic 'Hotel' object into a standard Python dictionary.
        # Why? The Supabase client expects a dict for insertion, not a custom object.
        data = hotel.dict()
        response = supabase.table("hotels").insert(data).execute()
        return {"message": "Hotel created successfully", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# REQUIRED: Delete Hotel.
# Why? Allows Administrators to remove outdated or closed hotels.
@app.delete("/admin/hotels/{hotel_id}")
def delete_hotel(hotel_id: int, token: str = Depends(verify_token)):
    # 'hotel_id' comes from URL path ({hotel_id})
    if not supabase:
         raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        # .eq("id", hotel_id): Filter query == "WHERE id = hotel_id"
        response = supabase.table("hotels").delete().eq("id", hotel_id).execute()
        return {"message": f"Hotel {hotel_id} deleted", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# REQUIRED: Update Hotel.
# Why? Allows Administrators to change details (like Price) without deleting the whole hotel.
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

# REQUIRED: Simulated Email Service.
# Why? Sending real emails takes time (1-3 seconds). We put this in a separate function
# so we can run it in the "background" while the user goes on with their day.
def send_confirmation_email(email: str, hotel_name: str):
    """
    Simulates a slow active (sending email).
    """
    time.sleep(2) # Fake delay
    print(f"📧 EMAIL SENT to {email}: Booking confirmed for {hotel_name}!")

# REQUIRED: Booking Endpoint.
# Why? To capture user intent to book. It uses BackgroundTasks to handle the slow email.
@app.post("/bookings")
async def create_booking(
    booking: BookingRequest, 
    background_tasks: BackgroundTasks, # Tool to run things *after* response
    token: str = Depends(verify_token)
):
    # Schedule the task. It runs in background.
    # Why? The user gets a generic "Success" message instantly, and the heavy lifting happens later.
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
    // 'async': Marks this function as asynchronous.
    // Why? It means this function will have to wait for something (like a network request) later on.
    form.addEventListener('submit', async (e) => {
        // e.preventDefault(): Default form behavior is to reload the page.
        // Why? We want to stay on the same page and just update the results dynamically (SPA behavior).
        e.preventDefault(); 

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
            // fetch: Used to make network requests to a server.
            // await: Tells the code to PAUSE here until 'fetch' is finished.
            // Why? If we don't wait, 'response' would be empty when we try to use it.
            const response = await fetch('/recommendations', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json' 
                    // Why? We must tell the server we are sending JSON data, otherwise it might ignore the body.
                },
                // JSON.stringify(payload): Converts a JavaScript Object ({ key: value }) into a text String ("{...}").
                // Why? We can only send Text over the internet, we cannot send raw computer memory objects.
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error('Failed to fetch recommendations');

            // response.json(): Reads the stream of text from the server and turns it back into a JavaScript Object.
            // await: Again, we have to wait for the conversion to finish.
            const recommendations = await response.json();
            
            // Call our render helper
            renderResults(recommendations);

        } catch (error) {
            console.error('Error:', error);
            resultsGrid.innerHTML = `<div class="glass-panel" style="color:#ef4444;text-align:center">Something went wrong.</div>`;
        }
    });

    // REQUIRED: Convert data to HTML.
    // Why? The API returns raw JSON (data). We need to build HTML elements (divs, buttons)
    // so the user can actually see and interact with the hotels.
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

    // REQUIRED: Handle Bookings.
    // Why? When a user clicks "Book Now", we need to collect their email
    // and send a request to our /bookings API endpoint.
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

### 5.4 File: `frontend/style.css`
(Paste the CSS from the repo file `frontend/style.css` if desired, or skip for a basic view).
```css
:root {
    --bg-color: #0f172a;
    --text-color: #f8fafc;
    --accent-color: #818cf8;
    --glass-bg: rgba(255, 255, 255, 0.05);
    --glass-border: rgba(255, 255, 255, 0.1);
    --card-hover: rgba(255, 255, 255, 0.1);
    --glow: #6366f1;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: 'Outfit', sans-serif;
}

body {
    background-color: var(--bg-color);
    color: var(--text-color);
    min-height: 100vh;
    overflow-x: hidden;
    position: relative;
}

/* Background Animation */
.background-blobs {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -1;
    overflow: hidden;
}

.blob {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.4;
    animation: float 10s infinite ease-in-out;
}

.blob-1 {
    width: 400px;
    height: 400px;
    background: #4f46e5;
    top: -10%;
    left: -10%;
}

.blob-2 {
    width: 300px;
    height: 300px;
    background: #ec4899;
    bottom: -5%;
    right: -5%;
    animation-delay: 2s;
}

.blob-3 {
    width: 250px;
    height: 250px;
    background: #06b6d4;
    top: 40%;
    left: 40%;
    animation-delay: 4s;
}

@keyframes float {
    0%, 100% { transform: translate(0, 0); }
    50% { transform: translate(20px, -20px); }
}

.container {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
}

/* Glass Panel Utility */
.glass-panel {
    background: var(--glass-bg);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--glass-border);
    border-radius: 24px;
    padding: 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
}

.header {
    text-align: center;
    margin-bottom: 3rem;
}

.header h1 {
    font-size: 3rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}

.accent {
    background: linear-gradient(135deg, #818cf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.search-section h2 {
    margin-bottom: 1.5rem;
    font-weight: 600;
}

.search-form {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
}

.form-group {
    flex: 1;
    min-width: 250px;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.form-group.full-width {
    flex: 100%;
}

label {
    font-size: 0.9rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}

input {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--glass-border);
    padding: 1rem;
    border-radius: 12px;
    color: white;
    font-size: 1rem;
    transition: all 0.3s;
}

input:focus {
    outline: none;
    border-color: var(--accent-color);
    background: rgba(255, 255, 255, 0.1);
}

/* Custom Checkboxes */
.amenities-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.8rem;
}

.checkbox-btn {
    cursor: pointer;
    position: relative;
}

.checkbox-btn input {
    position: absolute;
    opacity: 0;
    cursor: pointer;
}

.checkbox-btn span {
    display: inline-block;
    padding: 0.6rem 1.2rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    font-size: 0.9rem;
    color: #cbd5e1;
    transition: all 0.3s ease;
}

.checkbox-btn input:checked + span {
    background: var(--accent-color);
    color: white;
    border-color: var(--accent-color);
    box-shadow: 0 0 15px rgba(129, 140, 248, 0.4);
}

/* CTA Button */
.cta-button {
    width: 100%;
    padding: 1.2rem;
    margin-top: 1rem;
    border: none;
    border-radius: 16px;
    background: linear-gradient(135deg, #4f46e5, #9333ea);
    color: white;
    font-size: 1.1rem;
    font-weight: 700;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s;
}

.cta-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.5);
}

.cta-button:active {
    transform: translateY(0);
}

/* Results */
.hidden {
    display: none;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
}

.badge {
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
    padding: 0.4rem 0.8rem;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.results-grid {
    display: grid;
    gap: 1.5rem;
}

.hotel-card {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    padding: 1.5rem;
    transition: all 0.3s;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    position: relative;
    overflow: hidden;
}

.hotel-card:hover {
    background: var(--card-hover);
    transform: translateX(5px);
    border-color: var(--accent-color);
}

.hotel-card.top-pick {
    border: 1px solid #facc15;
    background: linear-gradient(to right, rgba(250, 204, 21, 0.05), transparent);
}

.hotel-card.top-pick::before {
    content: '★ Top Pick';
    position: absolute;
    top: 0;
    right: 0;
    background: #facc15;
    color: #000;
    padding: 0.3rem 0.8rem;
    font-size: 0.7rem;
    font-weight: 700;
    border-bottom-left-radius: 12px;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}

.hotel-name {
    font-size: 1.4rem;
    font-weight: 700;
    color: white;
}

.hotel-location {
    color: #94a3b8;
    font-size: 0.9rem;
    margin-top: 0.2rem;
}

.hotel-price {
    font-size: 1.2rem;
    font-weight: 700;
    color: #34d399;
}

.rating-badge {
    background: rgba(255, 255, 255, 0.1);
    padding: 0.2rem 0.6rem;
    border-radius: 8px;
    font-size: 0.8rem;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
}

.amenities-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.tag {
    background: rgba(99, 102, 241, 0.2);
    border: 1px solid rgba(99, 102, 241, 0.3);
    color: #a5b4fc;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.75rem;
}

.ai-reason {
    background: rgba(0, 0, 0, 0.3);
    padding: 1rem;
    border-radius: 12px;
    font-size: 0.9rem;
    line-height: 1.5;
    color: #e2e8f0;
    border-left: 3px solid var(--accent-color);
}

.ai-reason strong {
    color: var(--accent-color);
    display: block;
    margin-bottom: 0.3rem;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

textarea {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--glass-border);
    padding: 1rem;
    border-radius: 12px;
    color: white;
    font-size: 1rem;
    width: 100%;
    resize: vertical;
    transition: all 0.3s;
}

textarea:focus {
    outline: none;
    border-color: var(--accent-color);
    background: rgba(255, 255, 255, 0.1);
}

---

## **Part 6: Running the App**
1. Run the server:
   ```bash
   uvicorn main:app --reload
   ```
2. Open browser: [http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)


