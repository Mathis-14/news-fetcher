"""Fetch news from RSS feeds and Google News RSS."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote_plus

import feedparser
import httpx

from .url_safety import is_safe_article_url, is_safe_feed_url


GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss/search"
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; NewsFetcher/0.1; +https://github.com/news-fetcher)"


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
    """Get published date as ISO string, or empty if missing."""
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                dt = datetime(*parsed[:6])
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except (TypeError, ValueError):
                pass
    return ""


def _normalize_url(entry: feedparser.FeedParserDict) -> str:
    """Prefer link, then first link in links."""
    url = entry.get("link") or ""
    if not url and entry.get("links"):
        url = entry["links"][0].get("href") or ""
    return (url or "").strip()


def _html_strip(text: str) -> str:
    """Remove simple HTML tags for description."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def fetch_rss(url: str, source_name: str, *, timeout: float = 15.0) -> list[Article]:
    """Fetch and parse an RSS/Atom feed. Returns list of Article. Only fetches verified (safe) feed URLs."""
    if not is_safe_feed_url(url):
        return []
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            # SSRF: reject if redirect landed on an unsafe URL (e.g. internal host).
            if not is_safe_feed_url(str(resp.url)):
                return []
            content = resp.text
    except (httpx.HTTPError, httpx.RequestError, OSError):
        return []

    feed = feedparser.parse(content)
    articles: list[Article] = []

    for entry in feed.entries:
        raw_url = _normalize_url(entry)
        if not raw_url or not is_safe_article_url(raw_url):
            continue
        title = (entry.get("title") or "").strip()
        desc = entry.get("summary") or entry.get("description") or ""
        desc = _html_strip(desc).strip()[:500]  # cap length
        published = _parse_published(entry)

        articles.append(
            Article(
                title=title,
                url=raw_url,
                source=source_name,
                published=published,
                description=desc,
            )
        )

    return articles


def fetch_google_news(query: str, source_name: str, *, timeout: float = 15.0) -> list[Article]:
    """Fetch Google News RSS for a search query. Returns list of Article."""
    url = f"{GOOGLE_NEWS_RSS_BASE}?q={quote_plus(query)}&hl=en&gl=US"
    return fetch_rss(url, source_name, timeout=timeout)


def fetch_sources(sources: list[dict]) -> list[Article]:
    """
    Fetch from a list of source configs.
    Each item is either { "name": "...", "url": "..." } or
    { "name": "...", "type": "google_news", "query": "..." }.
    One failing feed does not abort the rest; errors are swallowed per source.
    """
    all_articles: list[Article] = []

    for src in sources:
        if not isinstance(src, dict):
            continue
        name = src.get("name") or "Unknown"
        if src.get("type") == "google_news":
            query = src.get("query") or ""
            if query:
                all_articles.extend(fetch_google_news(query, name))
        else:
            feed_url = src.get("url")
            if feed_url and is_safe_feed_url(str(feed_url).strip()):
                all_articles.extend(fetch_rss(str(feed_url).strip(), name))

    return all_articles
