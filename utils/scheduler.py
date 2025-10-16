"""
Background Scheduler - Layer 4: Automated Task Scheduling
Implements scheduled trend refresh and spike detection
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import streamlit as st

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    print("Warning: schedule not available. Install with: pip install schedule")

class TrendScheduler:
    """Background scheduler for automated trend analysis and spike detection"""
    
    def __init__(self):
        self.scheduler_thread = None
        self.running = False
        self.last_trend_refresh = None
        self.last_spike_check = None
        self.trend_history = []
        self.spike_history = []
        
        if not SCHEDULE_AVAILABLE:
            print("Scheduler disabled - schedule package not available")
    
    def start_scheduler(self):
        """Start the background scheduler"""
        if not SCHEDULE_AVAILABLE:
            return False
        
        if self.running:
            return True
        
        try:
            # Clear existing jobs
            schedule.clear()
            
            # Schedule trend refresh every 4 hours
            schedule.every(4).hours.do(self._scheduled_trend_refresh)
            
            # Schedule spike detection every 1 hour
            schedule.every(1).hours.do(self._scheduled_spike_detection)
            
            # Start scheduler thread
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            
            print("✅ Trend scheduler started")
            return True
            
        except Exception as e:
            print(f"Error starting scheduler: {e}")
            return False
    
    def stop_scheduler(self):
        """Stop the background scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        schedule.clear()
        print("🛑 Trend scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Scheduler error: {e}")
                time.sleep(60)
    
    def _scheduled_trend_refresh(self):
        """Scheduled task: Refresh trends every 4 hours"""
        try:
            print("🔄 Running scheduled trend refresh...")
            
            # This would normally scrape and analyze trends
            # For now, we'll simulate the process
            self.last_trend_refresh = datetime.now()
            
            # Store in session state if available
            if hasattr(st, 'session_state'):
                st.session_state['scheduled_trend_refresh'] = {
                    'timestamp': self.last_trend_refresh.isoformat(),
                    'status': 'completed'
                }
            
            print(f"✅ Scheduled trend refresh completed at {self.last_trend_refresh}")
            
        except Exception as e:
            print(f"Error in scheduled trend refresh: {e}")
    
    def _scheduled_spike_detection(self):
        """Scheduled task: Check for spikes every 1 hour"""
        try:
            print("🔍 Running scheduled spike detection...")
            
            # This would normally analyze trend history for spikes
            # For now, we'll simulate the process
            self.last_spike_check = datetime.now()
            
            # Simulate spike detection
            detected_spikes = self._simulate_spike_detection()
            
            if detected_spikes:
                print(f"🚨 Detected {len(detected_spikes)} spikes!")
                self.spike_history.extend(detected_spikes)
            else:
                print("✅ No spikes detected")
            
            # Store in session state if available
            if hasattr(st, 'session_state'):
                st.session_state['scheduled_spike_check'] = {
                    'timestamp': self.last_spike_check.isoformat(),
                    'spikes_detected': len(detected_spikes),
                    'status': 'completed'
                }
            
            print(f"✅ Scheduled spike detection completed at {self.last_spike_check}")
            
        except Exception as e:
            print(f"Error in scheduled spike detection: {e}")
    
    def _simulate_spike_detection(self) -> List[Dict]:
        """Simulate spike detection for demo purposes"""
        # This would normally use the trend_analyzer.detect_spikes() method
        # For now, return empty list
        return []
    
    def get_scheduler_status(self) -> Dict:
        """Get current scheduler status"""
        return {
            'running': self.running,
            'last_trend_refresh': self.last_trend_refresh.isoformat() if self.last_trend_refresh else None,
            'last_spike_check': self.last_spike_check.isoformat() if self.last_spike_check else None,
            'next_trend_refresh': self._get_next_run_time('trend_refresh'),
            'next_spike_check': self._get_next_run_time('spike_check'),
            'trend_history_count': len(self.trend_history),
            'spike_history_count': len(self.spike_history)
        }
    
    def _get_next_run_time(self, job_type: str) -> Optional[str]:
        """Get next scheduled run time for a job type"""
        if not SCHEDULE_AVAILABLE:
            return None
        
        try:
            jobs = schedule.get_jobs()
            for job in jobs:
                if job_type == 'trend_refresh' and 'trend_refresh' in str(job.job_func):
                    return str(job.next_run)
                elif job_type == 'spike_check' and 'spike_detection' in str(job.job_func):
                    return str(job.next_run)
        except:
            pass
        
        return None
    
    def manual_trend_refresh(self, user_id: str) -> Dict:
        """Manually trigger trend refresh"""
        try:
            from utils.scraper import scrape_user_sources
            from utils.trend_analyzer import trend_analyzer
            from config.sources import source_manager
            
            print(f"🔄 Manual trend refresh for user {user_id}")
            
            # Get user sources
            user_sources = source_manager.get_user_sources(user_id, active_only=True)
            if not user_sources:
                return {'success': False, 'error': 'No sources found'}
            
            # Scrape articles
            articles = scrape_user_sources(user_id, max_articles=20)
            if not articles:
                return {'success': False, 'error': 'No articles found'}
            
            # Generate market intelligence report
            trend_report = trend_analyzer.generate_market_intelligence_report(
                articles, 
                [s['source_url'] for s in user_sources]
            )
            
            # Store in session state
            if hasattr(st, 'session_state'):
                st.session_state['trend_report'] = trend_report
                st.session_state['trend_articles'] = articles
                st.session_state['trend_last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.last_trend_refresh = datetime.now()
            
            return {
                'success': True,
                'trends_found': len(trend_report.get('user_trends', [])),
                'timestamp': self.last_trend_refresh.isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def manual_spike_detection(self, user_id: str) -> Dict:
        """Manually trigger spike detection"""
        try:
            from utils.trend_analyzer import trend_analyzer
            
            print(f"🔍 Manual spike detection for user {user_id}")
            
            # Get trend history from session state
            if hasattr(st, 'session_state') and 'trend_history' in st.session_state:
                trend_history = st.session_state['trend_history']
            else:
                trend_history = []
            
            # Detect spikes
            spikes = trend_analyzer.detect_spikes(trend_history)
            
            # Store results
            if hasattr(st, 'session_state'):
                st.session_state['detected_spikes'] = spikes
                st.session_state['spike_last_checked'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.last_spike_check = datetime.now()
            
            return {
                'success': True,
                'spikes_detected': len(spikes),
                'spikes': spikes,
                'timestamp': self.last_spike_check.isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def configure_schedule(self, trend_interval_hours: int = 4, spike_interval_hours: int = 1):
        """Configure scheduler intervals"""
        if not SCHEDULE_AVAILABLE:
            return False
        
        try:
            # Stop current scheduler
            self.stop_scheduler()
            
            # Clear existing jobs
            schedule.clear()
            
            # Set new intervals
            schedule.every(trend_interval_hours).hours.do(self._scheduled_trend_refresh)
            schedule.every(spike_interval_hours).hours.do(self._scheduled_spike_detection)
            
            # Restart scheduler
            return self.start_scheduler()
            
        except Exception as e:
            print(f"Error configuring schedule: {e}")
            return False

# Create singleton instance
trend_scheduler = TrendScheduler()
