# Dynamic source management for AI Newsletter MVP
# Supports user-specific custom sources

from urllib.parse import urlparse
from datetime import datetime, timezone

# CRITICAL: reuse the authenticated Supabase client so RLS policies see auth.uid()
from utils.auth import supabase

class SourceManager:
    """Simple source management - users can add any URL"""
    
    def add_source(self, user_id: str, url: str, display_name: str = None, priority: int = 5):
        """Add a source - validates URL and stores it"""
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            return {'success': False, 'error': 'URL must start with http:// or https://'}
        
        # Auto-generate display name if not provided
        if not display_name:
            try:
                domain = urlparse(url).netloc.replace('www.', '')
                display_name = domain.split('.')[0].title()
            except:
                display_name = url[:50]  # Fallback to truncated URL
        
        try:
            result = supabase.table('user_sources').insert({
                'user_id': user_id,
                'source_url': url,
                'display_name': display_name,
                'priority': priority
            }).execute()
            
            return {'success': True, 'data': result.data}
        
        except Exception as e:
            error_msg = str(e).lower()
            if 'unique constraint' in error_msg or 'duplicate' in error_msg:
                return {'success': False, 'error': 'You already have this source added'}
            return {'success': False, 'error': str(e)}
    
    def bulk_add_sources(self, user_id: str, urls: list, display_names: list = None):
        """Add multiple sources at once"""
        results = {'success': [], 'failed': []}
        
        for i, url in enumerate(urls):
            display_name = display_names[i] if display_names and i < len(display_names) else None
            result = self.add_source(user_id, url, display_name)
            
            if result['success']:
                results['success'].append(url)
            else:
                results['failed'].append({'url': url, 'error': result['error']})
        
        return results
    
    def get_user_sources(self, user_id: str, active_only: bool = True):
        """Get all sources for a user"""
        try:
            query = supabase.table('user_sources')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('priority', desc=True)
            
            if active_only:
                query = query.eq('active', True)
            
            result = query.execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting user sources: {e}")
            return []
    
    def remove_source(self, source_id: str):
        """Remove a source"""
        try:
            supabase.table('user_sources').delete().eq('id', source_id).execute()
            return True
        except Exception as e:
            print(f"Error removing source: {e}")
            return False
    
    def toggle_source(self, source_id: str):
        """Toggle active state"""
        try:
            # Fetch current state
            source = supabase.table('user_sources')\
                .select('active')\
                .eq('id', source_id)\
                .single()\
                .execute()
            
            if not source.data:
                return False
            
            # Toggle it
            supabase.table('user_sources')\
                .update({'active': not source.data['active']})\
                .eq('id', source_id)\
                .execute()
            
            return True
        except Exception as e:
            print(f"Error toggling source: {e}")
            return False
    
    def update_scrape_timestamp(self, source_id: str):
        """Update last_scraped_at timestamp"""
        try:
            supabase.table('user_sources')\
                .update({'last_scraped_at': datetime.now(timezone.utc).isoformat()})\
                .eq('id', source_id)\
                .execute()
        except Exception as e:
            print(f"Error updating scrape timestamp: {e}")
    
    def initialize_default_sources(self, user_id: str, category: str = 'AI'):
        """Give new users starter sources based on category"""
        default_sources = {
            'AI': [
                ('https://openai.com/blog/', 'OpenAI Blog'),
                ('https://www.anthropic.com/news', 'Anthropic News'),
                ('https://www.deepmind.com/blog', 'DeepMind Blog'),
                ('https://www.reddit.com/r/artificial/', 'r/artificial')
            ],
            'Machine Learning': [
                ('https://distill.pub/', 'Distill'),
                ('https://blog.tensorflow.org/', 'TensorFlow Blog'),
                ('https://pytorch.org/blog/', 'PyTorch Blog'),
                ('https://www.reddit.com/r/MachineLearning/', 'r/MachineLearning')
            ],
            'Data Science': [
                ('https://towardsdatascience.com/', 'Towards Data Science'),
                ('https://www.kaggle.com/blog', 'Kaggle Blog'),
                ('https://www.reddit.com/r/datascience/', 'r/datascience')
            ],
            'Technology': [
                ('https://techcrunch.com/', 'TechCrunch'),
                ('https://www.theverge.com/', 'The Verge'),
                ('https://news.ycombinator.com/', 'Hacker News'),
                ('https://www.reddit.com/r/technology/', 'r/technology')
            ]
        }
        
        sources_to_add = default_sources.get(category, default_sources['AI'])
        
        for url, name in sources_to_add:
            self.add_source(user_id, url, name, priority=5)
        
        return len(sources_to_add)

# Create singleton instance
source_manager = SourceManager()

# BACKWARD COMPATIBILITY: Keep old NEWS_SOURCES for gradual migration
NEWS_SOURCES = {
    'AI': {
        'name': 'Artificial Intelligence',
        'api_sources': [
            'https://hn.algolia.com/api/v1/search_by_date?query=AI&tags=story&hitsPerPage=10',
            'https://www.reddit.com/r/artificial/hot.json?limit=5',
            'http://export.arxiv.org/api/query?search_query=cat:cs.AI&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending',
        ]
    },
    'Machine Learning': {
        'name': 'Machine Learning',
        'api_sources': [
            'https://hn.algolia.com/api/v1/search_by_date?query=machine+learning&tags=story&hitsPerPage=10',
            'https://www.reddit.com/r/MachineLearning/hot.json?limit=5',
            'http://export.arxiv.org/api/query?search_query=cat:cs.LG&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending',
        ]
    },
    'Data Science': {
        'name': 'Data Science',
        'api_sources': [
            'https://hn.algolia.com/api/v1/search_by_date?query=data+science&tags=story&hitsPerPage=10',
            'https://www.reddit.com/r/datascience/hot.json?limit=5',
        ]
    },
    'Technology': {
        'name': 'Technology',
        'api_sources': [
            'https://hn.algolia.com/api/v1/search_by_date?query=technology&tags=story&hitsPerPage=10',
            'https://www.reddit.com/r/technology/hot.json?limit=5',
        ]
    }
}
