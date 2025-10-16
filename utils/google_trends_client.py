"""
Google Trends Client - Layer 3: External Intelligence Integration
Provides access to Google Trends data for broader market intelligence
"""

import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import streamlit as st

try:
    from pytrends.request import TrendReq
    PYTENDS_AVAILABLE = True
except ImportError:
    PYTENDS_AVAILABLE = False
    print("Warning: pytrends not available. Install with: pip install pytrends")

class GoogleTrendsClient:
    """Client for accessing Google Trends data"""
    
    def __init__(self):
        self.pytrends = None
        self.last_request_time = 0
        self.request_delay = 1  # 1 second delay between requests
        
        if PYTENDS_AVAILABLE:
            try:
                self.pytrends = TrendReq(hl='en-US', tz=360)
            except Exception as e:
                print(f"Error initializing Google Trends client: {e}")
    
    def _rate_limit(self):
        """Simple rate limiting to avoid Google blocking"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    def get_trending_queries(self, geo: str = 'US', limit: int = 10) -> List[Dict]:
        """
        Get trending search queries from Google Trends
        """
        if not PYTENDS_AVAILABLE or not self.pytrends:
            return []
        
        try:
            self._rate_limit()
            
            # Get trending searches
            trending_searches = self.pytrends.trending_searches(pn=geo)
            
            if trending_searches is not None and not trending_searches.empty:
                trends = []
                for idx, row in trending_searches.head(limit).iterrows():
                    trends.append({
                        'query': row[0],
                        'rank': idx + 1,
                        'geo': geo,
                        'timestamp': datetime.now().isoformat()
                    })
                
                return trends
            
        except Exception as e:
            print(f"Error getting trending queries: {e}")
        
        return []
    
    def get_interest_over_time(self, keywords: List[str], timeframe: str = 'today 3-m') -> Dict:
        """
        Get interest over time for specific keywords
        """
        if not PYTENDS_AVAILABLE or not self.pytrends:
            return {}
        
        try:
            self._rate_limit()
            
            # Build payload
            self.pytrends.build_payload(keywords, timeframe=timeframe)
            
            # Get interest over time
            interest_data = self.pytrends.interest_over_time()
            
            if not interest_data.empty:
                # Convert to a more usable format
                result = {
                    'keywords': keywords,
                    'timeframe': timeframe,
                    'data': {}
                }
                
                for keyword in keywords:
                    if keyword in interest_data.columns:
                        result['data'][keyword] = interest_data[keyword].to_dict()
                
                return result
            
        except Exception as e:
            print(f"Error getting interest over time: {e}")
        
        return {}
    
    def get_related_queries(self, keyword: str, limit: int = 10) -> Dict:
        """
        Get related queries for a specific keyword
        """
        if not PYTENDS_AVAILABLE or not self.pytrends:
            return {}
        
        try:
            self._rate_limit()
            
            # Build payload for the keyword
            self.pytrends.build_payload([keyword], timeframe='today 3-m')
            
            # Get related queries
            related_queries = self.pytrends.related_queries()
            
            if keyword in related_queries and related_queries[keyword] is not None:
                top_queries = related_queries[keyword]['top']
                rising_queries = related_queries[keyword]['rising']
                
                result = {
                    'keyword': keyword,
                    'top_queries': [],
                    'rising_queries': []
                }
                
                if top_queries is not None and not top_queries.empty:
                    for idx, row in top_queries.head(limit).iterrows():
                        result['top_queries'].append({
                            'query': row['query'],
                            'value': row['value']
                        })
                
                if rising_queries is not None and not rising_queries.empty:
                    for idx, row in rising_queries.head(limit).iterrows():
                        result['rising_queries'].append({
                            'query': row['query'],
                            'value': row['value']
                        })
                
                return result
            
        except Exception as e:
            print(f"Error getting related queries: {e}")
        
        return {}
    
    def compare_interest_over_time(self, keywords: List[str], timeframe: str = 'today 3-m') -> Dict:
        """
        Compare interest over time for multiple keywords
        """
        if not PYTENDS_AVAILABLE or not self.pytrends:
            return {}
        
        try:
            self._rate_limit()
            
            # Build payload
            self.pytrends.build_payload(keywords, timeframe=timeframe)
            
            # Get interest over time
            interest_data = self.pytrends.interest_over_time()
            
            if not interest_data.empty:
                # Calculate summary statistics
                summary = {}
                for keyword in keywords:
                    if keyword in interest_data.columns:
                        data = interest_data[keyword]
                        summary[keyword] = {
                            'average': float(data.mean()),
                            'max': float(data.max()),
                            'min': float(data.min()),
                            'trend': 'increasing' if data.iloc[-1] > data.iloc[0] else 'decreasing',
                            'current_value': float(data.iloc[-1])
                        }
                
                return {
                    'keywords': keywords,
                    'timeframe': timeframe,
                    'summary': summary,
                    'raw_data': interest_data.to_dict()
                }
            
        except Exception as e:
            print(f"Error comparing interest over time: {e}")
        
        return {}
    
    def get_trending_topics_for_category(self, category: str, limit: int = 10) -> List[Dict]:
        """
        Get trending topics for a specific category (AI, Technology, etc.)
        """
        # Map categories to relevant keywords
        category_keywords = {
            'AI': ['artificial intelligence', 'machine learning', 'AI', 'ChatGPT', 'OpenAI'],
            'Technology': ['technology', 'tech', 'innovation', 'startup', 'software'],
            'Business': ['business', 'economy', 'finance', 'investment', 'market'],
            'Science': ['science', 'research', 'study', 'discovery', 'experiment'],
            'Data Science': ['data science', 'analytics', 'big data', 'statistics', 'python']
        }
        
        keywords = category_keywords.get(category, [category])
        
        # Get trending queries and filter by category
        trending_queries = self.get_trending_queries(limit=20)
        
        # Filter and score based on category relevance
        relevant_trends = []
        for trend in trending_queries:
            query = trend['query'].lower()
            for keyword in keywords:
                if keyword.lower() in query:
                    relevant_trends.append({
                        **trend,
                        'category': category,
                        'relevance_score': 1.0
                    })
                    break
        
        return relevant_trends[:limit]
    
    def analyze_trend_correlation(self, user_trends: List[str], market_trends: List[str]) -> Dict:
        """
        Analyze correlation between user's trends and market trends
        """
        if not user_trends or not market_trends:
            return {}
        
        # Simple correlation analysis
        correlations = []
        
        for user_trend in user_trends:
            for market_trend in market_trends:
                # Simple string similarity check
                similarity = self._calculate_similarity(user_trend.lower(), market_trend.lower())
                if similarity > 0.3:  # Threshold for relevance
                    correlations.append({
                        'user_trend': user_trend,
                        'market_trend': market_trend,
                        'similarity': similarity,
                        'correlation_type': 'strong' if similarity > 0.7 else 'moderate'
                    })
        
        # Sort by similarity
        correlations.sort(key=lambda x: x['similarity'], reverse=True)
        
        return {
            'correlations': correlations[:10],
            'total_correlations': len(correlations),
            'strong_correlations': len([c for c in correlations if c['similarity'] > 0.7])
        }
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple string similarity"""
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def get_market_intelligence_summary(self, user_categories: List[str]) -> Dict:
        """
        Get a summary of market intelligence for user's categories
        """
        summary = {
            'timestamp': datetime.now().isoformat(),
            'categories': {},
            'overall_trends': [],
            'recommendations': []
        }
        
        for category in user_categories:
            # Get trending topics for this category
            category_trends = self.get_trending_topics_for_category(category, limit=5)
            
            summary['categories'][category] = {
                'trending_topics': category_trends,
                'trend_count': len(category_trends)
            }
            
            # Add to overall trends
            summary['overall_trends'].extend(category_trends)
        
        # Generate recommendations
        if summary['overall_trends']:
            top_trends = sorted(summary['overall_trends'], 
                              key=lambda x: x.get('relevance_score', 0), 
                              reverse=True)[:5]
            
            summary['recommendations'] = [
                f"Consider monitoring: {trend['query']}" 
                for trend in top_trends
            ]
        
        return summary

# Create singleton instance
google_trends_client = GoogleTrendsClient()
