#!/usr/bin/env python3
"""Fetch news via news_fetcher, store in SQLite, and optionally enrich for alerts/reports.

Features:
- Input validation for config file.
- Structured logging (timestamps, levels).
- Batch inserts for performance.
- Error handling for network/config issues.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from news_db import DEFAULT_DB_PATH, DEFAULT_IMPORTANCE_SCORE, get_connection
from news_fetcher import fetch_news

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
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


def _validate_config(config_path: Path | str) -> None:
    """Validate the config file exists and is readable."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            pass  # File exists and is readable
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to read config: {e}")
        sys.exit(1)


def _generate_default_summary(title: str) -> str:
    """Generate a default summary for an article."""
    return f"Summary of {title}."


def _generate_default_bullet_points(title: str) -> List[str]:
    """Generate default bullet points for an article."""
    return [f"Key detail about {title}"]


def _generate_default_market_implications(source: str) -> List[str]:
    """Generate default market implications based on source."""
    return []


def _calculate_default_importance_score(source: str) -> int:
    """Calculate default importance score based on source."""
    high_importance_sources = {"Reuters", "Yahoo Finance", "Bloomberg", "BBC"}
    return 7 if source in high_importance_sources else DEFAULT_IMPORTANCE_SCORE


def _enrich_article(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich an article with summary, bullet points, market implications,
    and importance score. Uses defaults until an LLM/rules engine is added.
    """
    return {
        "summary": _generate_default_summary(article.get("title", "")),
        "bullet_points": _generate_default_bullet_points(article.get("title", "")),
        "market_implications": _generate_default_market_implications(article.get("source", "")),
        "importance_score": _calculate_default_importance_score(article.get("source", "")),
    }


def ensure_schema(conn) -> None:
    """Ensure the articles table exists."""
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
    """Check if a URL already exists in the database."""
    cur = conn.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
    return cur.fetchone() is not None


def _batch_insert_articles(conn, articles: List[Dict[str, Any]]) -> None:
    """Insert articles in batch for better performance."""
    enriched_articles = [_enrich_article(article) for article in articles]
    
    conn.executemany(
        """
        INSERT INTO articles (
            title, url, source, published, description,
            summary, bullet_points, market_implications,
            political_stance, is_fake_news, importance_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(
            article.get("title", ""),
            article.get("url", ""),
            article.get("source", ""),
            article.get("published", ""),
            article.get("description", ""),
            enriched["summary"],
            json.dumps(enriched["bullet_points"]),
            json.dumps(enriched["market_implications"]),
            "neutral",
            False,
            enriched["importance_score"],
        ) for article, enriched in zip(articles, enriched_articles)]
    )


def run_pipeline(
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    db_path: Path | str | None = None,
) -> int:
    """
    Fetch articles from news_fetcher, persist to SQLite. Returns number of new rows inserted.
    Enrichment fields (summary, bullet_points, market_implications, importance_score) use
    defaults; replace with an LLM or rules engine later if needed.
    
    Args:
        config_path: Path to the config file (default: "config.yaml").
        db_path: Path to the SQLite database (default: DEFAULT_DB_PATH).
    
    Returns:
        Number of new articles inserted.
    """
    # Validate config
    _validate_config(config_path)
    
    # Fetch articles
    try:
        articles = fetch_news(config_path)
        logger.info(f"Fetched {len(articles)} articles from sources")
    except Exception as e:
        logger.error(f"Failed to fetch news: {e}")
        return 0
    
    if not articles:
        logger.info("No articles fetched.")
        return 0

    # Process articles
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    inserted = 0

    with get_connection(path) as conn:
        ensure_schema(conn)
        
        # Filter out already processed URLs
        existing_urls = {
            row[0] for row in conn.execute("SELECT url FROM articles").fetchall()
        }
        new_articles = [
            article for article in articles 
            if article.get("url") and article["url"] not in existing_urls
        ]
        
        if not new_articles:
            logger.info("No new articles to process")
            return 0
        
        logger.info(f"Processing {len(new_articles)} new articles")
        _batch_insert_articles(conn, new_articles)
        inserted = len(new_articles)
        conn.commit()

    logger.info("Pipeline done. Inserted %d new article(s).", inserted)
    return inserted


def main() -> None:
    """Run the pipeline with default config and DB paths."""
    run_pipeline(DEFAULT_CONFIG_PATH, DEFAULT_DB_PATH)


if __name__ == "__main__":
    main()
