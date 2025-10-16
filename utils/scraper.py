"""
Main news scraper that gets real recent content from various sources
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import urllib3
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

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_sources(category: str, max_articles=5):
    """Main news scraper that gets real recent content"""
    print(f"🔍 Scraping recent {category} news (working method)...")
    
    articles = []
    
    # Use working news sources that are known to work
    working_sources = get_working_sources(category)
    
    for source in working_sources:
        try:
            print(f"📰 Checking: {source['name']}")
            articles_from_source = scrape_working_source(source)
            articles.extend(articles_from_source)
            
            if len(articles) >= max_articles:
                break
                
        except Exception as e:
            print(f"   ⚠️ Failed to scrape {source['name']}: {e}")
    
    print(f"✅ Found {len(articles)} real articles")
    return articles[:max_articles]

def get_working_sources(category):
    """Get working news sources for each category from config"""
    from config.sources import NEWS_SOURCES
    
    category_data = NEWS_SOURCES.get(category, {})
    api_sources = category_data.get('api_sources', [])
    
    sources = []
    
    for url in api_sources:
        if 'hn.algolia.com' in url:
            sources.append({
                'name': f'Hacker News {category}',
                'url': url,
                'type': 'api'
            })
        elif 'reddit.com' in url:
            sources.append({
                'name': f'Reddit {category}',
                'url': url,
                'type': 'reddit'
            })
        elif 'arxiv.org' in url:
            sources.append({
                'name': f'ArXiv {category}',
                'url': url,
                'type': 'arxiv'
            })
    
    return sources

def scrape_working_source(source):
    """Scrape from a working source"""
    articles = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        if source['type'] == 'api':
            articles = scrape_api_source(source, headers)
        elif source['type'] == 'reddit':
            articles = scrape_reddit_source(source, headers)
        elif source['type'] == 'arxiv':
            articles = scrape_arxiv_source(source, headers)
            
    except Exception as e:
        print(f"   ❌ Error scraping {source['name']}: {e}")
    
    return articles

def scrape_api_source(source, headers):
    """Scrape from API source (like Hacker News)"""
    articles = []
    
    try:
        response = requests.get(source['url'], headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'hits' in data:
            for hit in data['hits'][:5]:
                title = hit.get('title', '')
                url = hit.get('url', '')
                points = hit.get('points', 0)
                created_at = hit.get('created_at', '')
                
                if title and url and points > 5:  # Only articles with some engagement
                    # Get content from the article
                    content = get_article_content_safe(url)
                    
                    if content:
                        articles.append({
                            'source': url,
                            'title': title,
                            'content': content[:1500],
                            'published': created_at
                        })
                        print(f"   ✅ Found: {title[:50]}...")
                        
    except Exception as e:
        print(f"   ⚠️ API scraping error: {e}")
    
    return articles

def scrape_reddit_source(source, headers):
    """Scrape from Reddit source"""
    articles = []
    
    try:
        response = requests.get(source['url'], headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'data' in data and 'children' in data['data']:
            for post in data['data']['children'][:5]:
                post_data = post.get('data', {})
                title = post_data.get('title', '')
                url = post_data.get('url', '')
                score = post_data.get('score', 0)
                selftext = post_data.get('selftext', '')
                
                if title and url and score > 10:  # Only posts with some engagement
                    # Try to get real content from the external URL
                    if selftext and len(selftext) > 100:
                        content = selftext
                    else:
                        # Fetch content from the external article URL
                        content = get_article_content_safe(url)
                        if not content or len(content) < 100:
                            content = f"Recent news: {title}. This article discusses important developments in the field."
                    
                    articles.append({
                        'source': url,
                        'title': title,
                        'content': content[:1500],
                        'published': None
                    })
                    print(f"   ✅ Found: {title[:50]}...")
                    
    except Exception as e:
        print(f"   ⚠️ Reddit scraping error: {e}")
    
    return articles

def scrape_arxiv_source(source, headers):
    """Scrape from ArXiv source"""
    articles = []
    
    try:
        response = requests.get(source['url'], headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse XML response
        from xml.etree import ElementTree as ET
        root = ET.fromstring(response.content)
        
        # ArXiv namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', ns)[:5]:
            title_elem = entry.find('atom:title', ns)
            summary_elem = entry.find('atom:summary', ns)
            link_elem = entry.find('atom:link[@type="text/html"]', ns)
            
            if title_elem is not None and summary_elem is not None:
                title = title_elem.text.strip()
                summary = summary_elem.text.strip()
                url = link_elem.get('href') if link_elem is not None else ''
                
                articles.append({
                    'source': url,
                    'title': title,
                    'content': summary[:1500],
                    'published': None
                })
                print(f"   ✅ Found: {title[:50]}...")
                
    except Exception as e:
        print(f"   ⚠️ ArXiv scraping error: {e}")
    
    return articles

def get_article_content_safe(url):
    """Safely get article content with error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to extract main content with comprehensive selectors
        content_selectors = [
            # News site specific selectors
            '.article-body p',
            '.story-body p', 
            '.article-content p',
            '.post-content p',
            '.entry-content p',
            '.content p',
            '.story p',
            '.article p',
            'article p',
            'main p',
            '.main p',
            # Generic selectors
            'p'
        ]
        
        for selector in content_selectors:
            paragraphs = soup.select(selector)
            if paragraphs:
                content_parts = []
                for p in paragraphs[:5]:  # First 5 paragraphs for better context
                    text = p.get_text(strip=True)
                    if len(text) > 50:  # Longer minimum for better content
                        content_parts.append(text)
                
                if content_parts and len(' '.join(content_parts)) > 200:
                    return ' '.join(content_parts)
        
        # Try to get content from meta description as fallback
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            desc = meta_desc.get('content').strip()
            if len(desc) > 100:
                return desc
        
        # Final fallback: get all text and clean it
        text = soup.get_text()
        if len(text) > 100:
            # Clean up the text
            lines = text.split('\n')
            clean_lines = [line.strip() for line in lines if len(line.strip()) > 50]
            if clean_lines:
                return ' '.join(clean_lines[:3])  # First 3 substantial lines
        
    except Exception as e:
        print(f"     ⚠️ Error getting content from {url}: {e}")
    
    return ""

# ============================================================================
# NEW: DYNAMIC USER SOURCE SCRAPING
# ============================================================================

from typing import Optional, List, Dict
from urllib.parse import urlparse
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import time
from yt_to_id import get_youtube_video_id

def scrape_user_sources(user_id: str, max_articles: int = 20):
    """
    Scrape all sources for a specific user - auto-detects platform
    This is the NEW dynamic approach for personalized sources
    Enhanced with metadata for trend analysis
    """
    from config.sources import source_manager
    from datetime import datetime
    import threading
    
    print(f"🔍 Scraping custom sources for user...")
    print(f"   🧵 Running in thread: {threading.current_thread().name}")
    
    # Get user's custom sources
    try:
        sources = source_manager.get_user_sources(user_id, active_only=True)
        print(f"   📊 Retrieved {len(sources) if sources else 0} sources from database")
    except Exception as e:
        print(f"   ❌ Error getting sources from database: {e}")
        return []
    
    if not sources:
        print("⚠️  No custom sources found for user")
        return []
    
    print(f"📰 Found {len(sources)} active sources")
    
    all_articles = []
    scrape_metadata = {
        'total_sources': len(sources),
        'successful_sources': 0,
        'failed_sources': 0,
        'scrape_timestamp': datetime.now().isoformat(),
        'source_types': {},
        'articles_per_source': {}
    }
    
    for source in sources:
        try:
            url = source['source_url']
            display_name = source.get('display_name', url)
            source_type = detect_source_type(url)
            
            print(f"  📡 Scraping: {display_name} ({source_type})")
            
            # Smart detection and scraping with timeout
            print(f"     🔄 Starting scrape with timeout protection...")
            articles = scrape_url_smart_with_timeout(url, max_items=5, timeout=30)
            print(f"     📋 Scrape completed, got {len(articles) if articles else 0} articles")
            
            if articles:
                # Add metadata to each article
                for article in articles:
                    article['source_metadata'] = {
                        'source_id': source['id'],
                        'source_display_name': display_name,
                        'source_priority': source.get('priority', 5),
                        'scraped_at': datetime.now().isoformat(),
                        'source_type': source_type
                    }
                
                all_articles.extend(articles)
                scrape_metadata['successful_sources'] += 1
                scrape_metadata['articles_per_source'][display_name] = len(articles)
                
                # Track source types
                scrape_metadata['source_types'][source_type] = scrape_metadata['source_types'].get(source_type, 0) + 1
                
                print(f"     ✅ Found {len(articles)} articles")
                
                # Update scrape timestamp
                try:
                    source_manager.update_scrape_timestamp(source['id'])
                except Exception as e:
                    print(f"     ⚠️  Could not update timestamp: {e}")
            else:
                scrape_metadata['failed_sources'] += 1
                print(f"     ⚠️  No articles found - possible issues:")
                print(f"        - Source may be down or changed")
                print(f"        - Content may not meet quality threshold")
                print(f"        - Rate limiting or access restrictions")
                print(f"        - Platform-specific issues (e.g., nitter instances down)")
                
                # Provide specific guidance based on source type
                if source_type == 'twitter':
                    print(f"        💡 Twitter/X: Try checking if the account is public and active")
                    print(f"        💡 Twitter/X: Nitter instances may be temporarily unavailable")
                elif source_type == 'youtube':
                    print(f"        💡 YouTube: Check if the channel exists and has recent videos")
                elif source_type == 'reddit':
                    print(f"        💡 Reddit: Verify the subreddit exists and is public")
        
        except Exception as e:
            scrape_metadata['failed_sources'] += 1
            error_type = type(e).__name__
            print(f"     ❌ Error ({error_type}): {e}")
            
            # Provide helpful error context
            if "timeout" in str(e).lower():
                print(f"        💡 Try again later - source may be slow")
            elif "404" in str(e) or "not found" in str(e).lower():
                print(f"        💡 Check if URL is still valid")
            elif "403" in str(e) or "forbidden" in str(e).lower():
                print(f"        💡 Source may be blocking requests")
            elif "ssl" in str(e).lower() or "certificate" in str(e).lower():
                print(f"        💡 SSL certificate issue - source may be down")
            
            continue
    
    # Add overall metadata to the result
    result_articles = all_articles[:max_articles]
    
    # Store metadata in session state for trend analysis
    if 'scrape_metadata' not in st.session_state:
        st.session_state['scrape_metadata'] = []
    
    st.session_state['scrape_metadata'].append(scrape_metadata)
    
    # Keep only last 10 metadata entries to avoid memory issues
    if len(st.session_state['scrape_metadata']) > 10:
        st.session_state['scrape_metadata'] = st.session_state['scrape_metadata'][-10:]
    
    # Print comprehensive summary
    print(f"✅ Total articles scraped: {len(result_articles)}")
    print(f"📊 Scraping Summary:")
    print(f"   - Total sources: {scrape_metadata['total_sources']}")
    print(f"   - Successful: {scrape_metadata['successful_sources']}")
    print(f"   - Failed: {scrape_metadata['failed_sources']}")
    print(f"   - Success rate: {(scrape_metadata['successful_sources'] / scrape_metadata['total_sources'] * 100):.1f}%")
    
    if scrape_metadata['source_types']:
        print(f"   - Source types: {', '.join([f'{k}({v})' for k, v in scrape_metadata['source_types'].items()])}")
    
    if scrape_metadata['articles_per_source']:
        print(f"   - Articles per source: {', '.join([f'{k}({v})' for k, v in scrape_metadata['articles_per_source'].items()])}")
    
    return result_articles


def detect_source_type(url: str) -> str:
    """Detect the type of source from URL"""
    url_lower = url.lower()
    
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    elif 'reddit.com' in url_lower:
        return 'reddit'
    elif 'hn.algolia.com' in url_lower or 'news.ycombinator.com' in url_lower:
        return 'hackernews'
    elif url_lower.endswith(('.xml', '.rss', '/feed', '/feed/')):
        return 'rss'
    else:
        return 'website'


def scrape_url_smart(url: str, max_items: int = 5):
    """
    Smart scraper - detects platform from URL and routes accordingly
    NO COMPLEX REGEX - Just simple string checks
    """
    url_lower = url.lower()
    print(f"     🔍 Analyzing URL: {url}")
    print(f"     📝 URL lower: {url_lower}")
    
    # YouTube
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        print(f"     🎥 Detected: YouTube platform")
        return scrape_youtube(url, max_items)
    
    # Twitter/X
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        print(f"     🐦 Detected: Twitter/X platform")
        return scrape_twitter(url, max_items)
    
    # Reddit
    elif 'reddit.com' in url_lower:
        print(f"     🤖 Detected: Reddit platform")
        return scrape_reddit_url(url, max_items)
    
    # RSS (check if URL ends with common RSS patterns)
    elif url_lower.endswith(('.xml', '.rss', '/feed', '/feed/')):
        print(f"     📡 Detected: RSS feed")
        return scrape_rss(url, max_items)
    
    # Hacker News
    elif 'news.ycombinator.com' in url_lower or 'hn.algolia.com' in url_lower:
        print(f"     🔶 Detected: Hacker News platform")
        return scrape_hackernews_url(url, max_items)
    
    # Try as RSS first (many sites have RSS)
    else:
        print(f"     🌐 Detected: Generic website, trying RSS discovery")
        articles = scrape_generic_website(url, max_items)
        if articles:
            print(f"     ✅ RSS discovery successful")
            return articles
        
        print(f"     🔄 RSS failed, trying direct content scraping")
        # Fallback: Try to scrape as regular website
        content = get_article_content_safe(url)
        if content:
            print(f"     ✅ Direct content scraping successful")
            return [{
                'source': url,
                'title': urlparse(url).netloc,
                'content': content[:1500],
                'published': None
            }]
    
    print(f"     ❌ All scraping methods failed")
    return []


def scrape_url_smart_with_timeout(url: str, max_items: int = 5, timeout: int = 30):
    """
    Smart scraper with thread-safe timeout protection
    Uses concurrent.futures instead of signal for thread safety
    """
    import concurrent.futures
    import time
    
    def scrape_with_timeout():
        """Wrapper function for scraping with timeout"""
        return scrape_url_smart(url, max_items)
    
    try:
        # Use ThreadPoolExecutor for thread-safe timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            # Submit the scraping task
            future = executor.submit(scrape_with_timeout)
            
            try:
                # Wait for result with timeout
                result = future.result(timeout=timeout)
                return result
                
            except concurrent.futures.TimeoutError:
                print(f"     ⏰ Timeout after {timeout}s - source may be slow")
                # Cancel the future if possible
                future.cancel()
                return []
                
    except Exception as e:
        print(f"     ❌ Scraping error: {e}")
        raise e


def scrape_youtube(url: str, max_items: int):
    """
    Scrape a YouTube channel URL: return up to max_items latest videos with transcripts when available.
    Steps:
      1) Resolve channel_id from URL (supports /channel/UC..., /@handle, /c/ custom).
      2) Read channel RSS to get latest videos (no API key).
      3) For each video, fetch transcript (en/hi) and include as article content.
    """
    print("      🎥 Detected: YouTube")
    try:
        # Accept direct feed URL or resolve channel id
        if "feeds/videos.xml" in url:
            rss_url = url
        else:
            channel_id = extract_youtube_channel_id(url)
            if not channel_id:
                channel_id = resolve_channel_id_from_html(url)
            if not channel_id:
                print("      ⚠️  Couldn't extract channel ID from URL")
                return []
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

        # Limit to 3 per spec, short-circuit when we have enough
        target = min(max_items, 3)
        videos = fetch_latest_videos_from_rss(rss_url, limit=target)
        articles: List[Dict] = []
        for v in videos:
            transcript_text = get_youtube_transcript_safe(v['url'])
            # Guarantee non-empty content (fallback to title blurb)
            content = (transcript_text or v.get('summary') or f"Video: {v['title']} — Watch for details." )[:1500]
            articles.append({
                'source': v['url'],
                'title': v['title'],
                'content': content,
                'published': v.get('published')
            })
            if len(articles) >= target:
                break
        return articles
    except Exception as e:
        print(f"      ❌ YouTube scraping error: {e}")
        return []


def scrape_twitter(url: str, max_items: int):
    """
    Scrape Twitter/X account using LLM-powered username extraction
    Uses multiple nitter instances with health checking and fallback methods
    """
    print("      🐦 Detected: Twitter/X")
    
    try:
        # Use LLM to extract username more reliably
        username = extract_twitter_username_with_llm(url)
        
        if not username:
            print(f"      ❌ Could not extract username from: {url}")
            return []
        
        print(f"      📝 Extracted username: {username}")
        
        # Check nitter instance health first
        working_instances = check_nitter_instances_health()
        
        if not working_instances:
            print(f"      ⚠️ No nitter instances are currently working")
            print(f"      🔄 Trying alternative Twitter scraping methods...")
            return scrape_twitter_alternative(username, max_items)
        
        # Try working nitter instances
        for instance in working_instances:
            try:
                nitter_url = f"{instance}/{username}/rss"
                print(f"      🔄 Trying: {instance}")
                
                articles = scrape_rss(nitter_url, max_items)
                if articles:
                    print(f"      ✅ Success with: {instance}")
                    return articles
                    
                # Small delay between attempts
                import time
                time.sleep(1)
                
            except Exception as e:
                print(f"      ⚠️ {instance} failed: {e}")
                continue
        
        print(f"      ❌ All nitter instances failed for username: {username}")
        print(f"      🔄 Trying alternative Twitter scraping methods...")
        return scrape_twitter_alternative(username, max_items)
    
    except Exception as e:
        print(f"      ❌ Twitter scraping error: {e}")
        return []


def check_nitter_instances_health():
    """
    Check which nitter instances are currently working
    """
    import requests
    import time
    
    nitter_instances = [
        "https://nitter.net",
        "https://nitter.poast.org", 
        "https://nitter.privacydev.net",
        "https://nitter.1d4.us",
        "https://nitter.kavin.rocks"
    ]
    
    working_instances = []
    
    for instance in nitter_instances:
        try:
            # Quick health check - try to access the instance
            response = requests.get(instance, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; NitterBot/1.0)'
            })
            
            if response.status_code == 200:
                working_instances.append(instance)
                print(f"      ✅ {instance} is working")
            else:
                print(f"      ❌ {instance} returned status {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ {instance} health check failed: {e}")
            continue
    
    print(f"      📊 Found {len(working_instances)} working nitter instances")
    return working_instances


def scrape_twitter_alternative(username: str, max_items: int):
    """
    Alternative Twitter scraping methods when nitter fails
    """
    print(f"      🔄 Trying alternative methods for @{username}")
    
    # Method 1: Try Twitter's official RSS (if available)
    try:
        official_rss_url = f"https://twitter.com/{username}/rss"
        articles = scrape_rss(official_rss_url, max_items)
        if articles:
            print(f"      ✅ Official Twitter RSS worked")
            return articles
    except Exception as e:
        print(f"      ⚠️ Official Twitter RSS failed: {e}")
    
    # Method 2: Try alternative nitter instances
    alternative_instances = [
        "https://nitter.1d4.us",
        "https://nitter.kavin.rocks",
        "https://nitter.unixfox.eu",
        "https://nitter.domain.glass"
    ]
    
    for instance in alternative_instances:
        try:
            nitter_url = f"{instance}/{username}/rss"
            print(f"      🔄 Trying alternative: {instance}")
            
            articles = scrape_rss(nitter_url, max_items)
            if articles:
                print(f"      ✅ Alternative instance worked: {instance}")
                return articles
                
            time.sleep(1)
            
        except Exception as e:
            print(f"      ⚠️ {instance} failed: {e}")
            continue
    
    # Method 3: Create placeholder content when all methods fail
    print(f"      📝 Creating placeholder content for @{username}")
    return [{
        'source': f"https://x.com/{username}",
        'title': f"Recent posts from @{username}",
        'content': f"Unable to fetch recent posts from @{username}. The Twitter/X account may be private, suspended, or nitter instances may be temporarily unavailable. Please try again later or check the account manually.",
        'published': None,
        'author': username
    }]


def extract_twitter_username_with_llm(url: str) -> str:
    """
    Use LLM to extract Twitter username from various URL formats
    More reliable than regex patterns
    """
    try:
        from groq import Groq
        
        client = Groq(api_key=get_config("GROQ_API_KEY"))
        
        prompt = f"""Extract the Twitter/X username from this URL. Return ONLY the username without @ symbol.

URL: {url}

Examples:
- https://x.com/elonmusk → elonmusk
- https://twitter.com/OpenAI → OpenAI  
- https://x.com/xai/status/123456 → xai
- https://mobile.twitter.com/samaltman → samaltman
- @username → username

Return only the username, nothing else."""

        response = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=50
        )
        
        username = response.choices[0].message.content.strip()
        
        # Basic validation
        if username and len(username) <= 15 and username.replace('_', '').replace('-', '').isalnum():
            return username
        else:
            # Fallback to simple extraction
            return extract_twitter_username_simple(url)
            
    except Exception as e:
        print(f"      ⚠️ LLM username extraction failed: {e}")
        return extract_twitter_username_simple(url)


def extract_twitter_username_simple(url: str) -> str:
    """
    Simple fallback username extraction
    """
    import re
    
    # Remove @ symbol and clean URL
    url = url.replace('@', '')
    
    # Try different patterns
    patterns = [
        r'(?:https?://)?(?:www\.)?(?:mobile\.)?(?:x\.com|twitter\.com)/([^/]+)',
        r'([a-zA-Z0-9_]{1,15})',  # Basic username pattern
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            username = match.group(1)
            # Validate username format
            if re.match(r'^[a-zA-Z0-9_]{1,15}$', username):
                return username
    
    return None


def scrape_reddit_url(url: str, max_items: int):
    """
    Scrape Reddit subreddit
    Uses Reddit JSON API (free, no auth needed)
    """
    print("      🤖 Detected: Reddit")
    
    try:
        # Extract subreddit from URL
        # https://www.reddit.com/r/ArtificialInteligence/ → ArtificialInteligence
        if '/r/' not in url:
            return []
        
        subreddit = url.split('/r/')[1].split('/')[0]
        api_url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={max_items}"
        
        # Use existing Reddit scraper
        return scrape_reddit_source({'url': api_url}, {})
    
    except Exception as e:
        print(f"      ❌ Reddit scraping error: {e}")
        return []


def scrape_hackernews_url(url: str, max_items: int):
    """Scrape Hacker News (uses existing scraper)"""
    print("      🔶 Detected: Hacker News")
    
    try:
        # If it's already an API URL, use it
        if 'hn.algolia.com' in url:
            return scrape_api_source({'url': url}, {})
        
        # Otherwise, construct search URL
        api_url = f'https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage={max_items}'
        return scrape_api_source({'url': api_url}, {})
    
    except Exception as e:
        print(f"      ❌ Hacker News scraping error: {e}")
        return []


def scrape_rss(url: str, max_items: int):
    """
    Enhanced RSS scraper with LLM content validation
    Works with any RSS/Atom feed
    """
    try:
        import feedparser
        
        # Add proper headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; RSSBot/1.0)',
            'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml'
        }
        
        feed = feedparser.parse(url)
        
        if not feed.entries:
            print(f"      ⚠️ No entries found in RSS feed: {url}")
            return []
        
        articles = []
        for entry in feed.entries[:max_items]:
            # Enhanced content extraction
            content = extract_enhanced_rss_content(entry)
            
            # Use LLM to validate content quality
            if content and validate_content_with_llm(content, entry.get('title', '')):
                articles.append({
                    'source': entry.get('link', url),
                    'title': entry.get('title', 'Untitled')[:200],  # Limit title length
                    'content': content[:1500],
                    'published': entry.get('published', ''),
                    'author': entry.get('author', ''),
                    'tags': [tag.term for tag in entry.get('tags', [])]
                })
        
        print(f"      ✅ RSS: Found {len(articles)} valid articles from {len(feed.entries)} entries")
        return articles
    
    except ImportError:
        print("      ❌ feedparser not installed. Run: pip install feedparser")
        return []
    except Exception as e:
        print(f"      ❌ RSS parsing error: {e}")
        return []


def extract_enhanced_rss_content(entry) -> str:
    """
    Extract content with multiple fallback strategies
    """
    # Try different content fields
    content_fields = [
        'content',
        'summary', 
        'description',
        'summary_detail',
        'content_detail'
    ]
    
    for field in content_fields:
        content = entry.get(field, '')
        if isinstance(content, dict):
            content = content.get('value', '')
        
        if content and len(content.strip()) > 50:
            # Clean HTML tags
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            return soup.get_text().strip()
    
    return ''


def validate_content_with_llm(content: str, title: str) -> bool:
    """
    Use LLM to validate if content is meaningful and relevant
    """
    try:
        from groq import Groq
        import os
        
        # Skip LLM validation for very short content
        if len(content) < 100:
            return len(content) > 50
        
        client = Groq(api_key=get_config("GROQ_API_KEY"))
        
        prompt = f"""Is this content meaningful and worth including in a newsletter? Answer YES or NO only.

Title: {title[:100]}
Content: {content[:500]}

Consider:
- Is it informative or just promotional?
- Does it have substance or is it just a link?
- Is it relevant for a general tech/AI audience?

Answer: YES or NO"""

        response = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip().upper()
        return result == 'YES'
        
    except Exception as e:
        print(f"      ⚠️ LLM content validation failed: {e}")
        # Fallback: accept content if it's reasonably long
        return len(content) > 100


def scrape_generic_website(url: str, max_items: int):
    """
    Fallback for any website
    1. Try to find RSS feed automatically
    2. If no RSS, use web scraping
    """
    try:
        # Try common RSS URL patterns
        parsed = urlparse(url)
        domain = parsed.netloc
        base_url = f"{parsed.scheme}://{domain}"
        
        common_rss_paths = [
            f"{url}/feed",
            f"{url}/rss",
            f"{url}/feed.xml",
            f"{url}/atom.xml",
            f"{base_url}/feed",
            f"{base_url}/rss",
        ]
        
        for rss_url in common_rss_paths:
            articles = scrape_rss(rss_url, max_items)
            if articles:
                print(f"      ✅ Found RSS feed at: {rss_url}")
                return articles
        
        return []
    
    except Exception as e:
        print(f"      ❌ Generic website error: {e}")
        return []


def extract_youtube_channel_id(url: str) -> Optional[str]:
    """
    Extract YouTube channel ID from URL
    Handles: /channel/UCxyz, /@handle
    """
    # Direct channel ID URL
    if '/channel/' in url:
        return url.split('/channel/')[1].split('/')[0].split('?')[0]
    
    # Handle format (@username) or /c/<custom> - try HTML lookup for channelId
    return None


def resolve_channel_id_from_html(url: str) -> Optional[str]:
    """Resolve channel id for /@handle or /c/custom using HTML or oEmbed fallback."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept-Language': 'en'
    }
    cookies = { 'CONSENT': 'YES+1' }
    try:
        for attempt in range(2):
            resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
            if resp.status_code >= 500:
                time.sleep(0.5 * (attempt + 1))
                continue
            resp.raise_for_status()
            import re
            # Try canonical link first
            m = re.search(r'<link\s+rel="canonical"\s+href="https://www.youtube.com/channel/(UC[0-9A-Za-z_-]{22})"', resp.text)
            if m:
                return m.group(1)
            # Try JSON channelId
            m = re.search(r'"channelId"\s*:\s*"(UC[0-9A-Za-z_-]{22})"', resp.text)
            if m:
                return m.group(1)
            break
    except Exception as e:
        print(f"      ⚠️ Channel HTML lookup failed: {e}")
    # oEmbed fallback
    try:
        oembed = requests.get("https://www.youtube.com/oembed", params={"url": url, "format": "json"}, headers=headers, timeout=10)
        if oembed.ok:
            data = oembed.json()
            author_url = data.get('author_url')  # often https://www.youtube.com/channel/UC...
            if author_url and '/channel/' in author_url:
                return author_url.rstrip('/').split('/channel/')[1]
    except Exception as e:
        print(f"      ⚠️ oEmbed lookup failed: {e}")
    return None


def fetch_latest_videos_from_rss(rss_url: str, limit: int = 3) -> List[Dict]:
    """Read YouTube channel RSS and return latest videos as dicts with url/title/published/summary."""
    try:
        import feedparser
        # Fetch with headers for reliability, then parse content
        headers = { 'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en' }
        content = None
        for attempt in range(2):
            try:
                r = requests.get(rss_url, headers=headers, timeout=10)
                if r.status_code >= 500:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                r.raise_for_status()
                content = r.content
                break
            except Exception:
                if attempt == 1:
                    raise
        feed = feedparser.parse(content if content is not None else rss_url)
        videos: List[Dict] = []
        for entry in feed.entries[:limit]:
            # Prefer yt:videoId to build canonical URL
            vid = entry.get('yt_videoid') or entry.get('yt_video_id')
            link = entry.get('link')
            if not vid and link:
                # try to parse v= from link
                try:
                    from urllib.parse import urlparse, parse_qs
                    q = parse_qs(urlparse(link).query)
                    vid = (q.get('v') or [None])[0]
                except Exception:
                    vid = None
            video_url = f"https://www.youtube.com/watch?v={vid}" if vid else (link or '')
            if not video_url:
                continue
            videos.append({
                'url': video_url,
                'title': entry.get('title', ''),
                'published': entry.get('published', ''),
                'summary': entry.get('summary', '')
            })
        return videos
    except Exception as e:
        print(f"      ⚠️ RSS read failed: {e}")
        return []


def get_youtube_transcript_safe(video_url: str) -> Optional[str]:
    """Best-effort transcript fetch (en/hi). Returns text or None. Uses youtube_transcript_api and langdetect."""
    try:
        video_id = get_youtube_video_id(video_url)
        if not video_id:
            return None
        # Try English transcripts only (temporary: disable Hindi path)
        data = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US"]) 
        text = " ".join(chunk.get("text", "") for chunk in data if chunk.get("text"))
        if not text:
            return None
        return text
    except TranscriptsDisabled:
        return None
    except NoTranscriptFound:
        return None
    except Exception:
        return None


# ============================================================================
# END OF NEW DYNAMIC SCRAPING
# ============================================================================

# Main function
# Main function is now scrape_sources at the top of the file (for backward compatibility)
