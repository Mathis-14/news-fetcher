"""Config loading. Raises on error; no sys.exit or console output."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_config(config_path: str | Path) -> dict:
    """
    Load and validate config from a YAML file.
    Returns dict with keys: keywords (list), sources (list of dicts).
    Raises FileNotFoundError if path does not exist, OSError on read error.
    """
    config_path = Path(config_path).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        return {"keywords": [], "sources": []}

    keywords = data.get("keywords")
    if not isinstance(keywords, list):
        keywords = []

    sources = data.get("sources")
    if not isinstance(sources, list):
        sources = []
    sources = [s for s in sources if isinstance(s, dict)]

    return {"keywords": keywords, "sources": sources}
