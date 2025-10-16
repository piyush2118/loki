"""
Firecrawl Client - Layer 3: Intelligent Web Crawling Integration
Provides intelligent web crawling for discovered trends and content discovery
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
import streamlit as st

try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    print("Warning: firecrawl-py not available. Install with: pip install firecrawl-py")

class FirecrawlClient:
    """Client for intelligent web crawling using Firecrawl"""
    
    def __init__(self):
        self.app = None
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        
        if FIRECRAWL_AVAILABLE and self.api_key:
            try:
                self.app = FirecrawlApp(api_key=self.api_key)
            except Exception as e:
                print(f"Error initializing Firecrawl client: {e}")
        else:
            print("Firecrawl not available - API key missing or package not installed")
    
    def crawl_url(self, url: str, max_pages: int = 1) -> Dict:
        """
        Crawl a single URL and extract structured content
        """
        if not self.app:
            return {'error': 'Firecrawl not available'}
        
        try:
            # Crawl the URL
            crawl_result = self.app.crawl_url(
                url=url,
                params={
                    'crawlerOptions': {
                        'maxDepth': 1,
                        'maxPages': max_pages
                    },
                    'pageOptions': {
                        'includeHtml': False,
                        'includeMarkdown': True
                    }
                }
            )
            
            if crawl_result and 'data' in crawl_result:
                return {
                    'success': True,
                    'url': url,
                    'pages': crawl_result['data'],
                    'crawled_at': datetime.now().isoformat()
                }
            else:
                return {'error': 'No data returned from crawl'}
                
        except Exception as e:
            return {'error': f'Crawl failed: {str(e)}'}
    
    def scrape_url(self, url: str) -> Dict:
        """
        Scrape a single URL for content
        """
        if not self.app:
            return {'error': 'Firecrawl not available'}
        
        try:
            # Scrape the URL
            scrape_result = self.app.scrape_url(
                url=url,
                params={
                    'formats': ['markdown', 'html'],
                    'includeTags': ['title', 'meta', 'h1', 'h2', 'h3', 'p', 'a'],
                    'excludeTags': ['script', 'style', 'nav', 'footer']
                }
            )
            
            if scrape_result and 'data' in scrape_result:
                data = scrape_result['data']
                return {
                    'success': True,
                    'url': url,
                    'title': data.get('metadata', {}).get('title', ''),
                    'content': data.get('markdown', ''),
                    'html': data.get('html', ''),
                    'metadata': data.get('metadata', {}),
                    'scraped_at': datetime.now().isoformat()
                }
            else:
                return {'error': 'No data returned from scrape'}
                
        except Exception as e:
            return {'error': f'Scrape failed: {str(e)}'}
    
    def discover_content_for_trends(self, trends: List[str], max_results: int = 5) -> List[Dict]:
        """
        Discover content related to trending topics
        """
        if not self.app:
            return []
        
        discovered_content = []
        
        for trend in trends[:3]:  # Limit to avoid rate limits
            try:
                # Search for content related to this trend
                search_result = self.app.search(
                    query=trend,
                    num_results=max_results,
                    search_options={
                        'type': 'search',
                        'freshness': 'week'
                    }
                )
                
                if search_result and 'data' in search_result:
                    for item in search_result['data']:
                        discovered_content.append({
                            'trend': trend,
                            'title': item.get('title', ''),
                            'url': item.get('url', ''),
                            'snippet': item.get('snippet', ''),
                            'discovered_at': datetime.now().isoformat()
                        })
                
            except Exception as e:
                print(f"Error discovering content for trend '{trend}': {e}")
                continue
        
        return discovered_content
    
    def crawl_trending_sources(self, urls: List[str], max_pages_per_source: int = 2) -> List[Dict]:
        """
        Crawl multiple trending sources
        """
        if not self.app:
            return []
        
        crawled_sources = []
        
        for url in urls[:5]:  # Limit to avoid rate limits
            try:
                result = self.crawl_url(url, max_pages_per_source)
                if result.get('success'):
                    crawled_sources.append(result)
                
            except Exception as e:
                print(f"Error crawling source '{url}': {e}")
                continue
        
        return crawled_sources
    
    def extract_structured_data(self, url: str) -> Dict:
        """
        Extract structured data from a URL
        """
        if not self.app:
            return {'error': 'Firecrawl not available'}
        
        try:
            # Use Firecrawl's structured extraction
            result = self.app.scrape_url(
                url=url,
                params={
                    'formats': ['markdown'],
                    'extractorOptions': {
                        'mode': 'llm-extraction',
                        'extractionPrompt': """
                        Extract the following information from this content:
                        1. Main topic or subject
                        2. Key points or insights
                        3. Important dates or events
                        4. People or organizations mentioned
                        5. Technologies or tools discussed
                        
                        Format as JSON with these fields.
                        """
                    }
                }
            )
            
            if result and 'data' in result:
                return {
                    'success': True,
                    'url': url,
                    'structured_data': result['data'],
                    'extracted_at': datetime.now().isoformat()
                }
            else:
                return {'error': 'No structured data extracted'}
                
        except Exception as e:
            return {'error': f'Extraction failed: {str(e)}'}
    
    def find_related_sources(self, topic: str, max_sources: int = 10) -> List[Dict]:
        """
        Find related sources for a given topic
        """
        if not self.app:
            return []
        
        try:
            # Search for related content
            search_result = self.app.search(
                query=topic,
                num_results=max_sources,
                search_options={
                    'type': 'search',
                    'freshness': 'month'
                }
            )
            
            related_sources = []
            if search_result and 'data' in search_result:
                for item in search_result['data']:
                    related_sources.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'snippet': item.get('snippet', ''),
                        'relevance_score': 0.8,  # Default score
                        'topic': topic,
                        'found_at': datetime.now().isoformat()
                    })
            
            return related_sources
            
        except Exception as e:
            print(f"Error finding related sources for '{topic}': {e}")
            return []
    
    def analyze_content_gaps(self, user_sources: List[str], trending_topics: List[str]) -> Dict:
        """
        Analyze gaps in user's content coverage based on trending topics
        """
        if not self.app:
            return {'error': 'Firecrawl not available'}
        
        gaps = {
            'missing_topics': [],
            'suggested_sources': [],
            'coverage_analysis': {}
        }
        
        for topic in trending_topics:
            # Find sources that cover this topic
            related_sources = self.find_related_sources(topic, max_sources=5)
            
            # Check if user already has similar sources
            user_has_coverage = False
            for user_source in user_sources:
                for related_source in related_sources:
                    if self._sources_similar(user_source, related_source['url']):
                        user_has_coverage = True
                        break
                if user_has_coverage:
                    break
            
            if not user_has_coverage and related_sources:
                gaps['missing_topics'].append({
                    'topic': topic,
                    'suggested_sources': related_sources[:3],
                    'gap_severity': 'high' if len(related_sources) > 3 else 'medium'
                })
        
        # Generate coverage analysis
        gaps['coverage_analysis'] = {
            'total_topics_analyzed': len(trending_topics),
            'topics_with_coverage': len(trending_topics) - len(gaps['missing_topics']),
            'coverage_percentage': ((len(trending_topics) - len(gaps['missing_topics'])) / len(trending_topics)) * 100 if trending_topics else 0
        }
        
        return gaps
    
    def _sources_similar(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from similar sources"""
        try:
            from urllib.parse import urlparse
            domain1 = urlparse(url1).netloc
            domain2 = urlparse(url2).netloc
            
            # Simple similarity check
            return domain1 == domain2 or domain1 in domain2 or domain2 in domain1
        except:
            return False
    
    def get_intelligence_summary(self, user_sources: List[str], trending_topics: List[str]) -> Dict:
        """
        Get a comprehensive intelligence summary
        """
        summary = {
            'timestamp': datetime.now().isoformat(),
            'user_sources_count': len(user_sources),
            'trending_topics_count': len(trending_topics),
            'content_gaps': {},
            'discovered_content': [],
            'recommendations': []
        }
        
        if not self.app:
            summary['error'] = 'Firecrawl not available'
            return summary
        
        # Analyze content gaps
        summary['content_gaps'] = self.analyze_content_gaps(user_sources, trending_topics)
        
        # Discover content for trending topics
        summary['discovered_content'] = self.discover_content_for_trends(trending_topics, max_results=3)
        
        # Generate recommendations
        if summary['content_gaps']['missing_topics']:
            for gap in summary['content_gaps']['missing_topics'][:3]:
                summary['recommendations'].append(
                    f"Consider adding sources for '{gap['topic']}' - {gap['gap_severity']} priority"
                )
        
        return summary

# Create singleton instance
firecrawl_client = FirecrawlClient()
