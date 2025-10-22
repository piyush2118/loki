"""
Voice Training Module for AI Newsletter MVP
Phase 2: LLM-based feature extraction for personalized newsletter generation
"""

import json
from typing import List, Dict, Optional
from supabase import create_client
import streamlit as st
import os
from dotenv import load_dotenv
from utils.auth import supabase  # Use authenticated client
from groq import Groq

load_dotenv()

# Get config from st.secrets if available, else from env
def get_config(key):
    """Get config from st.secrets or environment variables"""
    try:
        return st.secrets.get(key)
    except:
        return os.getenv(key)

class VoiceTrainer:
    """Manage user voice training and style profiles"""
    
    def __init__(self):
        self.supabase = supabase
        self.groq_client = Groq(api_key=get_config("GROQ_API_KEY"))
    
    def upload_writing_sample(self, user_id: str, title: str, content: str, metadata: Dict = None) -> Dict:
        """Upload newsletter content, extract features, and store only features (no redundant content)"""
        try:
            # Extract features using LLM (this is the valuable data)
            features = self._extract_features_with_llm(content)
            if not features:
                return {'success': False, 'error': 'Failed to extract features from newsletter content'}
            
            # Calculate word count for analysis
            word_count = len(content.split())
            
            # Store only the extracted features (not the full content)
            result = self.supabase.table('user_newsletter_features').insert({
                'user_id': user_id,
                'newsletter_title': title,
                'topic_category': features.get('topic_category'),
                'writing_style': features.get('writing_style'),
                'voice_characteristics': features.get('voice_characteristics'),
                'content_focus': features.get('content_focus'),
                'target_length_range': features.get('target_length_range'),
                'confidence_score': features.get('confidence_score', 0.8),
                'word_count': word_count
            }).execute()
            
            return {'success': True, 'data': result.data[0] if result.data else None}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_user_samples(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get user's uploaded newsletter titles and features (no full content stored)"""
        try:
            result = self.supabase.table('user_newsletter_features')\
                .select('newsletter_title, topic_category, writing_style, voice_characteristics, content_focus, uploaded_at, word_count')\
                .eq('user_id', user_id)\
                .order('uploaded_at', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting user samples: {e}")
            return []
    
    def generate_style_card(self, user_id: str) -> Dict:
        """Generate style profile from user's extracted features"""
        try:
            # Get user's features instead of manual analysis
            features = self.get_user_features(user_id)
            
            if not features:
                return {'success': False, 'error': 'No features found. Upload some newsletters first.'}
            
            # Create style card from extracted features
            style_card = {
                'writing_style': features.get('writing_style', 'analytical'),
                'voice_characteristics': features.get('voice_characteristics', 'professional'),
                'content_focus': features.get('content_focus', 'trends'),
                'topic_category': features.get('topic_category', 'AI'),
                'target_length_range': features.get('target_length_range', '600-800'),
                'sample_count': features.get('sample_count', 0),
                'last_updated': 'now'
            }
            
            return {'success': True, 'style_card': style_card}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    
    
    def _extract_features_with_llm(self, newsletter_content: str) -> Optional[Dict]:
        """Extract features using LLM analysis"""
        try:
            # Calculate word count for length range
            word_count = len(newsletter_content.split())
            length_range = self._get_length_range(word_count)
            
            # LLM-based analysis for core features
            analysis_prompt = f"""Analyze this newsletter and classify it using these specific categories:

1. Writing Style: Choose ONE from: analytical, narrative, explanatory, persuasive
2. Voice Characteristics: Choose ONE from: authoritative, conversational, technical, accessible  
3. Content Focus: Choose ONE from: trends, tutorials, analysis, news, opinion
4. Topic Category: Choose ONE from: AI, Technology, Business, Science, Other

Newsletter content: {newsletter_content[:1500]}

Respond ONLY with valid JSON in this exact format:
{{"writing_style": "analytical", "voice_characteristics": "conversational", "content_focus": "trends", "topic_category": "AI"}}"""
            
            response = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.1,  # Lower temperature for more consistent JSON
                max_tokens=200
            )
            
            # Extract and clean the response
            raw_response = response.choices[0].message.content.strip()
            
            # Try to extract JSON from response (in case LLM adds extra text)
            import re
            json_match = re.search(r'\{[^}]*\}', raw_response)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = raw_response
            
            # Parse JSON
            features = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['writing_style', 'voice_characteristics', 'content_focus', 'topic_category']
            for field in required_fields:
                if field not in features:
                    print(f"Missing field {field} in LLM response")
                    return None
            
            # Add computed fields
            features['target_length_range'] = length_range
            features['confidence_score'] = 0.8
            
            return features
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Raw LLM response: {raw_response if 'raw_response' in locals() else 'No response'}")
            return None
        except Exception as e:
            print(f"Error extracting features with LLM: {e}")
            return None
    
    def _get_length_range(self, word_count: int) -> str:
        """Convert word count to range"""
        if word_count < 500:
            return "300-500"
        elif word_count < 800:
            return "500-800"
        elif word_count < 1200:
            return "800-1200"
        elif word_count < 2000:
            return "1200-2000"
        else:
            return "2000-3000"
    
    def get_user_features(self, user_id: str, topic_category: str = None) -> Optional[Dict]:
        """Get aggregated user features for prompt building"""
        try:
            query = self.supabase.table('user_newsletter_features')\
                .select('*')\
                .eq('user_id', user_id)
            
            if topic_category:
                query = query.eq('topic_category', topic_category)
            
            result = query.execute()
            
            if not result.data:
                return None
            
            # Aggregate features from multiple samples
            # Use the most recent sample's features (first in desc order)
            sample = result.data[0]
            
            # Validate all required fields are present
            required_fields = ['topic_category', 'writing_style', 'voice_characteristics', 
                             'content_focus', 'target_length_range']
            
            for field in required_fields:
                if not sample.get(field):
                    print(f"⚠️ Missing required field '{field}' in database for user {user_id}")
                    return None
            
            features = {
                'topic_category': topic_category or sample['topic_category'],
                'writing_style': sample['writing_style'],
                'voice_characteristics': sample['voice_characteristics'],
                'content_focus': sample['content_focus'],
                'target_length_range': sample['target_length_range'],
                'sample_count': len(result.data)
            }
            
            print(f"✅ Loaded features from database for user {user_id} ({len(result.data)} samples)")
            return features
            
        except Exception as e:
            print(f"Error getting user features: {e}")
            return None
    
    

# Create singleton instance
voice_trainer = VoiceTrainer()
