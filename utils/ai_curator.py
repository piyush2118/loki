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
        
        # DEBUG: Show whether we're using database features or fallback
        if user_features:
            print(f"✅ Using database features for user {user_id}:")
            print(f"   - Writing Style: {user_features.get('writing_style')}")
            print(f"   - Voice: {user_features.get('voice_characteristics')}")
            print(f"   - Content Focus: {user_features.get('content_focus')}")
            print(f"   - Target Length: {user_features.get('target_length_range')}")
            print(f"   - Sample Count: {user_features.get('sample_count')}")
        else:
            print(f"⚠️ No voice training features found for user {user_id} - using neutral fallback")
    
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

USER STYLE PROFILE:
- Writing Style: {user_features['writing_style']}
- Voice: {user_features['voice_characteristics']}
- Content Focus: {user_features['content_focus']}
- Topic Category: {user_features['topic_category']}
- Target Length: {user_features['target_length_range']} words

REQUIRED TEMPLATE STRUCTURE:
You MUST follow this exact structure:

**Introduction**
[2-3 sentences setting context for the articles below. Use {user_features['voice_characteristics']} tone]

**Curated Links:**
[Select 3-5 most important articles and format as:]
* **Article Title**: Brief summary (1-2 sentences) explaining why it matters. [Read more](source_url)

**Trends to Watch:**
[Identify exactly 3 trending topics from the articles AND trending context below. For each:]
* **Trend Name**: Brief explanation (1-2 sentences) with supporting evidence. [Explore](#)

ARTICLES TO CURATE:
{context}

INSTRUCTIONS FOR STYLE:
- Apply your {user_features['writing_style']} writing style throughout
- Maintain {user_features['voice_characteristics']} voice in all sections
- Focus content on {user_features['content_focus']} when selecting which articles to highlight
- Total length should be {user_features['target_length_range']} words
- Use bold headings, bullet points for structure
- Include descriptive link text like "Read more", "Learn more", "Discover here"

Generate the newsletter following the template structure exactly.{feedback_snippet}{trending_snippet}"""
        
    else:
        # Fallback: User has not trained their voice - use neutral structure-only approach
        # NO style assumptions - structure only
        prompt = f"""You are an AI newsletter curator. Create a newsletter following this exact template:

REQUIRED STRUCTURE:

**Introduction**
[2-3 sentences setting context about {', '.join(user_topics)}]

**Curated Links:**
[Select 3-5 most important articles and format as:]
* **Article Title**: Brief summary explaining why it matters. [Read more](url)

**Trends to Watch:**
[Identify exactly 3 trending topics. For each:]
* **Trend Name**: Brief explanation with supporting evidence. [Explore](#)

ARTICLES TO CURATE:
{context}

INSTRUCTIONS:
- Follow the template structure exactly
- Use clear, informative writing
- Format with bold headings and bullet points
- Include descriptive link text
- Keep summaries concise and factual
NOTE: User has not trained their writing style yet. Use neutral, clear tone.{feedback_snippet}{trending_snippet}"""
    
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
        temperature=0.4 if revision_mode else 0.5,  # Lower for better structure adherence
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
    """Build trending context snippet specifically for 'Trends to Watch' section"""
    if not trending_context:
        return ""
    
    snippet_parts = []
    snippet_parts.append("\n\nTRENDING CONTEXT FOR 'TRENDS TO WATCH' SECTION:")
    snippet_parts.append("Use the following data to help identify the 3 trends for your 'Trends to Watch' section:")
    snippet_parts.append("")
    
    # Add trending topics from user's sources
    if 'user_trends' in trending_context:
        trends = trending_context['user_trends'][:5]  # Top 5 user trends
        if trends:
            snippet_parts.append("TOP TRENDS FROM YOUR SOURCES:")
            for i, trend in enumerate(trends, 1):
                trend_name = trend.get('name', trend.get('topic', ''))
                score = trend.get('composite_score', trend.get('relevance_score', 0))
                snippet_parts.append(f"  {i}. {trend_name} (score: {score:.2f})")
            snippet_parts.append("")
    
    # Add market trends
    if 'market_intelligence' in trending_context:
        market_data = trending_context['market_intelligence']
        if 'overall_trends' in market_data:
            market_trends = market_data['overall_trends'][:3]  # Top 3 market trends
            if market_trends:
                snippet_parts.append("BROADER MARKET TRENDS:")
                for i, trend in enumerate(market_trends, 1):
                    query = trend.get('query', '')
                    snippet_parts.append(f"  {i}. {query}")
                snippet_parts.append("")
    
    # Add detected spikes (high priority)
    if 'detected_spikes' in trending_context:
        spikes = trending_context['detected_spikes'][:2]  # Top 2 spikes
        if spikes:
            snippet_parts.append("TRENDING SPIKES (High Priority):")
            for i, spike in enumerate(spikes, 1):
                spike_name = spike.get('trend_name', '')
                severity = spike.get('severity', '')
                snippet_parts.append(f"  {i}. {spike_name} ({severity} spike)")
            snippet_parts.append("")
    
    if len(snippet_parts) > 1:  # More than just the header
        snippet_parts.append("INSTRUCTIONS:")
        snippet_parts.append("- Select 3 trends total for 'Trends to Watch' section")
        snippet_parts.append("- Prioritize spikes if present")
        snippet_parts.append("- Combine data from both articles AND trending context above")
        snippet_parts.append("- Each trend should have: name, 1-2 sentence explanation, and relevance to articles")
        return "\n".join(snippet_parts)
    
    return ""