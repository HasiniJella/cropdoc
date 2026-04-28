# backend/database.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️  Warning: Supabase credentials not found in .env")
    supabase: Client = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase connected")

def get_db() -> Client:
    return supabase