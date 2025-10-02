# PTT Text Mining

A comprehensive web crawler and text mining toolkit for scraping PTT (批踢踢實業坊) board data with Chinese NLP support.

## Features

### Web Crawler
- Crawls PTT board posts and comments
- Handles 18+ age verification automatically
- Exports data to JSONL format (streaming-friendly)
- Configurable rate limiting to prevent server overload
- Batch processing of multiple boards

### Text Processing & Storage
- **PostgreSQL Database** - Structured storage with relational schema
- **Jieba Text Segmentation** - Chinese word segmentation for NLP tasks
- Automatic text preprocessing during import
- Separate tables for articles and comments
- Efficient indexing for fast queries

### Text Mining Ready
The segmented text (`j_content`) enables various text mining analyses:
- **TF-IDF (Term Frequency-Inverse Document Frequency)** - Keyword extraction
- **Word Cloud** - Visualization of frequent terms
- **Sentiment Analysis** - Using Chinese sentiment dictionaries
- **Topic Modeling** - LDA, NMF for discovering topics
- **N-gram Analysis** - Common phrase extraction

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ptt-textmining
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

The crawler supports three modes of operation:

### 1. List Available Boards

View all boards listed in `data/boards.txt`:

```bash
python src/ptt_textmining/crawler.py -l
# or
python src/ptt_textmining/crawler.py --list
```

### 2. Crawl a Specific Board

Crawl a single board by name:

```bash
python src/ptt_textmining/crawler.py -b NBA
# or
python src/ptt_textmining/crawler.py --board Stock
```

### 3. Crawl Multiple Boards from File

First, add board names to `data/boards.txt` (one per line):
```
Stock
NBA
Gossiping
MobileComm
```

Then run:
```bash
python src/ptt_textmining/crawler.py -f
# or
python src/ptt_textmining/crawler.py --file
```

**Note:** When using file mode (`-f`), boards are processed sequentially and removed from `boards.txt` after completion.

### Command-Line Options

```bash
python src/ptt_textmining/crawler.py -h
```

**Basic Options:**
- `-b, --board BOARD` - Crawl a specific board by name
- `-f, --file` - Crawl all boards listed in data/boards.txt
- `-l, --list` - List all available boards in boards.txt
- `-h, --help` - Show help message

**Rate Limiting Options:**
- `--article-delay SECONDS` - Delay between articles in seconds (default: 0.1)
- `--page-delay SECONDS` - Delay between pages in seconds (default: 0.5)

**Examples:**

```bash
# Use default rate limits
python src/ptt_textmining/crawler.py -b NBA

# Faster crawling (use with caution)
python src/ptt_textmining/crawler.py -b NBA --article-delay 0.05 --page-delay 0.2

# Slower/safer crawling
python src/ptt_textmining/crawler.py -b NBA --article-delay 0.5 --page-delay 1.0

# Crawl from file with custom delays
python src/ptt_textmining/crawler.py -f --article-delay 0.2 --page-delay 0.8
```

Output files will be saved to the `output/` directory as JSONL files.

## Output Format

Data is saved in **JSONL (JSON Lines)** format - one JSON object per line. Each line represents a single article with the following structure:

```json
{"id": "article_id", "author": "author_name", "title": "post_title", "date": "post_date", "content": "main_content", "comments": {"1": {"status": "推/噓/→", "commenter": "user_id", "content": "comment_text", "datetime": "comment_time"}}}
```

**Example formatted for readability:**
```json
{
    "id": "M.1234567890.A.123",
    "author": "username (User Name)",
    "title": "[問題] Example Title",
    "date": "Mon Jan 01 12:00:00 2024",
    "content": "Article content here...",
    "comments": {
        "1": {
            "status": "推",
            "commenter": "user123",
            "content": "Great post!",
            "datetime": "01/01 12:30"
        }
    }
}
```

**Output files:** `output/{board_name}.jsonl` (e.g., `output/NBA.jsonl`)

### Reading JSONL Files

**Python (pandas):**
```python
import pandas as pd
df = pd.read_json('output/NBA.jsonl', lines=True)
```

**Python (standard library):**
```python
import json
with open('output/NBA.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        article = json.loads(line)
        print(article['title'])
```

**Command line (jq):**
```bash
cat output/NBA.jsonl | jq '.title'
```

## Database Setup

This project includes a PostgreSQL database for storing and analyzing crawled data with jieba text segmentation.

### 1. Start the Database

```bash
docker compose up -d
```

This will start a PostgreSQL container with the database schema automatically created.

### 2. Import JSONL Data to Database

```bash
# Import a specific board
python src/ptt_textmining/import_to_db.py output/NBA.jsonl

# Specify board name manually
python src/ptt_textmining/import_to_db.py output/NBA.jsonl -b NBA
```

The import script will:
- Read JSONL files line by line
- Segment Chinese text using jieba
- Store articles and comments in separate tables
- Add `j_content` column with jieba-segmented text

### 3. Database Schema

**Articles Table:**
- `id` - Primary key
- `article_id` - PTT article ID (unique)
- `board` - Board name
- `author` - Article author
- `title` - Article title
- `date` - Post date
- `content` - Original content
- `j_content` - Jieba-segmented content
- `created_at`, `updated_at` - Timestamps

**Comments Table:**
- `id` - Primary key
- `article_id` - Foreign key to articles
- `comment_index` - Comment number
- `status` - Push type (推/噓/→)
- `commenter` - Commenter username
- `content` - Original comment
- `j_content` - Jieba-segmented comment
- `datetime` - Comment timestamp

### 4. Database Connection

Default credentials:
- **Host:** localhost
- **Port:** 5432
- **Database:** ptt_textmining
- **User:** ptt_user
- **Password:** ptt_password

### 5. Query Examples

```sql
-- Get all articles from a board
SELECT * FROM articles WHERE board = 'NBA';

-- Get article with comments
SELECT a.title, c.commenter, c.content
FROM articles a
LEFT JOIN comments c ON a.article_id = c.article_id
WHERE a.article_id = 'M.1759363294.A.FB7';

-- Search jieba-segmented content
SELECT title, j_content
FROM articles
WHERE j_content LIKE '%球員%';
```

### 6. Stop the Database

```bash
docker compose down
```

To remove all data:
```bash
docker compose down -v
```

## Text Mining Examples

Once data is imported to the database, you can perform various text mining analyses using the jieba-segmented content:

### TF-IDF Analysis

```python
from sklearn.feature_extraction.text import TfidfVectorizer
import psycopg2
import pandas as pd

# Connect to database
conn = psycopg2.connect(
    host="localhost", database="ptt_textmining",
    user="ptt_user", password="ptt_password"
)

# Load segmented content
df = pd.read_sql("SELECT title, j_content FROM articles WHERE board='NBA'", conn)

# Calculate TF-IDF
vectorizer = TfidfVectorizer(max_features=100)
tfidf_matrix = vectorizer.fit_transform(df['j_content'].fillna(''))

# Get top keywords
feature_names = vectorizer.get_feature_names_out()
print("Top keywords:", feature_names[:20])
```

### Word Frequency Analysis

```python
from collections import Counter

# Get all segmented words
cursor = conn.cursor()
cursor.execute("SELECT j_content FROM articles WHERE board='NBA'")
all_text = ' '.join([row[0] for row in cursor.fetchall() if row[0]])

# Count word frequency
words = all_text.split()
word_freq = Counter(words)
print("Most common words:", word_freq.most_common(20))
```

### Word Cloud Generation

```python
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Generate word cloud from segmented text
wordcloud = WordCloud(
    font_path='/System/Library/Fonts/PingFang.ttc',  # Mac Chinese font
    width=800, height=400,
    background_color='white'
).generate(all_text)

plt.figure(figsize=(10, 5))
plt.imshow(wordcloud, interpolation='bilinear')
plt.axis('off')
plt.show()
```

## Dependencies

### Core Dependencies
- `requests` - HTTP library for making requests
- `beautifulsoup4` - HTML parsing library
- `jieba` - Chinese text segmentation
- `psycopg2-binary` - PostgreSQL database adapter

### Optional (for text mining)
- `scikit-learn` - TF-IDF and machine learning
- `pandas` - Data analysis
- `wordcloud` - Word cloud visualization
- `matplotlib` - Plotting and visualization

## Project Structure

```
ptt-textmining/
├── data/
│   └── boards.txt              # List of boards to crawl
├── database/
│   └── init.sql                # Database schema
├── output/                      # Crawled data (JSONL files)
├── src/
│   └── ptt_textmining/
│       ├── __init__.py
│       ├── crawler.py          # Web crawler
│       └── import_to_db.py     # Database importer with jieba
├── docker-compose.yml          # PostgreSQL container
├── requirements.txt
└── README.md
```

## Notes

- **Rate Limiting:** Default delays are 0.1s between articles and 0.5s between pages. These can be customized using `--article-delay` and `--page-delay` options
- **Output Format:** Data is saved in JSONL format (one JSON object per line) for efficient streaming and processing
- **File Mode:** When using `-f`, boards are processed sequentially and removed from `boards.txt` after completion
- **Database:** PostgreSQL with jieba text segmentation for Chinese text analysis
- **Text Mining:** The `j_content` field contains space-separated Chinese words ready for NLP analysis
