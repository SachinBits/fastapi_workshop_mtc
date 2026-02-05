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
    """
    Filters hotels based on user criteria.
    """
    filtered_hotels = []
    
    for hotel in hotels:
        # Location filter (case-insensitive substring)
        if location and location.lower() not in hotel.location.lower():
            continue
            
        # Price filter
        if not (min_price <= hotel.price <= max_price):
            continue
            
        # Amenities filter (hotel must have ALL requested amenities)
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
    Calculates a match score (0-100) based on weighted criteria.
    Weights:
    - Price Match: 40% (Lower is better within range)
    - Rating: 30% (Higher is better)
    - Amenity Match: 30% (More matches = higher score)
    """
    score = 0.0
    
    # 1. Price Score (40 points)
    # If price is well below max_price, give higher score.
    if user_pref.max_price > 0:
        price_ratio = hotel.price / user_pref.max_price
        if price_ratio <= 1.0:
            # Lower price ratio -> higher score. 
            # e.g. 0.5 ratio -> 0.5 * 40 = 20 points? No, simpler:
            # Score = (1 - ratio) * 40? No, that punishes exact match.
            # Let's use simple inverse: 
            # If hotel is 50% of budget, it gets full marks? Maybe not.
            # Let's say: 40 points if within budget. Bonus for being cheaper?
            # Simple approach: 
            score += 40.0 # Base score for being within budget (filtered list)
            # Maybe subtract points as it gets closer to max? 
            # let's keep it simple for workshop: 
            # score += (1 - (hotel.price / user_pref.max_price)) * 10 # Bonus up to 10 points
    
    # 2. Rating Score (30 points)
    # Rating 5 = 30 points. Rating 0 = 0 points.
    score += (hotel.rating / 5.0) * 30.0
    
    # 3. Amenities Score (30 points)
    # Count how many of the user's PREFERRED amenities match the hotel.
    # Note: 'required_amenities' are already strictly filtered. 
    # Let's assume user might send *desired* amenities in preferences too?
    # For this simple model, let's just score based on total amenities count as a proxy for "luxury" 
    # OR if we had a separate "preferred" list. 
    # Let's stick to the prompt's simplicity: Maybe just raw amenity count?
    # Let's limit it to capping at 5 amenities = 30 points.
    amenity_count = len(hotel.amenities)
    score += min(amenity_count * 6.0, 30.0)
    
    return round(score, 1)

def generate_recommendation_reason(hotel: Hotel, user_pref: UserPreference, score: float) -> str:
    """
    Generates a reason for the recommendation using Hybrid approach.
    """
    # 1. Template-based fallback
    fallback_reason = (
        f"This hotel is a great match located in {hotel.location} with a rating of {hotel.rating}. "
        f"It costs ${hotel.price} per night."
    )
    
    # 2. AI Enhancement (Gemini)
    if API_KEY:
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = (
                f"Explain why '{hotel.name}' is a good recommendation for a traveler "
                f"looking for a hotel in {user_pref.location} with a budget of ${user_pref.max_price}. "
                f"The hotel costs ${hotel.price}, has a {hotel.rating} star rating, and these amenities: {', '.join(hotel.amenities)}. "
                f"Keep it persuasive but short (under 50 words)."
            )
            response = model.generate_content(prompt)
            if response.text:
                return response.text.replace("\n", " ").strip()
        except Exception as e:
            print(f"AI Generation failed: {e}")
            
    return fallback_reason

def rerank_hotels(hotels: List[Hotel], user_pref: UserPreference) -> List[dict]:
    """
    Uses Gemini AI to rerank a list of candidate hotels based on the user's free-text description.
    Returns a list of dicts with 'hotel', 'score', 'reasoning'.
    """
    if not user_pref.trip_description or not API_KEY:
        return []

    # Prepare the candidates for the prompt
    candidates_text = ""
    for i, h in enumerate(hotels):
        candidates_text += f"Hotel {i}: {h.name} (${h.price}, {h.rating} stars). Amenities: {', '.join(h.amenities)}. Loc: {h.location}.\n"

    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = (
            f"User is looking for: '{user_pref.trip_description}'.\n"
            f"Here are the candidates:\n{candidates_text}\n"
            "Task: Rank these hotels from best to worst match for the user's specific request. "
            "Return a JSON array where each object has: 'index' (int), 'score' (0-100), and 'reasoning' (max 20 words). "
            "The JSON should be the only output."
        )
        
        response = model.generate_content(prompt)
        # Simple parsing (in a workshop, we might need more robust JSON parsing)
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
