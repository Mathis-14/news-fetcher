"""CLI entry point for news-fetcher."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .fetcher import Article, fetch_sources
from .filter import dedupe_by_url, filter_already_seen, filter_by_keywords
from .url_safety import is_safe_article_url, is_safe_feed_url

# Default paths (relative to cwd)
DEFAULT_CONFIG_NAME = "config.yaml"
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_OUTPUT_FILE = "news.json"
DEFAULT_SEEN_FILE = ".seen_urls"

console = Console()


def load_config(config_path: Path) -> dict:
    """
    Load and validate config from a YAML file.
    Returns dict with keys: keywords (list), sources (list of dicts).
    """
    if not config_path.exists():
        console.print(f"[red]Config not found: {config_path}[/red]")
        sys.exit(1)

    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except OSError as e:
        console.print(f"[red]Cannot read config {config_path}: {e}[/red]")
        sys.exit(1)

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


def _filter_safe_sources(raw_sources: list[dict]) -> list[dict]:
    """
    Keep only sources with valid config and safe feed URLs.
    Google News entries are kept as-is; RSS entries require HTTPS URL.
    """
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
        else:
            name = src.get("name", "?")
            console.print(f"[yellow]Skipping source (invalid or non-HTTPS URL): {name}[/yellow]")
    return safe


def _read_existing_articles(path: Path) -> list[dict]:
    """Load existing articles from JSON file. Returns only items with safe URLs."""
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [
        item for item in data
        if is_safe_article_url((item.get("url") or "").strip())
    ]


def _dedupe_articles_by_url(articles: list[dict]) -> list[dict]:
    """Keep first occurrence of each URL."""
    seen: set[str] = set()
    out: list[dict] = []
    for item in articles:
        url = (item.get("url") or "").strip()
        if url and is_safe_article_url(url) and url not in seen:
            seen.add(url)
            out.append(item)
    return out


def _write_output(
    path: Path,
    articles: list[dict],
    *,
    overwrite: bool,
) -> int:
    """
    Write articles to JSON file.
    If overwrite: write only the given articles.
    Else: merge with existing file, dedupe by URL, then write.
    Returns total number of articles written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if overwrite:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(articles, f, indent=2, ensure_ascii=False)
        except OSError as e:
            console.print(f"[red]Cannot write output file {path}: {e}[/red]")
            sys.exit(1)
        return len(articles)

    existing = _read_existing_articles(path)
    combined = existing + articles
    unique = _dedupe_articles_by_url(combined)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(unique, f, indent=2, ensure_ascii=False)
    except OSError as e:
        console.print(f"[red]Cannot write output file {path}: {e}[/red]")
        sys.exit(1)
    return len(unique)


def _build_parser(cwd: Path) -> argparse.ArgumentParser:
    """Build CLI argument parser with default paths from cwd."""
    default_config = cwd / DEFAULT_CONFIG_NAME
    default_output = cwd / DEFAULT_OUTPUT_DIR / DEFAULT_OUTPUT_FILE
    parser = argparse.ArgumentParser(
        description="Zero-cost news fetcher for RSS and Google News",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config,
        help="Path to config YAML",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Overwrite output and ignore .seen_urls",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help="Output JSON file path",
    )
    return parser


def main() -> None:
    """Run the news fetcher: load config, fetch, filter, write output."""
    cwd = Path.cwd()
    parser = _build_parser(cwd)
    args = parser.parse_args()

    config_path = args.config.resolve()
    output_file = args.output.resolve()
    output_dir = output_file.parent
    seen_path = cwd / DEFAULT_SEEN_FILE

    config = load_config(config_path)
    keywords = config["keywords"]
    sources = _filter_safe_sources(config["sources"])

    if not sources:
        console.print(
            "[yellow]No sources in config. Add entries under 'sources' in config.yaml.[/yellow]",
        )
        sys.exit(0)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching sources…", total=None)
        articles = fetch_sources(sources)
        progress.update(task, description=f"Fetched {len(articles)} raw entries")

    articles = dedupe_by_url(articles)
    articles = filter_by_keywords(articles, keywords)
    if not args.fresh:
        articles = filter_already_seen(articles, seen_path, update_seen=True)

    payload = [a.to_dict() for a in articles]

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        console.print(f"[red]Cannot create output directory {output_dir}: {e}[/red]")
        sys.exit(1)

    total_written = _write_output(
        output_file,
        payload,
        overwrite=args.fresh,
    )

    console.print(
        f"[green]Wrote {len(payload)} new article(s) to {output_file}[/green] "
        f"(total in file: {total_written})",
    )


if __name__ == "__main__":
    main()
