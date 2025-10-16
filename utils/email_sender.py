import resend
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

resend.api_key = get_config("RESEND_API_KEY")

def send_newsletter(to_email: str, content: str):
    """Send the curated newsletter via email"""
    
    # Parse content (simple splitting)
    lines = content.split('\n')
    subject = next((l.replace('SUBJECT:', '').strip() for l in lines if 'SUBJECT:' in l), 'Your AI Newsletter')
    
    # Process content for HTML
    processed_content = content.replace('SUMMARY:', '<h2>Summary</h2>').replace('LEARNING:', '<h2>Key Learning</h2>').replace('ACTION:', '<h2>Today\'s Action</h2>')
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #2563eb;">📰 Your Personalized AI Newsletter</h1>
            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px;">
                {processed_content}
            </div>
        </body>
    </html>
    """
    
    try:
        resend.Emails.send({
            "from": "onboarding@resend.dev",  # Resend test domain
            "to": to_email,
            "subject": subject,
            "html": html_content
        })
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False