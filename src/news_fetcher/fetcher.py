"""Fetch news from RSS feeds and Google News RSS."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote_plus

import feedparser
import httpx

from .url_safety import is_safe_article_url, is_safe_feed_url

# Feed URLs
GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss/search"
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; NewsFetcher/0.1; +https://github.com/news-fetcher)"

# Feed entry keys (feedparser)
ENTRY_LINK = "link"
ENTRY_LINKS = "links"
ENTRY_TITLE = "title"
ENTRY_SUMMARY = "summary"
ENTRY_DESCRIPTION = "description"
ENTRY_PUBLISHED_PARSED = "published_parsed"
ENTRY_UPDATED_PARSED = "updated_parsed"
LINK_HREF = "href"

# Limits
DESCRIPTION_MAX_LENGTH = 500
HTTP_TIMEOUT_SECONDS = 15.0
PUBLISHED_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


@dataclass
class Article:
    """Article metadata for agent consumption."""

    title: str
    url: str
    source: str
    published: str
    description: str

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published": self.published,
            "description": self.description,
        }


def _parse_published(entry: feedparser.FeedParserDict) -> str:
    """Get published or updated date as ISO string. Returns empty string if missing."""
    for key in (ENTRY_PUBLISHED_PARSED, ENTRY_UPDATED_PARSED):
        parsed = entry.get(key)
        if not parsed:
            continue
        try:
            dt = datetime(*parsed[:6])
            return dt.strftime(PUBLISHED_DATE_FORMAT)
        except (TypeError, ValueError):
            pass
    return ""


def _normalize_url(entry: feedparser.FeedParserDict) -> str:
    """
    Get the article URL from a feed entry.
    Prefers entry.link, then first entry.links[].href.
    Returns empty string if none found (caller skips entry).
    """
    url = entry.get(ENTRY_LINK) or ""
    if not url and entry.get(ENTRY_LINKS):
        first_link = entry[ENTRY_LINKS][0]
        url = first_link.get(LINK_HREF) or ""
    return url.strip()


def _html_strip(text: str) -> str:
    """Remove simple HTML tags. Returns plain text."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _entry_to_article(
    entry: feedparser.FeedParserDict,
    source_name: str,
) -> Article | None:
    """
    Build an Article from a feed entry if the URL is present and safe.
    Returns None if URL is missing or unsafe (caller skips).
    """
    url = _normalize_url(entry)
    if not url or not is_safe_article_url(url):
        return None

    title = (entry.get(ENTRY_TITLE) or "").strip()
    raw_desc = entry.get(ENTRY_SUMMARY) or entry.get(ENTRY_DESCRIPTION) or ""
    description = _html_strip(raw_desc).strip()[:DESCRIPTION_MAX_LENGTH]
    published = _parse_published(entry)

    return Article(
        title=title,
        url=url,
        source=source_name,
        published=published,
        description=description,
    )


def fetch_rss(
    url: str,
    source_name: str,
    *,
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> list[Article]:
    """
    Fetch and parse an RSS/Atom feed.
    Only fetches verified (safe) feed URLs; rejects redirects to unsafe URLs.
    Returns empty list on error or unsafe redirect.
    """
    if not is_safe_feed_url(url):
        return []

    headers = {"User-Agent": DEFAULT_USER_AGENT}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            if not is_safe_feed_url(str(resp.url)):
                return []
            content = resp.text
    except (httpx.HTTPError, httpx.RequestError, OSError):
        return []

    feed = feedparser.parse(content)
    articles = []
    for entry in feed.entries:
        article = _entry_to_article(entry, source_name)
        if article is not None:
            articles.append(article)
    return articles


def fetch_google_news(
    query: str,
    source_name: str,
    *,
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> list[Article]:
    """Fetch Google News RSS for a search query."""
    url = f"{GOOGLE_NEWS_RSS_BASE}?q={quote_plus(query)}&hl=en&gl=US"
    return fetch_rss(url, source_name, timeout=timeout)


def fetch_sources(sources: list[dict]) -> list[Article]:
    """
    Fetch from a list of source configs.
    Each source is either {"name": "...", "url": "..."} (RSS) or
    {"name": "...", "type": "google_news", "query": "..."}.
    One failing feed does not abort the rest.
    """
    all_articles: list[Article] = []
    source_type_google = "google_news"

    for src in sources:
        if not isinstance(src, dict):
            continue
        name = src.get("name") or "Unknown"

        if src.get("type") == source_type_google:
            query = (src.get("query") or "").strip()
            if query:
                all_articles.extend(fetch_google_news(query, name))
            continue

        feed_url = src.get("url")
        if not feed_url:
            continue
        url_str = str(feed_url).strip()
        if is_safe_feed_url(url_str):
            all_articles.extend(fetch_rss(url_str, name))

    return all_articles
