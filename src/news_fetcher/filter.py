"""Keyword filtering and URL deduplication."""

from __future__ import annotations

from pathlib import Path

from .fetcher import Article
from .url_safety import is_safe_article_url

FILE_ENCODING = "utf-8"


def _article_url(article: Article) -> str:
    """Return normalized URL string for an article, or empty string."""
    return (article.url or "").strip()


def _normalize_for_match(text: str) -> str:
    """Lowercase and strip for keyword matching."""
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
    """Keep only articles that match at least one keyword. Empty keywords = keep all."""
    if not keywords:
        return articles
    return [a for a in articles if article_matches_keywords(a, keywords)]


def dedupe_by_url(articles: list[Article]) -> list[Article]:
    """Remove duplicates by URL, keeping first occurrence."""
    seen: set[str] = set()
    out: list[Article] = []
    for a in articles:
        url = _article_url(a)
        if url and url not in seen:
            seen.add(url)
            out.append(a)
    return out


def load_seen_urls(path: Path) -> set[str]:
    """Load previously seen URLs from file (one per line). Only returns safe URLs."""
    if not path.exists():
        return set()
    try:
        text = path.read_text(encoding=FILE_ENCODING)
    except OSError:
        return set()
    return {
        line.strip()
        for line in text.splitlines()
        if (line.strip() and is_safe_article_url(line.strip()))
    }


def save_seen_urls(path: Path, urls: set[str]) -> None:
    """Write URLs to file, one per line. Only safe URLs are written."""
    safe = {u for u in urls if u and is_safe_article_url(u)}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(sorted(safe)) + "\n", encoding=FILE_ENCODING)
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
    If update_seen is True, add current article URLs (verified only) to the seen file.
    """
    seen = load_seen_urls(seen_path)
    new_articles = [a for a in articles if _article_url(a) not in seen]

    if update_seen:
        for a in articles:
            url = _article_url(a)
            if url and is_safe_article_url(url):
                seen.add(url)
        save_seen_urls(seen_path, seen)

    return new_articles
