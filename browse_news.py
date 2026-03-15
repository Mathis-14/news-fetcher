#!/usr/bin/env python3
"""Generate a markdown report of today's news from the news SQLite DB."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from news_db import (
    DEFAULT_DB_PATH,
    HIGH_IMPORTANCE_MIN,
    NOTABLE_SCORE_MAX,
    NOTABLE_SCORE_MIN,
    TOP_N_HIGH,
    TOP_N_NOTABLE,
    get_connection,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _parse_json_field(value: str | None) -> list[str]:
    """Safely parse a JSON array from DB. Returns empty list on invalid or null."""
    if not value or not value.strip():
        return []
    try:
        parsed = json.loads(value)
        return list(parsed) if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def run_browse(db_path: Path | str | None = None) -> str:
    """Build and return today's news report as markdown."""
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")

    with get_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT title, url, source, importance_score, summary, bullet_points, market_implications
            FROM articles
            WHERE date(published) = date('now')
            AND importance_score >= ?
            ORDER BY importance_score DESC
            LIMIT ?
            """,
            (HIGH_IMPORTANCE_MIN, TOP_N_HIGH),
        )
        high_rows = cur.fetchall()

        cur = conn.execute(
            """
            SELECT title, url, source, importance_score
            FROM articles
            WHERE date(published) = date('now')
            AND importance_score BETWEEN ? AND ?
            ORDER BY importance_score DESC
            LIMIT ?
            """,
            (NOTABLE_SCORE_MIN, NOTABLE_SCORE_MAX, TOP_N_NOTABLE),
        )
        notable_rows = cur.fetchall()

    report = f"### Today's Top News ({today})\n\n"

    if high_rows:
        report += "#### High Importance (Score ≥ 7)\n"
        for idx, row in enumerate(high_rows, 1):
            bullets = _parse_json_field(row["bullet_points"])
            implications = _parse_json_field(row["market_implications"])
            report += f"{idx}. **{row['title']}** ({row['source']}, Score: {row['importance_score']})\n"
            report += f"   - *Summary*: {row['summary'] or '—'}\n"
            if implications:
                report += f"   - *Market Impact*: {', '.join(implications)}\n"
            report += f"   - [Read more]({row['url']})\n\n"
    else:
        report += "No high-importance news today.\n"

    if notable_rows:
        report += "\n#### Other Notable News\n"
        for row in notable_rows:
            report += f"- **{row['title']}** ({row['source']}, Score: {row['importance_score']}): [Read more]({row['url']})\n"

    return report


def main() -> None:
    report = run_browse(DEFAULT_DB_PATH)
    print(report)


if __name__ == "__main__":
    main()
