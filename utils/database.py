from supabase import create_client
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

# Get config from st.secrets if available, else from env
def get_config(key):
    """Get config from st.secrets or environment variables"""
    try:
        return st.secrets.get(key)
    except:
        return os.getenv(key)

supabase = create_client(
    get_config("SUPABASE_URL"),
    get_config("SUPABASE_KEY")
)

def save_preferences(email: str, topics: list):
    """Save or update user preferences"""
    try:
        # First check if the email exists
        existing = supabase.table('user_preference').select('id').eq('email', email).execute()

        if existing.data:
            # Update existing record
            data = supabase.table('user_preference').update({
                'topics': topics
            }).eq('email', email).execute()
        else:
            # Insert new record
            data = supabase.table('user_preference').insert({
                'email': email,
                'topics': topics
            }).execute()

        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def get_user_preferences(email: str):
    """Get user preferences by email"""
    try:
        response = supabase.table('user_preference')\
            .select("*")\
            .eq('email', email)\
            .execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error: {e}")
        return None
