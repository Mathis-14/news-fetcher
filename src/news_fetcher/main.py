"""CLI entry point for news-fetcher."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .api import fetch_news
from .config_loader import load_config
from .fetcher import Article, fetch_sources
from .filter import (
    dedupe_by_url,
    filter_already_seen,
    filter_already_seen_dicts,
    filter_by_keywords,
)
from .url_safety import is_safe_article_url, is_safe_feed_url

# Default paths (relative to cwd)
DEFAULT_CONFIG_NAME = "config.yaml"
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_OUTPUT_FILE = "news.json"
DEFAULT_SEEN_FILE = ".seen_urls"

console = Console()


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
    Raises OSError on write failure.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if overwrite:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        return len(articles)

    existing = _read_existing_articles(path)
    combined = existing + articles
    unique = _dedupe_articles_by_url(combined)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    return len(unique)


def _build_parser(cwd: Path) -> argparse.ArgumentParser:
    """Build CLI argument parser. Default output is relative to config file dir."""
    default_config = cwd / DEFAULT_CONFIG_NAME
    default_output = default_config.parent / DEFAULT_OUTPUT_DIR / DEFAULT_OUTPUT_FILE
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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print articles as JSON to stdout (no file write, no Rich output)",
    )
    return parser


def main() -> None:
    """Run the news fetcher: load config, fetch, filter, write output or print JSON."""
    cwd = Path.cwd()
    parser = _build_parser(cwd)
    args = parser.parse_args()

    config_path = args.config.resolve()
    output_file = args.output.resolve()
    output_dir = output_file.parent
    # Seen path next to config so it works when run from any cwd
    seen_path = config_path.parent / DEFAULT_SEEN_FILE

    try:
        config = load_config(config_path)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    except OSError as e:
        console.print(f"[red]Cannot read config {config_path}: {e}[/red]")
        sys.exit(1)

    sources = _filter_safe_sources(config["sources"])
    if not sources:
        console.print(
            "[yellow]No sources in config. Add entries under 'sources' in config.yaml.[/yellow]",
        )
        sys.exit(0)

    if args.json:
        try:
            payload = fetch_news(config_path)
            if not args.fresh:
                payload = filter_already_seen_dicts(
                    payload, seen_path, update_seen=True
                )
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        except (FileNotFoundError, OSError) as e:
            console.print(f"[red]{e}[/red]")
            sys.exit(1)
        return

    keywords = config["keywords"]
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
        total_written = _write_output(
            output_file,
            payload,
            overwrite=args.fresh,
        )
    except OSError as e:
        console.print(f"[red]Cannot write output: {e}[/red]")
        sys.exit(1)

    console.print(
        f"[green]Wrote {len(payload)} new article(s) to {output_file}[/green] "
        f"(total in file: {total_written})",
    )


if __name__ == "__main__":
    main()
