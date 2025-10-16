"""
Trend Analysis Module - Layer 1: Basic Trend Detection Infrastructure
Analyzes scraped content to identify trending topics using frequency analysis and NLP
"""

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import streamlit as st
import os
from groq import Groq
import statistics
import numpy as np

class TrendAnalyzer:
    """Basic trend detection using frequency analysis and simple NLP"""
    
    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
    
    def extract_keywords(self, text: str, min_length: int = 3) -> List[str]:
        """Extract keywords from text using simple word frequency"""
        # Clean and tokenize
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()
        
        # Filter out stop words and short words
        keywords = [word for word in words 
                   if word not in self.stop_words and len(word) >= min_length]
        
        return keywords
    
    def extract_ngrams(self, text: str, n: int = 2) -> List[str]:
        """Extract n-grams from text"""
        words = re.sub(r'[^\w\s]', ' ', text.lower()).split()
        ngrams = []
        
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n])
            if not any(word in self.stop_words for word in words[i:i+n]):
                ngrams.append(ngram)
        
        return ngrams
    
    def analyze_article_frequency(self, articles: List[Dict]) -> Dict[str, int]:
        """Analyze keyword frequency across articles"""
        all_keywords = []
        all_bigrams = []
        
        for article in articles:
            content = article.get('content', '') + ' ' + article.get('title', '')
            keywords = self.extract_keywords(content)
            bigrams = self.extract_ngrams(content, 2)
            
            all_keywords.extend(keywords)
            all_bigrams.extend(bigrams)
        
        # Count frequencies
        keyword_counts = Counter(all_keywords)
        bigram_counts = Counter(all_bigrams)
        
        return {
            'keywords': dict(keyword_counts.most_common(20)),
            'bigrams': dict(bigram_counts.most_common(15))
        }
    
    def calculate_source_diversity(self, articles: List[Dict]) -> Dict[str, int]:
        """Calculate source diversity metrics"""
        source_counts = Counter()
        domain_counts = Counter()
        
        for article in articles:
            source = article.get('source', '')
            if source:
                source_counts[source] += 1
                # Extract domain
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(source).netloc
                    domain_counts[domain] += 1
                except:
                    pass
        
        return {
            'unique_sources': len(source_counts),
            'unique_domains': len(domain_counts),
            'source_distribution': dict(source_counts.most_common(10)),
            'domain_distribution': dict(domain_counts.most_common(10))
        }
    
    def detect_emerging_topics(self, articles: List[Dict]) -> List[Dict]:
        """Detect emerging topics using frequency analysis"""
        frequency_data = self.analyze_article_frequency(articles)
        source_data = self.calculate_source_diversity(articles)
        
        # Combine keywords and bigrams for topic detection
        all_topics = []
        
        # Add high-frequency keywords as topics
        for keyword, count in frequency_data['keywords'].items():
            if count >= 2:  # Minimum threshold
                all_topics.append({
                    'topic': keyword,
                    'type': 'keyword',
                    'frequency': count,
                    'relevance_score': count / len(articles) if articles else 0
                })
        
        # Add high-frequency bigrams as topics
        for bigram, count in frequency_data['bigrams'].items():
            if count >= 2:  # Minimum threshold
                all_topics.append({
                    'topic': bigram,
                    'type': 'bigram',
                    'frequency': count,
                    'relevance_score': count / len(articles) if articles else 0
                })
        
        # Sort by relevance score
        all_topics.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return all_topics[:15]  # Top 15 topics
    
    def generate_trend_report(self, articles: List[Dict]) -> Dict:
        """Generate comprehensive trend report"""
        if not articles:
            return {
                'trends': [],
                'metrics': {},
                'summary': 'No articles available for analysis'
            }
        
        trends = self.detect_emerging_topics(articles)
        source_metrics = self.calculate_source_diversity(articles)
        frequency_data = self.analyze_article_frequency(articles)
        
        # Calculate overall metrics
        total_articles = len(articles)
        avg_content_length = sum(len(article.get('content', '')) for article in articles) / total_articles
        
        return {
            'trends': trends,
            'metrics': {
                'total_articles': total_articles,
                'unique_sources': source_metrics['unique_sources'],
                'unique_domains': source_metrics['unique_domains'],
                'avg_content_length': int(avg_content_length),
                'top_keywords': frequency_data['keywords'],
                'top_bigrams': frequency_data['bigrams'],
                'source_distribution': source_metrics['source_distribution']
            },
            'summary': f"Analyzed {total_articles} articles from {source_metrics['unique_sources']} sources"
        }
    
    def get_trending_topics(self, articles: List[Dict], limit: int = 10) -> List[Dict]:
        """Get top trending topics with metadata"""
        trends = self.detect_emerging_topics(articles)
        
        # Add supporting articles for each trend
        for trend in trends:
            trend['supporting_articles'] = []
            topic = trend['topic'].lower()
            
            for article in articles:
                content = (article.get('content', '') + ' ' + article.get('title', '')).lower()
                if topic in content:
                    trend['supporting_articles'].append({
                        'title': article.get('title', ''),
                        'source': article.get('source', ''),
                        'published': article.get('published', '')
                    })
            
            # Limit supporting articles
            trend['supporting_articles'] = trend['supporting_articles'][:3]
        
        return trends[:limit]
    
    def analyze_trends_with_llm(self, articles: List[Dict]) -> List[Dict]:
        """
        Layer 2: LLM-Powered Trend Analysis
        Use Groq LLM to identify meaningful patterns, emerging topics, and semantic clustering
        """
        if not articles:
            return []
        
        try:
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            
            # Prepare context for LLM
            context = "\n\n".join([
                f"Title: {a['title']}\nContent: {a['content'][:500]}..."
                for a in articles[:10]  # Limit to avoid token limits
            ])
            
            prompt = f"""Analyze the following articles and identify emerging trends, patterns, and meaningful topics.

ARTICLES:
{context}

INSTRUCTIONS:
1. Identify 5-8 emerging trends or topics from these articles
2. For each trend, provide:
   - A clear, descriptive name (2-4 words)
   - A brief description (1-2 sentences)
   - Relevance score (0.0-1.0)
   - Category (e.g., "Technology", "AI", "Business", "Science")
   - Supporting evidence from the articles

3. Focus on:
   - New developments or breakthroughs
   - Recurring themes across multiple articles
   - Emerging technologies or concepts
   - Industry shifts or changes

4. Format your response as JSON:
{{
  "trends": [
    {{
      "name": "Trend Name",
      "description": "Brief description of the trend",
      "relevance_score": 0.85,
      "category": "Technology",
      "evidence": ["Article title 1", "Article title 2"],
      "keywords": ["keyword1", "keyword2", "keyword3"]
    }}
  ]
}}

Return only the JSON, no additional text."""

            response = client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            try:
                # Clean up the response to extract JSON
                if result.startswith('```json'):
                    result = result[7:]
                if result.endswith('```'):
                    result = result[:-3]
                
                llm_data = json.loads(result)
                trends = llm_data.get('trends', [])
                
                # Enhance trends with supporting articles
                for trend in trends:
                    trend['supporting_articles'] = []
                    trend['type'] = 'llm_analyzed'
                    
                    # Find supporting articles based on keywords
                    keywords = trend.get('keywords', [])
                    for article in articles:
                        content = (article.get('title', '') + ' ' + article.get('content', '')).lower()
                        if any(keyword.lower() in content for keyword in keywords):
                            trend['supporting_articles'].append({
                                'title': article.get('title', ''),
                                'source': article.get('source', ''),
                                'published': article.get('published', '')
                            })
                    
                    # Limit supporting articles
                    trend['supporting_articles'] = trend['supporting_articles'][:3]
                
                return trends
                
            except json.JSONDecodeError as e:
                print(f"Error parsing LLM response: {e}")
                print(f"Raw response: {result}")
                return []
                
        except Exception as e:
            print(f"Error in LLM trend analysis: {e}")
            return []
    
    def calculate_trend_scores(self, trends: List[Dict], articles: List[Dict]) -> List[Dict]:
        """
        Layer 2: Implement Trend Scoring Algorithm
        Calculate trend scores based on: recency, source diversity, article engagement
        Weight factors: 40% recency, 30% frequency, 30% source authority
        """
        if not trends or not articles:
            return trends
        
        # Calculate source authority scores (simple heuristic)
        source_authority = {}
        for article in articles:
            source = article.get('source', '')
            if source:
                # Simple authority scoring based on domain
                domain = source.split('/')[2] if '//' in source else source
                if 'youtube.com' in domain:
                    source_authority[source] = 0.8
                elif 'reddit.com' in domain:
                    source_authority[source] = 0.6
                elif 'github.com' in domain or 'stackoverflow.com' in domain:
                    source_authority[source] = 0.9
                else:
                    source_authority[source] = 0.7
        
        # Calculate recency scores
        now = datetime.now()
        for trend in trends:
            recency_score = 0.0
            frequency_score = 0.0
            authority_score = 0.0
            
            # Calculate frequency (how many articles mention this trend)
            trend_keywords = trend.get('keywords', [])
            supporting_articles = trend.get('supporting_articles', [])
            
            frequency_score = min(len(supporting_articles) / 5.0, 1.0)  # Normalize to 0-1
            
            # Calculate recency (how recent are the supporting articles)
            if supporting_articles:
                recent_count = 0
                for article in supporting_articles:
                    # Simple recency check - assume recent if no date or if within last 7 days
                    recent_count += 1  # Simplified for now
                recency_score = min(recent_count / len(supporting_articles), 1.0)
            else:
                recency_score = 0.5  # Default for trends without clear articles
            
            # Calculate authority score
            if supporting_articles:
                total_authority = 0
                for article in supporting_articles:
                    source = article.get('source', '')
                    total_authority += source_authority.get(source, 0.5)
                authority_score = total_authority / len(supporting_articles)
            else:
                authority_score = 0.5
            
            # Calculate composite score with weights
            composite_score = (
                0.4 * recency_score +
                0.3 * frequency_score +
                0.3 * authority_score
            )
            
            trend['composite_score'] = composite_score
            trend['recency_score'] = recency_score
            trend['frequency_score'] = frequency_score
            trend['authority_score'] = authority_score
        
        # Sort by composite score
        trends.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
        
        return trends
    
    def generate_enhanced_trend_report(self, articles: List[Dict]) -> Dict:
        """
        Layer 2: Enhanced trend report with LLM analysis and scoring
        """
        if not articles:
            return {
                'trends': [],
                'metrics': {},
                'summary': 'No articles available for analysis'
            }
        
        # Get basic trends first
        basic_trends = self.detect_emerging_topics(articles)
        
        # Get LLM-analyzed trends
        llm_trends = self.analyze_trends_with_llm(articles)
        
        # Combine and score all trends
        all_trends = basic_trends + llm_trends
        scored_trends = self.calculate_trend_scores(all_trends, articles)
        
        # Get basic metrics
        source_metrics = self.calculate_source_diversity(articles)
        frequency_data = self.analyze_article_frequency(articles)
        
        # Calculate enhanced metrics
        total_articles = len(articles)
        avg_content_length = sum(len(article.get('content', '')) for article in articles) / total_articles
        
        # Calculate trend diversity
        trend_categories = Counter(trend.get('category', 'Uncategorized') for trend in scored_trends)
        
        return {
            'trends': scored_trends[:15],  # Top 15 trends
            'metrics': {
                'total_articles': total_articles,
                'unique_sources': source_metrics['unique_sources'],
                'unique_domains': source_metrics['unique_domains'],
                'avg_content_length': int(avg_content_length),
                'trend_categories': dict(trend_categories),
                'llm_trends_count': len(llm_trends),
                'basic_trends_count': len(basic_trends),
                'top_keywords': frequency_data['keywords'],
                'top_bigrams': frequency_data['bigrams'],
                'source_distribution': source_metrics['source_distribution']
            },
            'summary': f"Analyzed {total_articles} articles from {source_metrics['unique_sources']} sources. Found {len(scored_trends)} trends with {len(llm_trends)} AI-identified patterns."
        }
    
    def correlate_with_market_trends(self, user_trends: List[Dict], user_sources: List[str]) -> Dict:
        """
        Layer 3: Trend Correlation Engine
        Match Google Trends data with scraped content and identify gaps
        """
        try:
            from utils.google_trends_client import google_trends_client
            from utils.firecrawl_client import firecrawl_client
            
            # Extract trend names from user trends
            user_trend_names = [trend.get('name', trend.get('topic', '')) for trend in user_trends]
            
            # Get market trends for relevant categories
            categories = list(set(trend.get('category', 'Technology') for trend in user_trends))
            market_trends = []
            
            for category in categories:
                category_trends = google_trends_client.get_trending_topics_for_category(category, limit=5)
                market_trends.extend([trend['query'] for trend in category_trends])
            
            # Analyze correlation
            correlation_analysis = google_trends_client.analyze_trend_correlation(user_trend_names, market_trends)
            
            # Analyze content gaps
            content_gaps = firecrawl_client.analyze_content_gaps(user_sources, market_trends)
            
            # Generate "What You're Missing" section
            missing_analysis = {
                'correlations': correlation_analysis,
                'content_gaps': content_gaps,
                'market_trends': market_trends[:10],
                'user_trends': user_trend_names,
                'recommendations': []
            }
            
            # Generate recommendations
            if content_gaps.get('missing_topics'):
                for gap in content_gaps['missing_topics'][:3]:
                    missing_analysis['recommendations'].append({
                        'type': 'source_suggestion',
                        'topic': gap['topic'],
                        'priority': gap['gap_severity'],
                        'suggested_sources': gap['suggested_sources'][:2]
                    })
            
            if correlation_analysis.get('correlations'):
                for correlation in correlation_analysis['correlations'][:3]:
                    if correlation['similarity'] > 0.7:
                        missing_analysis['recommendations'].append({
                            'type': 'trend_alignment',
                            'user_trend': correlation['user_trend'],
                            'market_trend': correlation['market_trend'],
                            'similarity': correlation['similarity']
                        })
            
            return missing_analysis
            
        except Exception as e:
            print(f"Error in trend correlation: {e}")
            return {
                'error': str(e),
                'correlations': {},
                'content_gaps': {},
                'recommendations': []
            }
    
    def generate_market_intelligence_report(self, articles: List[Dict], user_sources: List[str]) -> Dict:
        """
        Layer 3: Generate comprehensive market intelligence report
        """
        if not articles:
            return {
                'user_trends': [],
                'market_intelligence': {},
                'correlation_analysis': {},
                'recommendations': []
            }
        
        # Get enhanced user trends
        user_trend_report = self.generate_enhanced_trend_report(articles)
        user_trends = user_trend_report['trends']
        
        # Correlate with market trends
        correlation_analysis = self.correlate_with_market_trends(user_trends, user_sources)
        
        # Get market intelligence summary
        try:
            from utils.google_trends_client import google_trends_client
            categories = list(set(trend.get('category', 'Technology') for trend in user_trends))
            market_intelligence = google_trends_client.get_market_intelligence_summary(categories)
        except:
            market_intelligence = {}
        
        return {
            'user_trends': user_trends,
            'market_intelligence': market_intelligence,
            'correlation_analysis': correlation_analysis,
            'recommendations': correlation_analysis.get('recommendations', []),
            'summary': f"Analyzed {len(user_trends)} user trends against market intelligence. Found {len(correlation_analysis.get('correlations', {}).get('correlations', []))} correlations."
        }
    
    def detect_spikes(self, trend_data: List[Dict], window_size: int = 7) -> List[Dict]:
        """
        Layer 4: Statistical Spike Detection Algorithm
        Implement Z-score, moving averages, and percentile-based spike detection
        """
        if not trend_data or len(trend_data) < window_size:
            return []
        
        spikes = []
        
        # Group trends by name for time series analysis
        trend_series = defaultdict(list)
        for data_point in trend_data:
            trend_name = data_point.get('name', data_point.get('topic', 'unknown'))
            trend_series[trend_name].append({
                'timestamp': data_point.get('timestamp', datetime.now().isoformat()),
                'score': data_point.get('composite_score', data_point.get('relevance_score', 0)),
                'frequency': data_point.get('frequency', 0)
            })
        
        for trend_name, series in trend_series.items():
            if len(series) < window_size:
                continue
            
            # Sort by timestamp
            series.sort(key=lambda x: x['timestamp'])
            
            # Extract scores for analysis
            scores = [point['score'] for point in series]
            frequencies = [point['frequency'] for point in series]
            
            # Calculate moving average and standard deviation
            if len(scores) >= window_size:
                recent_scores = scores[-window_size:]
                baseline_scores = scores[:-window_size] if len(scores) > window_size else scores
                
                if baseline_scores:
                    baseline_mean = statistics.mean(baseline_scores)
                    baseline_std = statistics.stdev(baseline_scores) if len(baseline_scores) > 1 else 0
                    
                    # Calculate Z-scores for recent data
                    for i, score in enumerate(recent_scores):
                        if baseline_std > 0:
                            z_score = (score - baseline_mean) / baseline_std
                            
                            # Determine spike severity
                            severity = 'moderate'
                            if z_score >= 4:
                                severity = 'critical'
                            elif z_score >= 3:
                                severity = 'high'
                            elif z_score >= 2:
                                severity = 'moderate'
                            else:
                                continue  # Not a significant spike
                            
                            # Calculate percentile rank
                            percentile = self._calculate_percentile(score, baseline_scores)
                            
                            spike = {
                                'trend_name': trend_name,
                                'timestamp': series[-(window_size-i)]['timestamp'],
                                'z_score': z_score,
                                'severity': severity,
                                'current_score': score,
                                'baseline_mean': baseline_mean,
                                'percentile': percentile,
                                'frequency': frequencies[-(window_size-i)] if i < len(frequencies) else 0,
                                'spike_type': 'frequency' if frequencies[-(window_size-i)] > statistics.mean([f for f in frequencies[:-window_size] if f > 0]) else 'score'
                            }
                            
                            spikes.append(spike)
        
        # Sort spikes by severity and Z-score
        severity_order = {'critical': 4, 'high': 3, 'moderate': 2}
        spikes.sort(key=lambda x: (severity_order.get(x['severity'], 0), x['z_score']), reverse=True)
        
        return spikes
    
    def _calculate_percentile(self, value: float, data: List[float]) -> float:
        """Calculate percentile rank of a value in a dataset"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        count_below = sum(1 for x in sorted_data if x < value)
        return (count_below / len(sorted_data)) * 100
    
    def analyze_trend_persistence(self, trend_history: List[Dict]) -> Dict:
        """
        Layer 4: Analyze how long trends persist
        """
        if not trend_history:
            return {}
        
        # Group by trend name
        trend_lifespans = defaultdict(list)
        for entry in trend_history:
            trend_name = entry.get('name', entry.get('topic', 'unknown'))
            trend_lifespans[trend_name].append({
                'timestamp': entry.get('timestamp', datetime.now().isoformat()),
                'score': entry.get('composite_score', entry.get('relevance_score', 0))
            })
        
        persistence_analysis = {}
        for trend_name, entries in trend_lifespans.items():
            if len(entries) < 2:
                continue
            
            # Sort by timestamp
            entries.sort(key=lambda x: x['timestamp'])
            
            # Calculate persistence metrics
            first_seen = entries[0]['timestamp']
            last_seen = entries[-1]['timestamp']
            
            try:
                first_date = datetime.fromisoformat(first_seen.replace('Z', '+00:00'))
                last_date = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                lifespan_days = (last_date - first_date).days
            except:
                lifespan_days = 0
            
            # Calculate trend direction
            scores = [entry['score'] for entry in entries]
            trend_direction = 'stable'
            if len(scores) >= 2:
                if scores[-1] > scores[0] * 1.1:
                    trend_direction = 'increasing'
                elif scores[-1] < scores[0] * 0.9:
                    trend_direction = 'decreasing'
            
            # Calculate volatility
            volatility = statistics.stdev(scores) if len(scores) > 1 else 0
            
            persistence_analysis[trend_name] = {
                'lifespan_days': lifespan_days,
                'entry_count': len(entries),
                'trend_direction': trend_direction,
                'volatility': volatility,
                'current_score': scores[-1],
                'peak_score': max(scores),
                'first_seen': first_seen,
                'last_seen': last_seen
            }
        
        return persistence_analysis
    
    def predict_emerging_trends(self, trend_history: List[Dict], current_trends: List[Dict]) -> List[Dict]:
        """
        Layer 4: Predict emerging trends using historical patterns
        """
        if not trend_history or not current_trends:
            return []
        
        # Analyze historical patterns
        persistence_data = self.analyze_trend_persistence(trend_history)
        
        # Find patterns in emerging trends
        emerging_patterns = []
        
        for trend in current_trends:
            trend_name = trend.get('name', trend.get('topic', ''))
            current_score = trend.get('composite_score', trend.get('relevance_score', 0))
            
            # Check if this is a new trend
            if trend_name not in persistence_data:
                # New trend - check if it has characteristics of emerging trends
                if current_score > 0.6:  # High initial score
                    emerging_patterns.append({
                        'trend_name': trend_name,
                        'prediction_type': 'new_emerging',
                        'confidence': min(current_score, 0.9),
                        'reason': 'High initial score for new trend',
                        'predicted_lifespan': 'short' if current_score > 0.8 else 'medium'
                    })
            else:
                # Existing trend - check for acceleration
                historical_data = persistence_data[trend_name]
                if historical_data['trend_direction'] == 'increasing' and current_score > historical_data['peak_score']:
                    emerging_patterns.append({
                        'trend_name': trend_name,
                        'prediction_type': 'accelerating',
                        'confidence': 0.8,
                        'reason': 'Trend is accelerating beyond historical peak',
                        'predicted_lifespan': 'long' if historical_data['lifespan_days'] > 7 else 'medium'
                    })
        
        # Sort by confidence
        emerging_patterns.sort(key=lambda x: x['confidence'], reverse=True)
        
        return emerging_patterns[:5]  # Top 5 predictions

# Create singleton instance
trend_analyzer = TrendAnalyzer()
