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
        self.request_delay = 3  # 3 second delay (safer for Google Trends rate limits)
        self.trends_available = False
        
        # Caching system to reduce API calls
        self.keyword_cache = {}
        self.cache_ttl = 14400  # 4 hours in seconds (4 * 60 * 60)
        
        if PYTENDS_AVAILABLE:
            try:
                self.pytrends = TrendReq(hl='en-US', tz=360)
                self.trends_available = True
                print("✅ Google Trends client initialized successfully (4-hour cache enabled)")
            except Exception as e:
                print(f"❌ Error initializing Google Trends client: {e}")
                self.trends_available = False
    
    def _rate_limit(self):
        """Simple rate limiting to avoid Google blocking"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    def _cleanup_expired_cache(self):
        """Remove expired cache entries to prevent memory leak"""
        current_time = time.time()
        expired_keys = []
        
        for key, (data, timestamp) in list(self.keyword_cache.items()):
            if current_time - timestamp > self.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.keyword_cache[key]
        
        if expired_keys:
            print(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
    
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
    
    def get_interest_over_time(self, keywords: List[str], timeframe: str = 'today 3-m', max_retries: int = 3) -> Dict:
        """
        Get interest over time for specific keywords with 4-hour caching and retry logic
        """
        if not PYTENDS_AVAILABLE or not self.pytrends:
            return {}
        
        # Generate cache key
        cache_key = f"{','.join(sorted(keywords))}_{timeframe}"
        
        # Clean up expired cache entries first
        self._cleanup_expired_cache()
        
        # Check cache first (4-hour TTL)
        if cache_key in self.keyword_cache:
            cached_data, timestamp = self.keyword_cache[cache_key]
            age_seconds = time.time() - timestamp
            age_minutes = int(age_seconds / 60)
            
            if age_seconds < self.cache_ttl:
                print(f"💾 Using cached data for {keywords} (age: {age_minutes} min, ttl: 4 hours)")
                return cached_data
            else:
                # Cache expired, remove it
                del self.keyword_cache[cache_key]
                print(f"🔄 Cache expired for {keywords} (age: {age_minutes} min), fetching fresh data...")
        
        # Fetch fresh data with retry logic
        for attempt in range(max_retries):
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
                    
                    # Cache the successful result
                    self.keyword_cache[cache_key] = (result, time.time())
                    print(f"✅ Fetched and cached data for {keywords}")
                    
                    return result
                else:
                    return {}
                    
            except Exception as e:
                error_str = str(e)
                
                # Handle rate limit (429) with exponential backoff
                if '429' in error_str or 'Too Many Requests' in error_str:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 3  # 3s, 6s, 12s
                        print(f"⚠️ Rate limited (429), waiting {wait_time}s before retry {attempt + 2}/{max_retries}...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"❌ Rate limit persists after {max_retries} retries: {e}")
                        return {}
                else:
                    # Non-rate-limit error
                    print(f"Error getting interest over time: {e}")
                    return {}
        
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
        Get trending topics using WORKING keyword-based API
        Uses get_interest_over_time() instead of broken trending_searches()
        """
        
        # Expanded keyword lists for better coverage
        category_keywords = {
            'AI': [
                'ChatGPT', 'OpenAI', 'Claude AI', 'Gemini', 'Anthropic',
                'GPT-4', 'GPT-4o', 'LLaMA', 'Mistral AI', 'AI agents',
                'Machine learning', 'Deep learning', 'Neural networks',
                'Stable Diffusion', 'Midjourney', 'AI safety', 'AGI',
                'Prompt engineering', 'RAG', 'Fine-tuning', 'LLM'
            ],
            'Technology': [
                'iPhone 16', 'iPhone 15', 'Android 15', 'Vision Pro', 'Meta Quest',
                'Tesla', 'SpaceX', 'Starlink', 'Steam Deck', 'Nintendo Switch',
                'AWS', 'Azure', 'Google Cloud', 'Kubernetes', 'Docker',
                'React', 'Next.js', 'Vue', 'TypeScript', 'Python', 'Rust'
            ],
            'Business': [
                'S&P 500', 'Nasdaq', 'Dow Jones', 'Stock market', 'Bitcoin',
                'Ethereum', 'Crypto', 'NFT', 'DeFi', 'Web3',
                'Startup funding', 'Venture capital', 'IPO', 'Unicorn',
                'Inflation', 'Federal Reserve', 'Interest rates', 'GDP'
            ],
            'Science': [
                'Climate change', 'CERN', 'NASA', 'SpaceX', 'James Webb',
                'Quantum computing', 'CRISPR', 'Gene editing', 'mRNA vaccine',
                'Fusion energy', 'Dark matter', 'Black hole', 'Exoplanet'
            ],
            'Data Science': [
                'Python', 'Pandas', 'NumPy', 'Scikit-learn', 'TensorFlow',
                'PyTorch', 'Jupyter', 'Data visualization', 'SQL', 'BigQuery',
                'Tableau', 'Power BI', 'Snowflake', 'dbt', 'Airflow'
            ]
        }
        
        keywords = category_keywords.get(category, [category])
        # Limit keywords to check (2x the desired limit for efficiency)
        keywords_to_check = keywords[:limit * 2]
        trending_topics = []
        
        print(f"🔍 Checking {len(keywords_to_check)} keywords for category '{category}' (limited from {len(keywords)} total)...")
        
        # Check each keyword for trending status
        for keyword in keywords_to_check:
            try:
                self._rate_limit()
                
                # Use the WORKING API
                interest_data = self.get_interest_over_time([keyword], timeframe='now 7-d')
                
                if not interest_data or not interest_data.get('data', {}).get(keyword):
                    continue
                
                # Extract time series values
                values = list(interest_data['data'][keyword].values())
                
                if len(values) < 7:
                    continue
                
                # Calculate trending status (compare recent vs baseline)
                recent_avg = sum(values[-3:]) / 3  # Last 3 days average
                baseline_avg = sum(values[:4]) / 4  # First 4 days average
                
                # Calculate percentage change
                if baseline_avg > 0:
                    change_pct = ((recent_avg - baseline_avg) / baseline_avg) * 100
                else:
                    change_pct = 0 if recent_avg == 0 else 100
                
                # Only include if trending UP by at least 15%
                if change_pct >= 15:
                    trending_topics.append({
                        'query': keyword,
                        'category': category,
                        'relevance_score': recent_avg / 100.0,  # Normalize to 0-1
                        'change_percent': round(change_pct, 1),
                        'trend': 'rising',
                        'rank': len(trending_topics) + 1,
                        'geo': 'US',
                        'timestamp': datetime.now().isoformat(),
                        'baseline_interest': round(baseline_avg, 1),
                        'current_interest': round(recent_avg, 1)
                    })
                    
                    # Early exit optimization: stop when we have enough trends
                    if len(trending_topics) >= limit:
                        print(f"⚡ Early exit: Found {limit} trending topics after checking {keywords_to_check.index(keyword)+1}/{len(keywords_to_check)} keywords")
                        break
            
            except Exception as e:
                # Silent fail for individual keywords, keep checking others
                continue
        
        # Sort by relevance score (highest interest first)
        trending_topics.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        print(f"✅ Found {len(trending_topics)} trending topics for '{category}'")
        
        return trending_topics[:limit]
    
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
            # Get trending topics for this category (with fallback to Reddit)
            category_trends = self.get_trending_topics_with_fallback(category, limit=5)
            
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
    
    def get_trending_topics_with_fallback(self, category: str, limit: int = 5) -> List[Dict]:
        """
        Get trending topics with fallback to Reddit/HN if Google Trends fails
        """
        # Try Google Trends first
        try:
            trends = self.get_trending_topics_for_category(category, limit)
            if trends:
                for trend in trends:
                    trend['data_source'] = 'Google Trends'
                print(f"✅ Using Google Trends data for '{category}' ({len(trends)} trends)")
                return trends
            else:
                print(f"⚠️ Google Trends returned empty for '{category}', trying community fallback...")
        except Exception as e:
            if '429' in str(e):
                print(f"🚫 Google Trends rate limited for '{category}', using community fallback...")
            else:
                print(f"❌ Google Trends error for '{category}': {e}, using community fallback...")
        
        # Fallback to Reddit/HN community trends
        return self._get_community_trends(category, limit)
    
    def _get_community_trends(self, category: str, limit: int) -> List[Dict]:
        """
        Get trending topics from Reddit/HN community (NO rate limits!)
        """
        from utils.scraper import scrape_reddit_url
        
        # Map categories to subreddits
        category_subreddits = {
            'AI': ['r/artificial', 'r/MachineLearning'],
            'Technology': ['r/technology', 'r/programming'],
            'Business': ['r/business', 'r/startups'],
            'Science': ['r/science', 'r/Physics'],
            'Data Science': ['r/datascience', 'r/learnmachinelearning']
        }
        
        subreddits = category_subreddits.get(category, [f'r/{category.lower()}'])
        trends = []
        
        print(f"🔍 Fetching community trends from {len(subreddits)} subreddits for '{category}'...")
        
        for subreddit in subreddits:
            try:
                url = f"https://reddit.com/{subreddit}"
                articles = scrape_reddit_url(url, max_items=10)
                
                for article in articles:
                    # Extract score/engagement
                    score = 0
                    if 'score' in article:
                        score = article['score']
                    elif 'points' in article:
                        score = article['points']
                    
                    # High engagement = trending (>100 upvotes)
                    if score > 100:
                        trends.append({
                            'query': article['title'][:60],
                            'category': category,
                            'relevance_score': min(score / 1000.0, 1.0),
                            'trend': 'community',
                            'data_source': 'Reddit',
                            'upvotes': score,
                            'url': article.get('source', ''),
                            'timestamp': datetime.now().isoformat()
                        })
            except Exception as e:
                print(f"  ⚠️ Could not fetch from {subreddit}: {e}")
                continue
        
        # Sort by engagement
        trends.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        result = trends[:limit]
        print(f"✅ Found {len(result)} community trends for '{category}' from Reddit")
        return result

# Create singleton instance
google_trends_client = GoogleTrendsClient()
