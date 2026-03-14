"""
Public API for programmatic use (e.g. by agents).
No side effects: no file writes, no sys.exit, no console output.
"""

from __future__ import annotations

from pathlib import Path

from .fetcher import Article, fetch_sources
from .filter import dedupe_by_url, filter_by_keywords
from .config_loader import load_config
from .url_safety import is_safe_feed_url


def _filter_safe_sources(raw_sources: list[dict]) -> list[dict]:
    """Keep only sources with valid config and safe feed URLs. No console output."""
    safe = []
    for src in raw_sources:
        if src.get("type") == "google_news":
            safe.append(src)
            continue
        feed_url = src.get("url")
        if not feed_url:
            continue
        url_str = str(feed_url).strip()
        if is_safe_feed_url(url_str):
            safe.append(src)
    return safe


def fetch_news(config_path: str | Path) -> list[dict]:
    """
    Load config, fetch from all sources, filter by keywords, dedupe by URL.
    Returns list of article dicts (title, url, source, published, description).
    Raises FileNotFoundError if config is missing, OSError on config read error.
    No side effects: does not write files or update .seen_urls.
    """
    config_path = Path(config_path).resolve()
    config = load_config(config_path)
    keywords = config["keywords"]
    sources = _filter_safe_sources(config["sources"])

    articles: list[Article] = fetch_sources(sources)
    articles = dedupe_by_url(articles)
    articles = filter_by_keywords(articles, keywords)

    return [a.to_dict() for a in articles]
