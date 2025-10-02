# PTT Text Mining

A web crawler for scraping PTT (批踢踢實業坊) board data for text mining analysis.

## Features

- Crawls PTT board posts and comments
- Handles 18+ age verification automatically
- Exports data to JSON format
- Rate limiting to prevent server overload
- Batch processing of multiple boards

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

Options:
- `-b, --board BOARD` - Crawl a specific board by name
- `-f, --file` - Crawl all boards listed in data/boards.txt
- `-l, --list` - List all available boards in boards.txt
- `-h, --help` - Show help message

Output files will be saved to the `output/` directory as JSON files.

## Project Structure

```
ptt-textmining/
├── data/
│   └── boards.txt          # List of boards to crawl
├── output/                  # Crawled data (JSON files)
├── src/
│   └── ptt_textmining/
│       ├── __init__.py
│       └── crawler.py      # Main crawler script
├── requirements.txt
└── README.md
```

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

## Dependencies

- `requests` - HTTP library for making requests
- `beautifulsoup4` - HTML parsing library

## Notes

- The crawler includes rate limiting (0.1s between articles, 0.5s between pages)
- Output is in JSONL format (one JSON object per line) for efficient streaming and processing
- When using file mode (`-f`), boards are processed sequentially and removed from `boards.txt` after completion
