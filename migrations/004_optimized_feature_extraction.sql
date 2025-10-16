-- Optimized Feature Extraction - No Redundant Newsletter Storage
-- Replace user_writing_samples with direct feature extraction

-- Drop the redundant user_writing_samples table (if it exists)
-- Users will lose their stored newsletters, but we only need features going forward
DROP TABLE IF EXISTS user_writing_samples CASCADE;

-- Enhanced user_newsletter_features table (standalone, no foreign key dependency)
CREATE TABLE IF NOT EXISTS user_newsletter_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Newsletter identification (minimal)
    newsletter_title TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    
    -- LLM-extracted features (the valuable data)
    topic_category TEXT,
    writing_style TEXT,
    voice_characteristics TEXT,
    content_focus TEXT,
    target_length_range TEXT,
    
    -- Metadata
    confidence_score DECIMAL DEFAULT 0.8,
    word_count INTEGER, -- Store word count for length analysis
    
    -- Allow multiple samples per user
    UNIQUE(user_id, newsletter_title)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_newsletter_features_user_id ON user_newsletter_features(user_id);
CREATE INDEX IF NOT EXISTS idx_newsletter_features_topic ON user_newsletter_features(topic_category);
CREATE INDEX IF NOT EXISTS idx_newsletter_features_uploaded ON user_newsletter_features(uploaded_at DESC);

-- Row Level Security
ALTER TABLE user_newsletter_features ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own features" ON user_newsletter_features FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own features" ON user_newsletter_features FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own features" ON user_newsletter_features FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own features" ON user_newsletter_features FOR DELETE USING (auth.uid() = user_id);

-- Grant permissions
GRANT ALL ON user_newsletter_features TO authenticated;
GRANT ALL ON user_newsletter_features TO service_role;

-- ===============================================
-- DYNAMIC SOURCE MANAGEMENT TABLE
-- ===============================================

-- Create user_sources table for dynamic source management
CREATE TABLE IF NOT EXISTS user_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    source_url TEXT NOT NULL,
    display_name TEXT,
    active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 5,
    added_at TIMESTAMP DEFAULT NOW(),
    last_scraped_at TIMESTAMP,
    UNIQUE(user_id, source_url),
    CHECK (priority >= 1 AND priority <= 10)
);

-- Indexes for user_sources
CREATE INDEX IF NOT EXISTS idx_user_sources_user_active ON user_sources(user_id, active);
CREATE INDEX IF NOT EXISTS idx_user_sources_priority ON user_sources(priority DESC);
CREATE INDEX IF NOT EXISTS idx_user_sources_url ON user_sources(source_url);

-- Row Level Security for user_sources
ALTER TABLE user_sources ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_sources
CREATE POLICY "Users can view own sources" ON user_sources FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own sources" ON user_sources FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own sources" ON user_sources FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own sources" ON user_sources FOR DELETE USING (auth.uid() = user_id);

-- Grant permissions for user_sources
GRANT ALL ON user_sources TO authenticated;
GRANT ALL ON user_sources TO service_role;
