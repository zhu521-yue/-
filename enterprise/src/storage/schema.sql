CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    source VARCHAR(100) NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_stream_id ON events(stream_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

CREATE TABLE IF NOT EXISTS student_state (
    learner_id VARCHAR(255) PRIMARY KEY,
    mastery JSONB DEFAULT '{}',
    session_state VARCHAR(50) DEFAULT 'ONBOARDING',
    engagement_state VARCHAR(50) DEFAULT 'FOCUSED',
    last_activity TIMESTAMP DEFAULT NOW(),
    total_submissions INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    id SERIAL PRIMARY KEY,
    knowledge_id VARCHAR(255) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_knowledge_id ON knowledge_embeddings(knowledge_id);
