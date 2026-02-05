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
This defines the structure of our data (Pydantic models).
```python
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
```

### 2.2 File: `db.py`
This handles the connection to Supabase.
```python
import os
from typing import List
from dotenv import load_dotenv
from supabase import create_client, Client
from models import Hotel

load_dotenv()

# Initialize Supabase Client
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

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
        response = supabase.table("hotels").select("*").execute()
        # Allows for handling both object and dictionary return types from supabase-py versions
        data = response.data 
        return [Hotel(**hotel) for hotel in data]
    except Exception as e:
        print(f"Error fetching hotels from Supabase: {e}")
        return []
```

### 2.3 File: `seed_db.py` (One-time setup)
Run this file `python3 seed_db.py` to populate your database with fake hotels.
```python
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import random

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or "your_supabase_url" in url:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    exit(1)

supabase: Client = create_client(url, key)

# Procedural Generation Lists
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
        while True:
            name = f"{random.choice(adjectives)} {random.choice(nouns)}"
            if name not in use_existing_names:
                use_existing_names.add(name)
                break
        
        location = random.choice(cities)
        price = random.randint(50, 800)
        rating = round(random.uniform(3.0, 5.0), 1)
        num_amenities = random.randint(3, 8)
        amenities = random.sample(amenities_pool, num_amenities)
        description = f"Experience the {name} in {location}. {random.choice(['Perfect for relaxation.', 'Ideal for business.', 'Great for families.', 'A romantic getaway.', 'Budget friendly choice.'])}"

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
This contains filtering logic and AI integration.
```python
from typing import List, Optional
import os
import google.generativeai as genai
from models import Hotel, UserPreference

# Configure Gemini API
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

def filter_hotels(hotels: List[Hotel], 
                 location: Optional[str] = None, 
                 min_price: float = 0, 
                 max_price: float = 10000, 
                 amenities: List[str] = []) -> List[Hotel]:
    """Filters hotels based on user criteria."""
    filtered_hotels = []
    
    for hotel in hotels:
        if location and location.lower() not in hotel.location.lower():
            continue
        if not (min_price <= hotel.price <= max_price):
            continue
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
    """Calculates a match score (0-100)."""
    score = 0.0
    # Price Score (40 points)
    if user_pref.max_price > 0:
        score += 40.0
    # Rating Score (30 points)
    score += (hotel.rating / 5.0) * 30.0
    # Amenities Score (30 points)
    amenity_count = len(hotel.amenities)
    score += min(amenity_count * 6.0, 30.0)
    return round(score, 1)

def generate_recommendation_reason(hotel: Hotel, user_pref: UserPreference, score: float) -> str:
    """Generates a reason/blurb for the recommendation."""
    fallback_reason = f"This hotel is a great match located in {hotel.location} with a rating of {hotel.rating}."
    
    if API_KEY:
        try:
            model = genai.GenerativeModel('gemini-pro')
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
            pass
    return fallback_reason

def rerank_hotels(hotels: List[Hotel], user_pref: UserPreference) -> List[dict]:
    """Uses Gemini AI to rerank candidates based on 'vibes' (description)."""
    if not user_pref.trip_description or not API_KEY:
        return []

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
        import json
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        
        rankings = json.loads(text)
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
The final state of your `main.py`, including **Middleware**, **Background Tasks**, **Pagination**, and **Admin Endpoints**.
```python
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
    """Admin: Add a new hotel."""
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
    """Admin: Delete a hotel by ID."""
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
```

---

## **Part 5: Frontend (Glassmorphism UI)**

### 5.1 Create Directory
```bash
mkdir frontend
```

### 5.2 File: `frontend/index.html`
*(Can copy-paste from repo or use simple HTML structure)*
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DreamStay - Smart Hotel Finder</title>
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
        <header class="glass-panel header">
            <h1>DreamStay <span class="accent">AI</span></h1>
            <p>Find your perfect getaway with smart recommendations.</p>
        </header>

        <section class="glass-panel search-section">
            <form id="recommendation-form" class="search-form">
                <div class="form-group">
                    <label for="location">Destination</label>
                    <input type="text" id="location" placeholder="e.g. New York, Miami" required>
                </div>
                <div class="form-group">
                    <label for="max-price">Max Budget ($)</label>
                    <input type="number" id="max-price" placeholder="400" min="0">
                </div>
                <!-- Amenities Checkboxes go here -->
                <div class="form-group full-width">
                     <label>Amenities</label>
                     <div class="amenities-grid">
                        <!-- Add checkboxes <input type="checkbox" name="amenities" value="WiFi"> -->
                        <label class="checkbox-btn"><input type="checkbox" name="amenities" value="WiFi"><span>WiFi</span></label>
                        <label class="checkbox-btn"><input type="checkbox" name="amenities" value="Pool"><span>Pool</span></label>
                     </div>
                </div>
                <div class="form-group full-width">
                    <label for="trip-desc">Describe your dream trip (AI)</label>
                    <textarea id="trip-desc" rows="3" placeholder="e.g. Family vacation..."></textarea>
                </div>
                <button type="submit" class="cta-button">Find Hotels</button>
            </form>
        </section>

        <section id="results-section" class="results-section hidden">
            <div id="results-grid" class="results-grid"></div>
        </section>
    </main>
    <script src="script.js"></script>
</body>
</html>
```

### 5.3 File: `frontend/script.js`
The logic to connect to your API.
```javascript
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('recommendation-form');
    const resultsSection = document.getElementById('results-section');
    const resultsGrid = document.getElementById('results-grid');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const location = document.getElementById('location').value;
        const maxPrice = document.getElementById('max-price').value;
        const tripDesc = document.getElementById('trip-desc').value;
        const amenitiesNodes = document.querySelectorAll('input[name="amenities"]:checked');
        const amenities = Array.from(amenitiesNodes).map(node => node.value);

        const payload = {
            location: location || undefined,
            min_price: 0,
            max_price: maxPrice ? parseFloat(maxPrice) : 10000,
            required_amenities: amenities,
            trip_description: tripDesc || undefined
        };

        resultsSection.classList.remove('hidden');
        resultsGrid.innerHTML = `<div class="glass-panel" style="text-align:center">🤖 AI is thinking...</div>`;

        try {
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

    function renderResults(recommendations) {
        resultsGrid.innerHTML = '';
        if (recommendations.length === 0) {
            resultsGrid.innerHTML = '<div class="glass-panel">No hotels found.</div>';
            return;
        }

        recommendations.forEach((item, index) => {
            const hotel = item.hotel;
            const card = document.createElement('div');
            card.className = `hotel-card ${index === 0 ? 'top-pick' : ''}`;
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

    window.bookHotel = async (hotelId, hotelName) => {
        const email = prompt(`Enter your email to book ${hotelName}:`, "user@example.com");
        if (!email) return;

        try {
            const response = await fetch('/bookings', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'x-token': 'secret-token' 
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
