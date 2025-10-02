-- PTT Text Mining Database Schema

-- Create articles table
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(255) UNIQUE NOT NULL,
    board VARCHAR(100) NOT NULL,
    author VARCHAR(255),
    title TEXT,
    date VARCHAR(100),
    content TEXT,
    j_content TEXT,  -- Jieba segmented content
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create comments table
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(255) NOT NULL,
    comment_index INTEGER NOT NULL,
    status VARCHAR(10),  -- 推/噓/→
    commenter VARCHAR(255),
    content TEXT,
    j_content TEXT,  -- Jieba segmented content
    datetime VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(article_id) ON DELETE CASCADE,
    UNIQUE(article_id, comment_index)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_articles_board ON articles(board);
CREATE INDEX IF NOT EXISTS idx_articles_article_id ON articles(article_id);
CREATE INDEX IF NOT EXISTS idx_articles_author ON articles(author);
CREATE INDEX IF NOT EXISTS idx_comments_article_id ON comments(article_id);
CREATE INDEX IF NOT EXISTS idx_comments_commenter ON comments(commenter);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for articles table
CREATE TRIGGER update_articles_updated_at BEFORE UPDATE ON articles
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
