import sys
sys.path.insert(0, "src")

import requests
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET
from news_fetcher.fetcher import is_safe_feed_url

GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss/search"
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; NewsFetcher/0.1; +https://github.com/news-fetcher)"
HTTP_TIMEOUT_SECONDS = 15.0

# Test Google News query
query = "artificial intelligence"
url = f"{GOOGLE_NEWS_RSS_BASE}?q={quote_plus(query)}&hl=en&gl=US"
print(f"Testing Google News query: {url}")

try:
    resp = requests.get(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=HTTP_TIMEOUT_SECONDS,
        allow_redirects=True,
    )
    print(f"HTTP status: {resp.status_code}")
    print(f"Final URL: {resp.url}")
    
    if not is_safe_feed_url(resp.url):
        print("ERROR: Unsafe feed URL")
        exit(1)
    
    content = resp.text
    print(f"Fetched {len(content)} bytes")
    
    # Try parsing
    root = ET.fromstring(content)
    print("XML parsed successfully")
    
    # Count items
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    print(f"Found {len(items)} items")
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")