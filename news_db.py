"""Shared SQLite DB path and connection helper for the pipeline scripts."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to SQLite DB (relative to cwd when scripts run)
DEFAULT_DB_PATH: Path = Path("news.db")

# Importance score thresholds
ALERT_IMPORTANCE_MIN = 8
HIGH_IMPORTANCE_MIN = 7
NOTABLE_SCORE_MIN = 5
NOTABLE_SCORE_MAX = 6
TOP_N_HIGH = 5
TOP_N_NOTABLE = 5

# Default importance when no enrichment is available
DEFAULT_IMPORTANCE_SCORE = 5


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Return a connection to the news DB. Caller must close or use as context manager."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    return sqlite3.connect(path)
