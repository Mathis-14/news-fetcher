#!/usr/bin/env python3
"""Print high-importance article alerts from the news SQLite DB."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from news_db import ALERT_IMPORTANCE_MIN, DEFAULT_DB_PATH, get_connection

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_alerts(db_path: Path | str | None = None) -> None:
    """Query today's high-importance articles and log alerts."""
    with get_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT title, url, source, importance_score
            FROM articles
            WHERE date(published) = date('now')
            AND importance_score >= ?
            ORDER BY importance_score DESC
            """,
            (ALERT_IMPORTANCE_MIN,),
        )
        rows = cur.fetchall()

    if rows:
        for row in rows:
            logger.info(
                "🚨 ALERT: %s (Score: %s) - %s",
                row["title"],
                row["importance_score"],
                row["url"],
            )
    else:
        logger.info("No high-importance alerts today.")


def main() -> None:
    run_alerts(DEFAULT_DB_PATH)


if __name__ == "__main__":
    main()
