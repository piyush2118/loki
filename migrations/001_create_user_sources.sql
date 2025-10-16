-- Migration: Create user_sources table for dynamic source management
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS user_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Essential fields
    source_url TEXT NOT NULL,               -- Store exactly what user pastes
    display_name TEXT,                      -- User-friendly name (optional)
    active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 5,
    
    -- Minimal metadata
    added_at TIMESTAMP DEFAULT NOW(),
    last_scraped_at TIMESTAMP,
    
    -- Constraints
    UNIQUE(user_id, source_url),
    CHECK (priority >= 1 AND priority <= 10)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_sources_user_active ON user_sources(user_id, active);
CREATE INDEX IF NOT EXISTS idx_user_sources_priority ON user_sources(priority DESC);
CREATE INDEX IF NOT EXISTS idx_user_sources_url ON user_sources(source_url);

-- Enable Row Level Security (RLS)
ALTER TABLE user_sources ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access their own sources
CREATE POLICY "Users can view own sources"
    ON user_sources FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sources"
    ON user_sources FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sources"
    ON user_sources FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sources"
    ON user_sources FOR DELETE
    USING (auth.uid() = user_id);

-- Grant permissions
GRANT ALL ON user_sources TO authenticated;
GRANT ALL ON user_sources TO service_role;

