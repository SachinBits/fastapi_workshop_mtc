import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or "your_supabase_url" in url:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    exit(1)

supabase: Client = create_client(url, key)

import random

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
        # Generate Name
        while True:
            name = f"{random.choice(adjectives)} {random.choice(nouns)}"
            if name not in use_existing_names:
                use_existing_names.add(name)
                break
        
        # Generate Location
        location = random.choice(cities)
        
        # Generate Price (weighted random)
        price = random.randint(50, 800)
        
        # Generate Rating
        rating = round(random.uniform(3.0, 5.0), 1)
        
        # Generate Amenities (3 to 8 random amenities)
        num_amenities = random.randint(3, 8)
        amenities = random.sample(amenities_pool, num_amenities)
        
        # Generate Description
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
    # Insert in batches to be efficient
    batch_size = 20
    for i in range(0, len(hotels_data), batch_size):
        batch = hotels_data[i:i+batch_size]
        try:
            # We use 'upsert' or just insert. Since we don't provide IDs, new rows are created.
            data, count = supabase.table("hotels").insert(batch).execute()
            print(f"Inserted batch {i//batch_size + 1}/{len(hotels_data)//batch_size}")
        except Exception as e:
            print(f"Failed to insert batch: {e}")
            
    print("Seeding complete!")

if __name__ == "__main__":
    seed_data()
