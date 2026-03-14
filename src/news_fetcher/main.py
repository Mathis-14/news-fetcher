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

console = Console()


def load_config(config_path: Path) -> dict:
    """Load config.yaml. Keys: keywords (list), sources (list of dicts). Validates structure."""
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
    # Ensure each source is a dict (avoid iterating over string keys etc.)
    sources = [s for s in sources if isinstance(s, dict)]
    return {"keywords": keywords, "sources": sources}


def main() -> None:
    """Run the news fetcher: load config, fetch, filter, write output."""
    # Paths relative to cwd
    cwd = Path.cwd()
    config_path = cwd / "config.yaml"
    output_dir = cwd / "output"
    output_file = output_dir / "news.json"
    seen_path = cwd / ".seen_urls"

    parser = argparse.ArgumentParser(description="Zero-cost news fetcher for RSS and Google News")
    parser.add_argument(
        "--config",
        type=Path,
        default=config_path,
        help="Path to config.yaml",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Overwrite output and ignore .seen_urls (no append, no dedupe by history)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=output_file,
        help="Output JSON file path",
    )
    args = parser.parse_args()

    config_path = args.config.resolve()
    output_file = args.output.resolve()
    output_dir = output_file.parent

    config = load_config(config_path)
    raw_sources = config["sources"]
    keywords = config["keywords"]

    # Only pass verified feed URLs (and google_news entries) to the fetcher.
    sources = []
    for src in raw_sources:
        if src.get("type") == "google_news":
            sources.append(src)
            continue
        feed_url = src.get("url")
        if not feed_url:
            continue
        url_str = str(feed_url).strip()
        if is_safe_feed_url(url_str):
            sources.append(src)
        else:
            console.print(f"[yellow]Skipping source (invalid or non-HTTPS URL): {src.get('name', '?')}[/yellow]")

    if not sources:
        console.print("[yellow]No sources in config. Add entries under 'sources' in config.yaml.[/yellow]")
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
    total_in_file = len(payload)
    if args.fresh:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except OSError as e:
            console.print(f"[red]Cannot write output file {output_file}: {e}[/red]")
            sys.exit(1)
    else:
        existing: list = []
        if output_file.exists():
            try:
                with open(output_file, encoding="utf-8") as f:
                    existing = json.load(f)
                if not isinstance(existing, list):
                    existing = []
            except (json.JSONDecodeError, OSError):
                existing = []
        # Only keep existing items with verified URLs (defense in depth).
        existing = [item for item in existing if is_safe_article_url((item.get("url") or "").strip())]
        combined = existing + payload
        seen_urls: set[str] = set()
        unique: list[dict] = []
        for item in combined:
            url = (item.get("url") or "").strip()
            if url and is_safe_article_url(url) and url not in seen_urls:
                seen_urls.add(url)
                unique.append(item)
        total_in_file = len(unique)
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(unique, f, indent=2, ensure_ascii=False)
        except OSError as e:
            console.print(f"[red]Cannot write output file {output_file}: {e}[/red]")
            sys.exit(1)

    console.print(f"[green]Wrote {len(payload)} new article(s) to {output_file}[/green] (total in file: {total_in_file})")


if __name__ == "__main__":
    main()
