import streamlit as st
import streamlit_shadcn_ui as ui
from datetime import datetime
from config.sources import NEWS_SOURCES, source_manager
from utils.database import save_preferences
from utils.scraper import scrape_sources, scrape_user_sources
from utils.ai_curator import curate_newsletter
from utils.email_sender import send_newsletter
from utils.voice_trainer import voice_trainer
from utils.trend_analyzer import trend_analyzer
from utils.scheduler import trend_scheduler
from utils.auth import (
    init_auth, sign_up, sign_in, sign_out, reset_password,
    get_current_user, is_authenticated, get_user_email, handle_auth_state_change
)


st.set_page_config(page_title="AI Newsletter MVP", page_icon="📰", layout="wide")

# Initialize authentication
init_auth()
handle_auth_state_change()

# Initialize trend scheduler
if 'scheduler_initialized' not in st.session_state:
    trend_scheduler.start_scheduler()
    st.session_state['scheduler_initialized'] = True

def show_auth_page():
    """Show authentication page"""
    st.title("📰 AI Newsletter MVP")
    st.caption("Get curated AI insights delivered to your inbox every morning")
    
    # Authentication tabs
    auth_tab, signup_tab = st.tabs(["Sign In", "Sign Up"])
    
    with auth_tab:
        st.subheader("Sign In")
        with st.form("signin_form"):
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In")
            
            if submit:
                if email and password:
                    result = sign_in(email, password)
                    if result["success"]:
                        st.success(result["message"])
                        st.rerun()
                    else:
                        st.error(result["message"])
                else:
                    st.error("Please fill in all fields")
        
        # Password reset
        if st.button("Forgot Password?"):
            reset_email = st.text_input("Enter your email for password reset", placeholder="your@email.com")
            if reset_email:
                result = reset_password(reset_email)
                if result["success"]:
                    st.success(result["message"])
                else:
                    st.error(result["message"])
    
    with signup_tab:
        st.subheader("Sign Up")
        with st.form("signup_form"):
            new_email = st.text_input("Email", placeholder="your@email.com", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
            submit_signup = st.form_submit_button("Sign Up")
            
            if submit_signup:
                if new_email and new_password and confirm_password:
                    if new_password == confirm_password:
                        if len(new_password) >= 6:
                            result = sign_up(new_email, new_password)
                            if result["success"]:
                                st.success(result["message"])
                            else:
                                st.error(result["message"])
                        else:
                            st.error("Password must be at least 6 characters long")
                    else:
                        st.error("Passwords do not match")
                else:
                    st.error("Please fill in all fields")

def show_draft_preview(user_id: str, user_email: str):
    """Show draft preview with approve/regenerate options"""
    st.subheader("📝 Review Your Newsletter Draft")
    st.caption("Review and edit before sending")
    
    # Get draft from session state
    draft_content = st.session_state.get('draft_content', '')
    draft_articles = st.session_state.get('draft_articles', [])
    draft_topics = st.session_state.get('draft_topics', [])
    draft_mode = st.session_state.get('draft_mode', 'custom')  # 'custom' or 'legacy'
    
    # Editable preview
    st.write("**Edit your newsletter below:**")
    edited_content = st.text_area(
        "Newsletter Content",
        value=draft_content,
        height=400,
        key="draft_editor",
        help="Feel free to edit the content before sending"
    )
    
    # Show article count
    st.info(f"📊 Based on {len(draft_articles)} articles from your sources")
    
    # Quick feedback (comment only) for regeneration guidance
    st.write("**What should I change?**")
    feedback_comment = st.text_area(
        "Comment (optional)",
        value=st.session_state.get('draft_feedback', {}).get('comment', ''),
        height=100,
        key="draft_feedback_comment",
        placeholder="Tell the AI what to change (e.g., 'Shorten intro, add more trends, keep tone formal')."
    )

    # Save feedback to session for use during regeneration
    st.session_state['draft_feedback'] = {
        'comment': feedback_comment,
    }

    # Action buttons
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        if st.button("✅ Approve & Send", type="primary", key="approve_send_btn"):
            with st.spinner("📧 Sending your newsletter..."):
                # Save preferences if legacy mode
                if draft_mode == 'legacy':
                    save_preferences(user_email, draft_topics)
                
                # Send the newsletter (use edited version)
                send_result = send_newsletter(user_email, edited_content)
                
                if send_result:
                    st.success("✅ Newsletter sent successfully! Check your inbox.")
                    st.balloons()
                    
                    # Clear draft from session state
                    del st.session_state['draft_content']
                    del st.session_state['draft_articles']
                    del st.session_state['draft_topics']
                    del st.session_state['draft_mode']
                    
                    # Show final preview
                    with st.expander("📬 Final Newsletter"):
                        st.markdown(edited_content)
                    
                    st.info("💡 Generate another newsletter or manage your sources in other tabs.")
                else:
                    st.error("❌ Failed to send newsletter. Please try again.")
    
    with col2:
        if st.button("🔄 Regenerate", key="regenerate_btn"):
            with st.spinner("🔍 Scraping sources again..."):
                # Re-scrape based on mode
                if draft_mode == 'custom':
                    articles = scrape_user_sources(user_id, max_articles=20)
                else:
                    articles = scrape_sources(draft_topics[0] if draft_topics else 'AI')
            
            if not articles:
                st.error("❌ No articles found. Try adding more sources.")
            else:
                with st.spinner("🤖 AI is curating a new newsletter..."):
                    # FIX: Read comment directly from form state to avoid timing issues
                    current_comment = st.session_state.get('draft_feedback_comment', '')
                    # Also try the alternative key in case of inconsistency
                    if not current_comment:
                        current_comment = st.session_state.get('draft_feedback', {}).get('comment', '')
                    previous_feedback = {'comment': current_comment} if current_comment else None
                    current_draft = st.session_state.get('draft_content')
                    
                    # DEBUG: Print what we're passing to the LLM
                    print(f"🔍 DEBUG - Comment: '{current_comment}'")
                    print(f"🔍 DEBUG - Comment length: {len(current_comment)}")
                    print(f"🔍 DEBUG - Has feedback: {bool(previous_feedback)}")
                    print(f"🔍 DEBUG - Has current draft: {bool(current_draft)}")
                    print(f"🔍 DEBUG - Current draft length: {len(current_draft) if current_draft else 0}")
                    print(f"🔍 DEBUG - Articles count: {len(articles)}")
                    print(f"🔍 DEBUG - Draft mode: {draft_mode}")
                    print(f"🔍 DEBUG - Current draft preview: {current_draft[:100] if current_draft else 'None'}...")
                    
                    # Get trending context for regeneration
                    trending_context = st.session_state.get('trend_report', {})
                    new_content = curate_newsletter(articles, draft_topics, user_id, previous_feedback=previous_feedback, current_draft=current_draft, trending_context=trending_context)
                    
                    # DEBUG: Check what LLM returned
                    print(f"🔍 LLM RESPONSE DEBUG - New content length: {len(new_content)}")
                    print(f"🔍 LLM RESPONSE DEBUG - New content preview: {new_content[:200]}...")
                    print(f"🔍 LLM RESPONSE DEBUG - Content changed: {new_content != current_draft}")
                
                # Update session state with new draft
                st.session_state['draft_content'] = new_content
                st.session_state['draft_articles'] = articles
                # Force text area to update by clearing its widget state
                if 'draft_editor' in st.session_state:
                    del st.session_state['draft_editor']
                st.success("✨ New draft generated! Review it below.")
                st.rerun()
    
    with col3:
        if st.button("❌ Discard", key="discard_btn"):
            # Clear draft from session state
            if 'draft_content' in st.session_state:
                del st.session_state['draft_content']
            if 'draft_articles' in st.session_state:
                del st.session_state['draft_articles']
            if 'draft_topics' in st.session_state:
                del st.session_state['draft_topics']
            if 'draft_mode' in st.session_state:
                del st.session_state['draft_mode']
            
            st.info("Draft discarded. Generate a new one when ready.")
            st.rerun()
    
    # Show preview
    st.divider()
    st.write("**Preview:**")
    st.markdown(edited_content)


def show_voice_training():
    """UI for voice training and style management"""
    user = get_current_user()
    if not user:
        st.error("Please sign in to train your voice")
        return
    
    user_id = user.id
    
    st.subheader("🎯 Voice Training")
    st.caption("Upload past newsletters to train AI on your writing style")
    
    # Upload section
    with st.expander("📤 Upload Past Newsletters", expanded=True):
        with st.form("upload_newsletters_form"):
            st.write("**Upload your past newsletters** (one per section):")
            
            # Sample newsletter uploads
            st.write("**Newsletter 1:**")
            title1 = st.text_input("Title", value="AI's Growing Role in Creative Industries", key="title1")
            content1 = st.text_area("Content", value="""**Introduction**
As AI technologies continue to evolve, they're finding their way into creative fields, unlocking new possibilities and transforming industries. This week, we explore how AI is reshaping art, music, and literature, and what it means for human creativity.

**Curated Links:**

* **AI Art Generation:** *How AI is changing the art world*, an exploration of generative art and its implications for artists and galleries. [Read more](#)
* **AI-Driven Music Composition:** *The rise of AI in music production*, examining the AI tools helping artists compose symphonies and beats. [Discover here](#)
* **AI and Literature:** *The role of AI in writing novels*, with examples from AI-written poetry and fiction. [Learn more](#)

**Trends to Watch:**

* **AI in Art Curation:** AI curators are now helping galleries decide which artworks to feature. This trend is disrupting the traditional roles of curators and artists alike. [Explore the trend](#)
* **AI's Impact on Copyright Laws:** As AI generates original content, how will intellectual property laws evolve to handle these creations? This is a topic of increasing debate. [More on this](#)
* **AI and the Future of Creativity:** Can AI fully replace human creativity, or will it always be a tool for enhancement? The discussion continues to spark new ideas. [Join the conversation](#)""", height=300, key="content1")
            
            st.write("**Newsletter 2:**")
            title2 = st.text_input("Title", value="Quantum Computing: The Next Frontier", key="title2")
            content2 = st.text_area("Content", value="""**Introduction**
Quantum computing promises to revolutionize the tech landscape, solving problems once deemed impossible. We delve into the latest breakthroughs and how close we are to harnessing the true potential of quantum mechanics for computing.

**Curated Links:**

* **The Quantum Leap:** *Explaining quantum computing in simple terms*, an introductory guide to understanding qubits and entanglement. [Start here](#)
* **Quantum vs Classical Computing:** *What sets quantum computers apart?* A deep dive into the differences and the groundbreaking implications. [Read more](#)
* **Quantum Computing in Medicine:** *How quantum computing could change drug development*, using molecular simulations to speed up discovery. [Find out more](#)

**Trends to Watch:**

* **Quantum Encryption:** As quantum computers become more powerful, they might also crack existing encryption methods. Researchers are now developing quantum-resistant encryption algorithms. [Read about this](#)
* **Quantum AI Synergy:** The combination of AI and quantum computing could lead to advancements in machine learning that we've yet to imagine. [Explore the synergy](#)
* **Government Investments in Quantum Tech:** Governments worldwide are pouring billions into quantum research, which could accelerate development. [What's happening here](#)""", height=300, key="content2")
            
            submit = st.form_submit_button("🚀 Train My Voice", type="primary")
            
            if submit:
                with st.spinner("Training AI on your writing style..."):
                    # Upload samples
                    results = []
                    for title, content in [(title1, content1), (title2, content2)]:
                        if title and content:
                            result = voice_trainer.upload_writing_sample(user_id, title, content)
                            results.append(result)
                    
                    # Generate style profile from extracted features
                    style_result = voice_trainer.generate_style_card(user_id)
                
                if all(r['success'] for r in results) and style_result['success']:
                    st.success("✅ Voice training complete! AI now understands your style.")
                    
                    # Display extracted features in a readable format
                    style_card = style_result['style_card']
                    st.write("**Your Writing Style Profile:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Style", style_card.get('writing_style', 'N/A'))
                        st.metric("Voice", style_card.get('voice_characteristics', 'N/A'))
                    with col2:
                        st.metric("Focus", style_card.get('content_focus', 'N/A'))
                        st.metric("Topic", style_card.get('topic_category', 'N/A'))
                    with col3:
                        st.metric("Length", style_card.get('target_length_range', 'N/A'))
                        st.metric("Samples", style_card.get('sample_count', 0))
                else:
                    st.error("❌ Some uploads failed. Please try again.")
                
                st.rerun()
    
    # Display current style profile from extracted features
    features = voice_trainer.get_user_features(user_id)
    if features:
        st.write("**Your Current Style Profile:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Style", features.get('writing_style', 'N/A'))
            st.metric("Voice", features.get('voice_characteristics', 'N/A'))
        with col2:
            st.metric("Focus", features.get('content_focus', 'N/A'))
            st.metric("Topic", features.get('topic_category', 'N/A'))
        with col3:
            st.metric("Length", features.get('target_length_range', 'N/A'))
            st.metric("Samples", features.get('sample_count', 0))
    
    # Show uploaded samples (features only, no full content stored)
    samples = voice_trainer.get_user_samples(user_id)
    if samples:
        st.write(f"**Uploaded Newsletter Features ({len(samples)} total):**")
        for sample in samples:
            with st.expander(f"📄 {sample['newsletter_title']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Style:** {sample.get('writing_style', 'N/A')}")
                    st.write(f"**Voice:** {sample.get('voice_characteristics', 'N/A')}")
                    st.write(f"**Focus:** {sample.get('content_focus', 'N/A')}")
                with col2:
                    st.write(f"**Topic:** {sample.get('topic_category', 'N/A')}")
                    st.write(f"**Length:** {sample.get('word_count', 0)} words")
                    st.write(f"**Uploaded:** {sample.get('uploaded_at', 'N/A')}")


def show_trends():
    """UI for trend analysis and visualization"""
    user = get_current_user()
    if not user:
        st.error("Please sign in to view trends")
        return
    
    user_id = user.id
    
    st.subheader("📈 Trend Analysis")
    st.caption("Discover trending topics from your sources")
    
    # Check if user has custom sources
    user_sources = source_manager.get_user_sources(user_id, active_only=True)
    
    if not user_sources:
        st.info("💡 Add custom sources in the 'Manage Sources' tab to see trends!")
        return
    
    # Hybrid controls with scheduler status
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        st.write(f"📊 Analyzing {len(user_sources)} active sources")
        
        # Scheduler status
        scheduler_status = trend_scheduler.get_scheduler_status()
        if scheduler_status['running']:
            st.caption("🟢 Auto-refresh: ON")
        else:
            st.caption("🔴 Auto-refresh: OFF")
    
    with col2:
        if st.button("🔄 Refresh Trends", type="primary"):
            with st.spinner("🔍 Scraping sources and analyzing trends..."):
                result = trend_scheduler.manual_trend_refresh(user_id)
                if result['success']:
                    st.success(f"✅ Found {result['trends_found']} trending topics!")
                else:
                    st.error(f"❌ {result['error']}")
    
    with col3:
        if st.button("🔍 Check Spikes"):
            with st.spinner("🔍 Checking for trend spikes..."):
                result = trend_scheduler.manual_spike_detection(user_id)
                if result['success']:
                    if result['spikes_detected'] > 0:
                        st.warning(f"🚨 {result['spikes_detected']} spikes detected!")
                    else:
                        st.success("✅ No spikes detected")
                else:
                    st.error(f"❌ {result['error']}")
    
    with col4:
        if 'trend_last_updated' in st.session_state:
            st.caption(f"Last updated: {st.session_state['trend_last_updated']}")
        
        # Next auto-refresh countdown
        if scheduler_status['next_trend_refresh']:
            try:
                next_refresh = datetime.fromisoformat(scheduler_status['next_trend_refresh'].replace('Z', '+00:00'))
                time_until = next_refresh - datetime.now()
                if time_until.total_seconds() > 0:
                    hours = int(time_until.total_seconds() // 3600)
                    minutes = int((time_until.total_seconds() % 3600) // 60)
                    st.caption(f"Next auto-refresh: {hours}h {minutes}m")
            except:
                pass
    
    # Display trends if available
    if 'trend_report' in st.session_state:
        trend_report = st.session_state['trend_report']
        articles = st.session_state.get('trend_articles', [])
        
        # Check if this is the new market intelligence report format
        if 'user_trends' in trend_report:
            # New format with market intelligence
            user_trends = trend_report['user_trends']
            market_intelligence = trend_report.get('market_intelligence', {})
            correlation_analysis = trend_report.get('correlation_analysis', {})
            
            # Summary metrics for market intelligence
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("User Trends", len(user_trends))
            with col2:
                st.metric("Market Trends", len(market_intelligence.get('overall_trends', [])))
            with col3:
                correlations = correlation_analysis.get('correlations', {}).get('correlations', [])
                st.metric("Correlations", len(correlations))
            with col4:
                recommendations = trend_report.get('recommendations', [])
                st.metric("Recommendations", len(recommendations))
            with col5:
                coverage = correlation_analysis.get('content_gaps', {}).get('coverage_analysis', {})
                st.metric("Coverage %", f"{coverage.get('coverage_percentage', 0):.0f}%")
        else:
            # Legacy format
            metrics = trend_report.get('metrics', {})
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Articles Analyzed", metrics.get('total_articles', 0))
            with col2:
                st.metric("Unique Sources", metrics.get('unique_sources', 0))
            with col3:
                st.metric("AI Trends", metrics.get('llm_trends_count', 0))
            with col4:
                st.metric("Basic Trends", metrics.get('basic_trends_count', 0))
            with col5:
                st.metric("Categories", len(metrics.get('trend_categories', {})))
        
        st.divider()
        
        # Spike alerts section
        if 'detected_spikes' in st.session_state and st.session_state['detected_spikes']:
            st.write("**🔥 Spikes Detected**")
            spikes = st.session_state['detected_spikes']
            
            for spike in spikes[:5]:  # Show top 5 spikes
                severity = spike.get('severity', 'moderate')
                if severity == 'critical':
                    st.error(f"🚨 **CRITICAL SPIKE:** {spike['trend_name']} (Z-score: {spike['z_score']:.1f})")
                elif severity == 'high':
                    st.warning(f"⚠️ **HIGH SPIKE:** {spike['trend_name']} (Z-score: {spike['z_score']:.1f})")
                else:
                    st.info(f"📈 **MODERATE SPIKE:** {spike['trend_name']} (Z-score: {spike['z_score']:.1f})")
                
                with st.expander(f"Spike Details: {spike['trend_name']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Severity:** {spike['severity']}")
                        st.write(f"**Z-Score:** {spike['z_score']:.2f}")
                        st.write(f"**Current Score:** {spike['current_score']:.2f}")
                        st.write(f"**Baseline Mean:** {spike['baseline_mean']:.2f}")
                    with col2:
                        st.write(f"**Percentile:** {spike['percentile']:.1f}%")
                        st.write(f"**Spike Type:** {spike['spike_type']}")
                        st.write(f"**Frequency:** {spike['frequency']}")
                        st.write(f"**Detected:** {spike['timestamp']}")
            
            st.divider()
        
        # Trending topics
        st.write("**🔥 Trending Topics**")
        
        # Get trends based on report format
        if 'user_trends' in trend_report:
            trends_to_show = user_trends
        else:
            trends_to_show = trend_report.get('trends', [])
        
        if trends_to_show:
            for i, trend in enumerate(trends_to_show[:5], 1):
                # Determine trend name and score
                trend_name = trend.get('name', trend.get('topic', 'Unknown'))
                trend_score = trend.get('composite_score', trend.get('relevance_score', 0))
                trend_type = trend.get('type', 'basic')
                
                # Color coding for trend types
                if trend_type == 'llm_analyzed':
                    emoji = "🤖"
                    color = "blue"
                else:
                    emoji = "📊"
                    color = "green"
                
                with st.expander(f"{emoji} {i}. {trend_name} (Score: {trend_score:.2f})"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Type:** {trend_type}")
                        st.write(f"**Category:** {trend.get('category', 'Uncategorized')}")
                        
                        # Show description for LLM trends
                        if trend.get('description'):
                            st.write(f"**Description:** {trend['description']}")
                        
                        # Show frequency or composite score details
                        if trend_type == 'llm_analyzed':
                            st.write(f"**Composite Score:** {trend_score:.2f}")
                            st.write(f"**Recency:** {trend.get('recency_score', 0):.2f}")
                            st.write(f"**Authority:** {trend.get('authority_score', 0):.2f}")
                        else:
                            st.write(f"**Frequency:** {trend.get('frequency', 0)} mentions")
                            st.write(f"**Relevance Score:** {trend_score:.2f}")
                        
                        # Supporting articles
                        if trend.get('supporting_articles'):
                            st.write("**Supporting Articles:**")
                            for article in trend['supporting_articles']:
                                st.write(f"• [{article['title'][:60]}...]({article['source']})")
                    
                    with col2:
                        # Enhanced visualization
                        if trend_type == 'llm_analyzed':
                            # Show score breakdown
                            score_data = {
                                'Recency': trend.get('recency_score', 0),
                                'Authority': trend.get('authority_score', 0),
                                'Frequency': trend.get('frequency_score', 0)
                            }
                            st.bar_chart(score_data)
                        else:
                            # Simple frequency chart
                            st.bar_chart({trend_name: trend.get('frequency', 0)})
        else:
            st.info("No trending topics detected. Try refreshing or adding more sources.")
        
        st.divider()
        
        # Market Trends vs Your Sources comparison (only for new format)
        if 'user_trends' in trend_report:
            # Market Trends section
            st.write("**🌍 Market Trends vs Your Sources**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Your Trends:**")
                if user_trends:
                    for trend in user_trends[:5]:
                        st.write(f"• {trend.get('name', trend.get('topic', 'Unknown'))}")
                else:
                    st.write("No trends detected")
            
            with col2:
                st.write("**Market Trends:**")
                market_trends = market_intelligence.get('overall_trends', [])
                if market_trends:
                    for trend in market_trends[:5]:
                        st.write(f"• {trend.get('query', 'Unknown')}")
                else:
                    st.write("No market trends available")
            
            # Recommendations section
            recommendations = trend_report.get('recommendations', [])
            if recommendations:
                st.write("**💡 Recommendations**")
                for rec in recommendations[:5]:
                    if rec.get('type') == 'source_suggestion':
                        st.info(f"**Add sources for:** {rec.get('topic')} ({rec.get('priority')} priority)")
                        if rec.get('suggested_sources'):
                            for source in rec['suggested_sources'][:2]:
                                st.write(f"  • [{source.get('title', 'Source')}]({source.get('url', '#')})")
                    elif rec.get('type') == 'trend_alignment':
                        st.success(f"**Trend alignment:** Your '{rec.get('user_trend')}' aligns with market trend '{rec.get('market_trend')}' ({rec.get('similarity', 0):.1%} similarity)")
        
        # Legacy charts (for both formats)
        if 'user_trends' in trend_report:
            # For new format, show market intelligence categories
            if market_intelligence.get('categories'):
                st.write("**📈 Market Trend Categories**")
                category_data = {cat: data.get('trend_count', 0) for cat, data in market_intelligence['categories'].items()}
                if category_data:
                    st.bar_chart(category_data)
        else:
            # Legacy format charts
            metrics = trend_report.get('metrics', {})
            if metrics.get('trend_categories'):
                st.write("**📈 Trend Categories**")
                category_data = metrics['trend_categories']
                st.bar_chart(category_data)
            
            # Source distribution
            st.write("**📊 Source Distribution**")
            if metrics.get('source_distribution'):
                source_data = metrics['source_distribution']
                st.bar_chart(source_data)
            
            # Top keywords
            st.write("**🔤 Top Keywords**")
            if metrics.get('top_keywords'):
                keyword_data = dict(list(metrics['top_keywords'].items())[:10])
                st.bar_chart(keyword_data)
    
    else:
        st.info("👆 Click 'Refresh Trends' to analyze your sources and discover trending topics!")
    
    # Scheduler configuration section
    st.divider()
    st.write("**⚙️ Auto-Refresh Settings**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        trend_interval = st.selectbox(
            "Trend Refresh Interval",
            [1, 2, 4, 6, 8, 12, 24],
            index=2,  # Default to 4 hours
            help="How often to automatically refresh trends"
        )
    
    with col2:
        spike_interval = st.selectbox(
            "Spike Check Interval", 
            [1, 2, 4, 6, 8, 12],
            index=0,  # Default to 1 hour
            help="How often to check for trend spikes"
        )
    
    with col3:
        if st.button("🔄 Update Schedule"):
            success = trend_scheduler.configure_schedule(trend_interval, spike_interval)
            if success:
                st.success("✅ Schedule updated!")
            else:
                st.error("❌ Failed to update schedule")
    
    # Show current scheduler status
    scheduler_status = trend_scheduler.get_scheduler_status()
    if scheduler_status['running']:
        st.success("🟢 Auto-refresh is active")
        col1, col2 = st.columns(2)
        with col1:
            if scheduler_status['last_trend_refresh']:
                st.caption(f"Last trend refresh: {scheduler_status['last_trend_refresh']}")
        with col2:
            if scheduler_status['last_spike_check']:
                st.caption(f"Last spike check: {scheduler_status['last_spike_check']}")
    else:
        st.warning("🔴 Auto-refresh is disabled")


def show_source_management():
    """UI for managing custom sources"""
    user = get_current_user()
    if not user:
        st.error("Please sign in to manage sources")
        return
    
    user_id = user.id
    
    st.subheader("📰 Manage Your Sources")
    st.caption("Add custom URLs to personalize your newsletter content")
    
    # Quick add section
    with st.expander("➕ Add New Sources", expanded=True):
        with st.form("add_sources_form"):
            st.write("**Paste URLs** (one per line):")
            urls_input = st.text_area(
                "Source URLs",
                placeholder="""https://www.youtube.com/@wsj
https://x.com/xai
https://www.reddit.com/r/ArtificialInteligence/
https://openai.com/blog/
https://techcrunch.com/feed/""",
                height=150,
                help="Paste YouTube channels, Twitter/X accounts, Reddit communities, RSS feeds, or website URLs"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                category = st.selectbox("Category (optional)", ['', 'AI', 'Technology', 'News', 'Business', 'Other'])
            with col2:
                priority = st.slider("Priority", 1, 10, 5, help="Higher priority sources are scraped first")
            
            submit = st.form_submit_button("🚀 Add Sources", type="primary")
            
            if submit and urls_input:
                urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
                
                with st.spinner(f"Adding {len(urls)} sources..."):
                    results = source_manager.bulk_add_sources(user_id, urls)
                
                if results['success']:
                    st.success(f"✅ Added {len(results['success'])} sources!")
                
                if results['failed']:
                    st.warning(f"⚠️ {len(results['failed'])} sources failed:")
                    for fail in results['failed']:
                        st.error(f"  • {fail['error']}")
                
                st.rerun()
    
    # Display existing sources
    sources = source_manager.get_user_sources(user_id, active_only=False)
    
    if sources:
        st.write(f"**Your Sources ({len(sources)} total)**")
        
        for source in sources:
            with st.container():
                col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
                
                with col1:
                    status_emoji = "🟢" if source['active'] else "🔴"
                    st.write(f"{status_emoji} **{source['display_name']}**")
                    st.caption(f"{source['source_url'][:60]}... • Priority: {source['priority']}")
                
                with col2:
                    if source.get('last_scraped_at'):
                        from datetime import datetime
                        try:
                            scraped = datetime.fromisoformat(source['last_scraped_at'])
                            st.caption(f"🕐 Last: {scraped.strftime('%m/%d %H:%M')}")
                        except:
                            st.caption("🕐 Never")
                    else:
                        st.caption("🕐 Never scraped")
                
                with col3:
                    if st.button("⏸️" if source['active'] else "▶️", key=f"toggle_{source['id']}"):
                        source_manager.toggle_source(source['id'])
                        st.rerun()
                
                with col4:
                    if st.button("🗑️", key=f"delete_{source['id']}"):
                        source_manager.remove_source(source['id'])
                        st.success(f"Removed {source['display_name']}")
                        st.rerun()
                
                st.divider()
    else:
        st.info("👋 No sources yet! Add some URLs above to get started.")
        
        # Offer starter pack
        st.write("**Quick Start:**")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🤖 AI Starter Pack"):
                source_manager.initialize_default_sources(user_id, 'AI')
                st.rerun()
        
        with col2:
            if st.button("💻 Tech Starter Pack"):
                source_manager.initialize_default_sources(user_id, 'Technology')
                st.rerun()
        
        with col3:
            if st.button("📊 Data Science Pack"):
                source_manager.initialize_default_sources(user_id, 'Data Science')
                st.rerun()
        
        with col4:
            if st.button("🧠 ML Starter Pack"):
                source_manager.initialize_default_sources(user_id, 'Machine Learning')
                st.rerun()


def show_main_app():
    """Show main newsletter application"""
    user = get_current_user()
    if not user:
        st.error("Please sign in to access the newsletter")
        return
    
    user_id = user.id
    user_email = get_user_email()
    
    # Header with user info and sign out
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📰 Your Personalized AI Newsletter")
        st.caption(f"Welcome back, {user_email}!")
    with col2:
        if st.button("Sign Out", type="secondary"):
            sign_out()
            st.rerun()
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📬 Generate Newsletter", "⚙️ Manage Sources", "🎯 Voice Training", "📈 Trends"])
    
    with tab1:
        # Check if there's a draft in session state
        if 'draft_content' in st.session_state:
            # Show draft preview
            show_draft_preview(user_id, user_email)
        else:
            # Check if user has custom sources
            user_sources = source_manager.get_user_sources(user_id, active_only=True)
            
            if user_sources:
                # NEW: Use dynamic sources
                st.subheader("Generate from Your Custom Sources")
                st.write(f"✅ You have {len(user_sources)} active sources")
                
                # Show which sources will be used
                with st.expander("📋 View Active Sources"):
                    for source in user_sources[:10]:  # Show first 10
                        st.write(f"• {source['display_name']}")
                    if len(user_sources) > 10:
                        st.write(f"... and {len(user_sources) - 10} more")
                
                if ui.button("Generate My Newsletter", key="generate_btn_custom"):
                    with st.spinner("🔍 Scraping your custom sources..."):
                        articles = scrape_user_sources(user_id, max_articles=20)
                    
                    if not articles:
                        st.error("❌ No articles found. Try adding more sources or check if they're accessible.")
                    else:
                        with st.spinner("🤖 AI is curating your newsletter..."):
                            # Get trending context if available
                            trending_context = st.session_state.get('trend_report', {})
                            newsletter_content = curate_newsletter(articles, ['custom'], user_id, trending_context=trending_context)
                        
                        # Store draft in session state instead of sending immediately
                        st.session_state['draft_content'] = newsletter_content
                        st.session_state['draft_articles'] = articles
                        st.session_state['draft_topics'] = ['custom']
                        st.session_state['draft_mode'] = 'custom'
                        
                        st.success(f"✨ Draft generated with {len(articles)} articles! Review it below.")
                        st.rerun()
            
            else:
                # FALLBACK: Use old category-based system
                st.subheader("Choose Topics (Classic Mode)")
                st.info("💡 Add custom sources in the 'Manage Sources' tab for personalized content!")
                
                selected_categories = ui.tabs(
                    options=list(NEWS_SOURCES.keys()), 
                    default_value='AI', 
                    key="topic_tabs"
                )
                
                st.write(f"You selected: {selected_categories}")
                
                if ui.button("Generate Newsletter", key="generate_btn_legacy"):
                    with st.spinner("🔍 Scraping sources..."):
                        articles = scrape_sources(selected_categories)
                    
                    if not articles:
                        st.error("❌ No articles found. Please try again.")
                    else:
                        with st.spinner("🤖 AI is curating your newsletter..."):
                            # Get trending context if available
                            trending_context = st.session_state.get('trend_report', {})
                            newsletter_content = curate_newsletter(articles, [selected_categories], user_id, trending_context=trending_context)
                        
                        # Store draft in session state instead of sending immediately
                        st.session_state['draft_content'] = newsletter_content
                        st.session_state['draft_articles'] = articles
                        st.session_state['draft_topics'] = [selected_categories]
                        st.session_state['draft_mode'] = 'legacy'
                        
                        st.success("✨ Draft generated! Review it below.")
                        st.rerun()
    
    with tab2:
        show_source_management()
    
    with tab3:
        show_voice_training()
    
    with tab4:
        show_trends()

# Main app logic
if is_authenticated():
    show_main_app()
else:
    show_auth_page()


