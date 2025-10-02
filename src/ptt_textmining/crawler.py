"""PTT Web Crawler for text mining.

This module crawls PTT (批踢踢實業坊) board data including posts and comments.
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

# Constants
PTT_BASE_URL = "https://www.ptt.cc"
DATA_DIR = Path(__file__).parent.parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
BOARDS_FILE = DATA_DIR / "boards.txt"

# Global session
session = requests.Session()


def get_board_page(board: str) -> BeautifulSoup:
    """Get board index page, handling 18+ confirmation if needed.

    Args:
        board: Board name

    Returns:
        BeautifulSoup object of the board page
    """
    url = f"{PTT_BASE_URL}/bbs/{board}/index.html"
    response = session.get(url)

    # Check if 18+ confirmation is required
    if "over18" in response.url:
        payload = {
            "from": f"/bbs/{board}/index.html",
            "yes": "yes"
        }
        response = session.post(f"{PTT_BASE_URL}/ask/over18", data=payload)

    return BeautifulSoup(response.text, "html.parser")


def extract_page_number(url: str) -> int:
    """Extract page number from URL.

    Args:
        url: URL containing page index

    Returns:
        Page number as integer
    """
    start_idx = url.find("index")
    end_idx = url.find(".html")
    return int(url[start_idx + 5:end_idx])


def crawl_board_pages(url_list: List[str], board_name: str) -> None:
    """Crawl all pages in the board and extract articles.

    Args:
        url_list: List of board page URLs to crawl
        board_name: Name of the board
    """
    count = 0
    total = len(url_list)

    while url_list:
        try:
            url = url_list.pop(0)
            response = session.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Check if service is temporarily unavailable
            if soup.title and "Service Temporarily" in soup.title.text:
                url_list.append(url)
                time.sleep(1)
            else:
                count += 1
                # Extract article links from the page
                for entry in soup.find_all(class_="r-ent"):
                    link = entry.find("a")
                    if link:
                        article_url = PTT_BASE_URL + link["href"]
                        time.sleep(0.1)  # Rate limiting
                        parse_article(article_url, board_name)

                print(f"Download: {board_name} {100 * count / total:.1f}%")

        except Exception as e:
            print(f"Exception: {url}")
            print(e)
            time.sleep(1)
        else:
            time.sleep(0.5)  # Rate limiting


def safe_extract_meta(soup: BeautifulSoup, class_tag: str, index: int,
                      field_name: str) -> str:
    """Safely extract metadata from article, returning default if not found.

    Args:
        soup: BeautifulSoup object
        class_tag: CSS class selector
        index: Index of the element
        field_name: Name of the field for default value

    Returns:
        Extracted content or default value
    """
    try:
        return soup.select(class_tag)[index].text
    except (IndexError, AttributeError):
        return f"no {field_name}"


def parse_article(url: str, board_name: str) -> None:
    """Parse a single article and save to file.

    Args:
        url: Article URL
        board_name: Name of the board
    """
    response = session.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract article metadata
    author = safe_extract_meta(soup, ".article-meta-value", 0, "author")
    title = safe_extract_meta(soup, ".article-meta-value", 2, "title")
    date = safe_extract_meta(soup, ".article-meta-value", 3, "date")

    # Extract article ID from URL
    article_id = url.replace(f"{PTT_BASE_URL}/bbs/{board_name}/", "").replace(".html", "")

    # Extract main content
    try:
        content = soup.find(id="main-content")
        # Remove metadata lines
        for element in content.select("div.article-metaline"):
            element.extract()
        for element in content.select("div.article-metaline-right"):
            element.extract()

        content_text = content.text
        # Split at PTT signature
        signature = "※ 發信站: 批踢踢實業坊(ptt.cc),"
        main_content = content_text.split(signature)[0].replace("\n", "  ")
    except Exception:
        main_content = "main_content error"

    # Extract comments/pushes
    comments = {}
    for idx, tag in enumerate(soup.select("div.push"), start=1):
        try:
            # Safely extract each element
            push_tag_elem = tag.find("span", {"class": "push-tag"})
            push_user_elem = tag.find("span", {"class": "push-userid"})
            push_content_elem = tag.find("span", {"class": "push-content"})
            push_time_elem = tag.find("span", {"class": "push-ipdatetime"})

            # Skip if any required element is missing
            if not all([push_tag_elem, push_user_elem, push_content_elem, push_time_elem]):
                continue

            push_tag = push_tag_elem.text
            push_user = push_user_elem.text
            push_content = push_content_elem.text[1:] if len(push_content_elem.text) > 0 else ""
            push_time = push_time_elem.text.rstrip()

            comments[idx] = {
                "status": push_tag,
                "commenter": push_user,
                "content": push_content,
                "datetime": push_time
            }
        except Exception as e:
            print(f"Error parsing comment: {e}")

    # Build article data
    article_data = {
        "id": article_id,
        "author": author,
        "title": title,
        "date": date,
        "content": main_content,
        "comments": comments
    }

    # Convert to JSONL format (one line per record, no trailing comma)
    json_line = json.dumps(article_data, ensure_ascii=False) + "\n"
    save_to_file(json_line, board_name)


def save_to_file(data: str, board_name: str) -> None:
    """Save data to output file in JSONL format.

    Args:
        data: JSON line to save
        board_name: Name of the board (used as filename)
    """
    output_file = OUTPUT_DIR / f"{board_name}.jsonl"
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(data)


def process_boards() -> None:
    """Process all boards listed in boards.txt file.

    Reads boards from file, processes each one, and removes it from the list.
    Continues recursively until all boards are processed.
    """
    with open(BOARDS_FILE, "r", encoding="utf-8") as f:
        boards = f.readlines()

    if not boards:
        print("Done processing all boards")
        return

    # Process first board
    board_name = boards[0].strip()
    crawl_board(board_name)

    # Remove processed board from file
    with open(BOARDS_FILE, "w", encoding="utf-8") as f:
        f.writelines(boards[1:])

    time.sleep(3)
    process_boards()  # Recursively process remaining boards


def crawl_board(board_name: str) -> None:
    """Crawl all pages of a specific board.

    Args:
        board_name: Name of the board to crawl
    """
    soup = get_board_page(board_name)

    # Get total number of pages
    last_page_url = soup.select(".btn.wide")[1]["href"]
    total_pages = extract_page_number(last_page_url) + 1

    # Build list of page URLs
    page_urls = []
    for page_num in range(total_pages, 0, -1):
        page_url = f"{PTT_BASE_URL}/bbs/{board_name}/index{page_num}.html"
        page_urls.append(page_url)
        print(page_url)

    # Initialize output file (clear existing content for fresh start)
    output_file = OUTPUT_DIR / f"{board_name}.jsonl"
    output_file.write_text("", encoding="utf-8")

    # Crawl all pages
    crawl_board_pages(page_urls, board_name)

    print(f"{board_name} crawling completed")


def list_available_boards() -> None:
    """List all boards available in boards.txt file."""
    if not BOARDS_FILE.exists():
        print(f"Error: {BOARDS_FILE} not found")
        sys.exit(1)

    with open(BOARDS_FILE, "r", encoding="utf-8") as f:
        boards = [line.strip() for line in f if line.strip()]

    if not boards:
        print("No boards found in boards.txt")
    else:
        print("Available boards in boards.txt:")
        for board in boards:
            print(f"  - {board}")


def main() -> None:
    """Main entry point for the crawler."""
    parser = argparse.ArgumentParser(
        description="PTT Web Crawler for scraping board data"
    )
    parser.add_argument(
        "-b", "--board",
        type=str,
        help="Specific board name to crawl (e.g., Stock, NBA)"
    )
    parser.add_argument(
        "-f", "--file",
        action="store_true",
        help="Crawl all boards listed in data/boards.txt"
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all available boards in boards.txt"
    )

    args = parser.parse_args()

    # Create necessary directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Handle list command
    if args.list:
        list_available_boards()
        return

    # Handle board-specific crawl
    if args.board:
        print(f"Crawling board: {args.board}")
        crawl_board(args.board)
        return

    # Handle file-based crawl
    if args.file:
        print("Crawling boards from boards.txt")
        process_boards()
        return

    # No arguments provided - show help
    parser.print_help()
    print("\nTip: Use -l to list available boards, -b to crawl a specific board, or -f to crawl from file")


if __name__ == "__main__":
    main()
