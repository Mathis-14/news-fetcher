"""Keyword filtering and URL deduplication."""

from __future__ import annotations

from pathlib import Path

from .fetcher import Article
from .url_safety import is_safe_article_url


def _normalize_for_match(text: str) -> str:
    return (text or "").lower().strip()


def article_matches_keywords(article: Article, keywords: list[str]) -> bool:
    """True if any keyword appears in title or description (case-insensitive)."""
    if not keywords:
        return True
    title = _normalize_for_match(article.title)
    desc = _normalize_for_match(article.description)
    combined = f"{title} {desc}"
    for kw in keywords:
        if kw and _normalize_for_match(kw) in combined:
            return True
    return False


def filter_by_keywords(articles: list[Article], keywords: list[str]) -> list[Article]:
    """Keep only articles that match at least one keyword. If keywords is empty, keep all."""
    if not keywords:
        return articles
    return [a for a in articles if article_matches_keywords(a, keywords)]


def dedupe_by_url(articles: list[Article]) -> list[Article]:
    """Remove duplicates by URL, keeping first occurrence."""
    seen: set[str] = set()
    out: list[Article] = []
    for a in articles:
        url = (a.url or "").strip()
        if url and url not in seen:
            seen.add(url)
            out.append(a)
    return out


def load_seen_urls(path: Path) -> set[str]:
    """Load previously seen URLs from file (one URL per line). Only returns verified (safe) URLs."""
    if not path.exists():
        return set()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    seen = set()
    for line in text.splitlines():
        url = line.strip()
        if url and is_safe_article_url(url):
            seen.add(url)
    return seen


def save_seen_urls(path: Path, urls: set[str]) -> None:
    """Write URLs to file, one per line. Only verified (safe) URLs are written."""
    safe = {u for u in urls if u and is_safe_article_url(u)}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(sorted(safe)) + "\n", encoding="utf-8")
    except OSError:
        pass  # e.g. read-only filesystem; do not crash the run


def filter_already_seen(
    articles: list[Article],
    seen_path: Path,
    *,
    update_seen: bool = True,
) -> list[Article]:
    """
    Return only articles whose URL is not in the seen set.
    If update_seen is True, add all current article URLs (verified only) to the seen file.
    """
    seen = load_seen_urls(seen_path)
    new_articles = [a for a in articles if (a.url or "").strip() not in seen]
    if update_seen:
        for a in articles:
            url = (a.url or "").strip()
            if url and is_safe_article_url(url):
                seen.add(url)
        save_seen_urls(seen_path, seen)
    return new_articles
