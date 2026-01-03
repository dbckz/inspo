"""Fetch quotes from a Google Doc."""

import re
import requests
from typing import List, Optional
from config import GOOGLE_DOC_URL, FALLBACK_QUOTES


def extract_doc_id(url: str) -> Optional[str]:
    """Extract the document ID from a Google Docs URL."""
    patterns = [
        r'/document/d/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_quotes_from_google_doc(url: str = GOOGLE_DOC_URL) -> List[str]:
    """
    Fetch quotes from a publicly shared Google Doc.

    The doc should be shared with 'Anyone with the link can view'.
    Each non-empty line in the document is treated as a separate quote.
    """
    doc_id = extract_doc_id(url)

    if not doc_id or doc_id == "YOUR_DOCUMENT_ID":
        print("No valid Google Doc ID configured. Using fallback quotes.")
        return FALLBACK_QUOTES

    # Use the export URL to get plain text content
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

    try:
        response = requests.get(export_url, timeout=10)
        response.raise_for_status()

        # Parse the content - each line is a quote
        content = response.text
        quotes = [
            line.strip()
            for line in content.split('\n')
            if line.strip() and len(line.strip()) > 5
        ]

        if quotes:
            print(f"Successfully loaded {len(quotes)} quotes from Google Doc.")
            return quotes
        else:
            print("No quotes found in document. Using fallback quotes.")
            return FALLBACK_QUOTES

    except requests.exceptions.RequestException as e:
        print(f"Error fetching quotes from Google Doc: {e}")
        print("Using fallback quotes.")
        return FALLBACK_QUOTES


def get_random_quote(quotes: Optional[List[str]] = None) -> str:
    """Get a random quote from the list."""
    import random

    if quotes is None:
        quotes = fetch_quotes_from_google_doc()

    return random.choice(quotes)


if __name__ == "__main__":
    # Test the fetcher
    quotes = fetch_quotes_from_google_doc()
    print(f"\nLoaded {len(quotes)} quotes:")
    for i, quote in enumerate(quotes[:5], 1):
        print(f"  {i}. {quote[:80]}...")
