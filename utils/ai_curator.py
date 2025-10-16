from groq import Groq
import streamlit as st
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Get config from st.secrets if available, else from env
def get_config(key):
    """Get config from st.secrets or environment variables"""
    try:
        return st.secrets.get(key)
    except:
        return os.getenv(key)

def curate_newsletter(articles: list, user_topics: list, user_id: str = None, previous_feedback: Optional[Dict] = None, current_draft: Optional[str] = None, trending_context: Optional[Dict] = None):
    """Use Groq LLM to curate and summarize articles with user's voice training.
    previous_feedback can include: {'tags': [...], 'comment': '...'} to steer regeneration.
    """
    
    client = Groq(api_key=get_config("GROQ_API_KEY"))
    
    # Get user's extracted features if available
    user_features = None
    
    if user_id:
        from utils.voice_trainer import voice_trainer
        user_features = voice_trainer.get_user_features(user_id)
    
    # Combine articles into context
    context = "\n\n".join([
        f"Source: {a['source']}\nTitle: {a['title']}\nContent: {a['content']}" 
        for a in articles
    ])
    
    # Build optional feedback instruction snippet and detect revision mode
    feedback_snippet = ""
    has_comment = bool(previous_feedback and previous_feedback.get('comment'))
    revision_mode = bool(has_comment and current_draft)
    
    # Build trending context snippet
    trending_snippet = ""
    if trending_context:
        trending_snippet = _build_trending_context_snippet(trending_context)
    
    # DEBUG: Print what we received
    print(f"🔍 CURATOR DEBUG - previous_feedback: {previous_feedback}")
    print(f"🔍 CURATOR DEBUG - has_comment: {has_comment}")
    print(f"🔍 CURATOR DEBUG - current_draft length: {len(current_draft) if current_draft else 0}")
    print(f"🔍 CURATOR DEBUG - revision_mode: {revision_mode}")
    if has_comment:
        comment = previous_feedback.get('comment', '')
        comment_line = f"Editor Comment: {comment}"
        if revision_mode:
            base_instruction = (
                "IMPORTANT: Revise the CURRENT_DRAFT directly to address the editor comment. "
                "Do not generate a completely new newsletter. Preserve overall structure, sources, and factual content; "
                "modify tone/length/structure/links only as needed per the comment."
            )
        else:
            base_instruction = (
                "Apply the editor comment faithfully when generating the newsletter."
            )
        feedback_lines = f"{comment_line}\n{base_instruction}"
        feedback_snippet = f"\n\nEDITOR FEEDBACK:\n{feedback_lines}\n\nApply these changes."

    # Optional: include current draft content for model to revise in-place
    current_draft_block = f"\n\nCURRENT_DRAFT:\n{current_draft}\n" if current_draft and revision_mode else ""

    # If in revision mode, construct a strict revision prompt
    if revision_mode:
        prompt = f"""TASK: Revise the newsletter draft below based on the editor's feedback.

CURRENT DRAFT TO REVISE:
{current_draft}

ARTICLES CONTEXT (for reference only):
{context}

INSTRUCTIONS:
1. Read the current draft above
2. Apply the editor feedback exactly
3. Keep the same structure and sources
4. Make the changes visible and clear
5. Output the revised newsletter content only

{feedback_snippet}{trending_snippet}"""

    # If user has extracted features, use them for personalized generation
    elif user_features:
        prompt = f"""Create a newsletter with these specifications:

WRITING STYLE: {user_features['writing_style']}
VOICE: {user_features['voice_characteristics']}
CONTENT FOCUS: {user_features['content_focus']}
TOPIC: {user_features['topic_category']}
LENGTH: {user_features['target_length_range']} words

ARTICLES TO CURATE:
{context}

INSTRUCTIONS:
- Follow the writing style and voice characteristics exactly
- Focus on the specified content type
- Write within the target length range
- Use bold headings, bullet points, and italic emphasis
- Include descriptive link text like "Read more", "Learn more", "Discover here"
- End with engaging call-to-action phrases

Generate a newsletter matching these specifications.{feedback_snippet}{trending_snippet}"""
        
    else:
        # Fallback to generic template-based approach
        prompt = f"""You are an AI newsletter curator. Create a professional newsletter following this template structure:

**Introduction**
[2-3 sentences setting context about {', '.join(user_topics)}]

**Curated Links:**
[3 items with descriptions and links]

**Trends to Watch:**
[3 items with brief explanations]

Articles to curate:
{context}

Instructions:
- Write 600-800 words
- Use professional but accessible tone
- Include phrases like "we explore", "here's what", "discover more"
- Use bold headings, bullet points, italic emphasis
- End with engaging call-to-action phrases{feedback_snippet}{trending_snippet}"""
    
    # DEBUG: Print the prompt being sent to LLM
    print(f"🔍 PROMPT DEBUG - Revision mode: {revision_mode}")
    print(f"🔍 PROMPT DEBUG - Prompt length: {len(prompt)}")
    print(f"🔍 PROMPT DEBUG - Has feedback snippet: {bool(feedback_snippet)}")
    if feedback_snippet:
        print(f"🔍 PROMPT DEBUG - Feedback snippet: {feedback_snippet[:200]}...")
    
    # Show first 500 chars of prompt for debugging
    print(f"🔍 PROMPT PREVIEW: {prompt[:500]}...")
    
    # Show the full prompt if it's short enough
    if len(prompt) < 2000:
        print(f"🔍 FULL PROMPT: {prompt}")
    else:
        print(f"🔍 PROMPT TOO LONG ({len(prompt)} chars), showing first 1000: {prompt[:1000]}...")
    
    response = client.chat.completions.create(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5 if revision_mode else 0.7,
        max_tokens=2000
    )
    
    result = response.choices[0].message.content
    
    # DEBUG: Show what LLM returned
    print(f"🔍 LLM RETURNED - Length: {len(result)}")
    print(f"🔍 LLM RETURNED - Preview: {result[:200]}...")
    if revision_mode and current_draft:
        print(f"🔍 LLM RETURNED - Same as input: {result == current_draft}")
        print(f"🔍 LLM RETURNED - Similar to input: {result[:100] == current_draft[:100]}")
    
    return result


def _build_trending_context_snippet(trending_context: Dict) -> str:
    """Build trending context snippet for newsletter generation"""
    if not trending_context:
        return ""
    
    snippet_parts = []
    
    # Add trending topics
    if 'user_trends' in trending_context:
        trends = trending_context['user_trends'][:5]  # Top 5 trends
        if trends:
            trend_names = [trend.get('name', trend.get('topic', '')) for trend in trends]
            snippet_parts.append(f"TRENDING TOPICS: {', '.join(trend_names)}")
    
    # Add market trends
    if 'market_intelligence' in trending_context:
        market_data = trending_context['market_intelligence']
        if 'overall_trends' in market_data:
            market_trends = market_data['overall_trends'][:3]  # Top 3 market trends
            if market_trends:
                market_names = [trend.get('query', '') for trend in market_trends]
                snippet_parts.append(f"MARKET TRENDS: {', '.join(market_names)}")
    
    # Add detected spikes
    if 'detected_spikes' in trending_context:
        spikes = trending_context['detected_spikes'][:3]  # Top 3 spikes
        if spikes:
            spike_names = [spike.get('trend_name', '') for spike in spikes]
            snippet_parts.append(f"TREND SPIKES: {', '.join(spike_names)}")
    
    if snippet_parts:
        return f"\n\nTRENDING CONTEXT:\n{chr(10).join(snippet_parts)}\n\nConsider incorporating these trending topics and market insights into your newsletter where relevant."
    
    return ""