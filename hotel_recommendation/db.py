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
