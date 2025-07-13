CREATE TABLE IF NOT EXISTS session_logs (
    id SERIAL PRIMARY KEY,
    twitter_handle TEXT,
    timestamp TIMESTAMPTZ,
    tweet_content TEXT,
    ai_reply TEXT,
    likes INTEGER,
    retweets INTEGER
);
