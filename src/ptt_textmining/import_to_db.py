"""Import JSONL data to PostgreSQL database with jieba text segmentation."""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

import jieba
import psycopg2
from psycopg2.extras import execute_batch

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "ptt_textmining",
    "user": "ptt_user",
    "password": "ptt_password"
}


def segment_text(text: str) -> str:
    """Segment Chinese text using jieba.

    Args:
        text: Input text to segment

    Returns:
        Space-separated segmented text
    """
    if not text or text.startswith("no ") or text == "main_content error":
        return ""

    # Segment text and join with spaces
    words = jieba.cut(text)
    return " ".join(words)


def connect_db() -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database.

    Returns:
        Database connection object
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)


def import_article(conn: psycopg2.extensions.connection, article: Dict, board: str) -> None:
    """Import a single article and its comments to database.

    Args:
        conn: Database connection
        article: Article data from JSONL
        board: Board name
    """
    cursor = conn.cursor()

    try:
        # Segment article content
        j_content = segment_text(article.get("content", ""))

        # Insert article
        article_sql = """
            INSERT INTO articles (article_id, board, author, title, date, content, j_content)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (article_id) DO UPDATE SET
                author = EXCLUDED.author,
                title = EXCLUDED.title,
                date = EXCLUDED.date,
                content = EXCLUDED.content,
                j_content = EXCLUDED.j_content,
                updated_at = CURRENT_TIMESTAMP
        """

        cursor.execute(article_sql, (
            article["id"],
            board,
            article.get("author", ""),
            article.get("title", ""),
            article.get("date", ""),
            article.get("content", ""),
            j_content
        ))

        # Prepare comments data
        comments = article.get("comments", {})
        if comments:
            comment_data = []
            for idx, comment in comments.items():
                j_comment_content = segment_text(comment.get("content", ""))
                comment_data.append((
                    article["id"],
                    int(idx),
                    comment.get("status", ""),
                    comment.get("commenter", ""),
                    comment.get("content", ""),
                    j_comment_content,
                    comment.get("datetime", "")
                ))

            # Batch insert comments
            comment_sql = """
                INSERT INTO comments (article_id, comment_index, status, commenter, content, j_content, datetime)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (article_id, comment_index) DO UPDATE SET
                    status = EXCLUDED.status,
                    commenter = EXCLUDED.commenter,
                    content = EXCLUDED.content,
                    j_content = EXCLUDED.j_content,
                    datetime = EXCLUDED.datetime
            """
            execute_batch(cursor, comment_sql, comment_data)

        conn.commit()

    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error importing article {article.get('id', 'unknown')}: {e}")
    finally:
        cursor.close()


def import_jsonl_file(file_path: Path, board: str) -> None:
    """Import JSONL file to database.

    Args:
        file_path: Path to JSONL file
        board: Board name
    """
    if not file_path.exists():
        print(f"Error: File {file_path} not found")
        sys.exit(1)

    conn = connect_db()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            count = 0
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    article = json.loads(line)
                    import_article(conn, article, board)
                    count += 1
                    if count % 100 == 0:
                        print(f"Imported {count} articles...")
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON on line {line_num}: {e}")
                    continue

        print(f"\nImport completed! Total articles imported: {count}")

    finally:
        conn.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import PTT JSONL data to PostgreSQL database with jieba segmentation"
    )
    parser.add_argument(
        "file",
        type=str,
        help="Path to JSONL file (e.g., output/NBA.jsonl)"
    )
    parser.add_argument(
        "-b", "--board",
        type=str,
        help="Board name (auto-detected from filename if not specified)"
    )

    args = parser.parse_args()

    file_path = Path(args.file)

    # Auto-detect board name from filename if not provided
    if args.board:
        board = args.board
    else:
        board = file_path.stem

    print(f"Importing {file_path} to database (board: {board})...")
    print("Initializing jieba...")
    jieba.initialize()  # Preload jieba dictionary

    import_jsonl_file(file_path, board)


if __name__ == "__main__":
    main()
