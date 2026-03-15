#!/usr/bin/env python3
"""Fetch news via news_fetcher, store in SQLite, and optionally enrich for alerts/reports."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from news_db import DEFAULT_DB_PATH, DEFAULT_IMPORTANCE_SCORE, get_connection
from news_fetcher import fetch_news

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Config path for the fetcher (relative to cwd)
DEFAULT_CONFIG_PATH: Path = Path("config.yaml")

# Schema: same as before so alerts/browse_news keep working
CREATE_ARTICLES_TABLE = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT UNIQUE,
    source TEXT,
    published TEXT,
    description TEXT,
    summary TEXT,
    bullet_points TEXT,
    market_implications TEXT,
    political_stance TEXT,
    is_fake_news BOOLEAN,
    importance_score INTEGER
)
"""


def ensure_schema(conn) -> None:
    conn.execute(CREATE_ARTICLES_TABLE)


def insert_article(
    conn,
    title: str,
    url: str,
    source: str,
    published: str,
    description: str,
    summary: str = "",
    bullet_points: str = "[]",
    market_implications: str = "[]",
    political_stance: str = "neutral",
    is_fake_news: bool = False,
    importance_score: int = DEFAULT_IMPORTANCE_SCORE,
) -> None:
    """Insert one article. Caller should use a transaction."""
    conn.execute(
        """
        INSERT INTO articles (
            title, url, source, published, description,
            summary, bullet_points, market_implications,
            political_stance, is_fake_news, importance_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            url,
            source,
            published,
            description,
            summary,
            bullet_points,
            market_implications,
            political_stance,
            is_fake_news,
            importance_score,
        ),
    )


def url_exists(conn, url: str) -> bool:
    cur = conn.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
    return cur.fetchone() is not None


def run_pipeline(
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    db_path: Path | str | None = None,
) -> int:
    """
    Fetch articles from news_fetcher, persist to SQLite. Returns number of new rows inserted.
    Enrichment fields (summary, bullet_points, market_implications, importance_score) use
    defaults; replace with an LLM or rules engine later if needed.
    """
    articles = fetch_news(config_path)
    if not articles:
        logger.info("No articles fetched.")
        return 0

    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    inserted = 0

    with get_connection(path) as conn:
        ensure_schema(conn)
        for article in articles:
            url = article.get("url") or ""
            if not url or url_exists(conn, url):
                continue
            insert_article(
                conn,
                title=article.get("title") or "",
                url=url,
                source=article.get("source") or "",
                published=article.get("published") or "",
                description=article.get("description") or "",
                summary=article.get("description") or "",
                bullet_points=json.dumps([]),
                market_implications=json.dumps([]),
                political_stance="neutral",
                is_fake_news=False,
                importance_score=DEFAULT_IMPORTANCE_SCORE,
            )
            inserted += 1
        conn.commit()

    logger.info("Pipeline done. Inserted %d new article(s).", inserted)
    return inserted


def main() -> None:
    run_pipeline(DEFAULT_CONFIG_PATH, DEFAULT_DB_PATH)


if __name__ == "__main__":
    main()
