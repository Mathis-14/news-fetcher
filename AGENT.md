# Agent Integration Guide

This file is for you, the agent. It tells you exactly how to use this repo to get news article URLs and metadata.

---

## What this repo does

It fetches news from RSS feeds and Google News, filters by keywords, and returns article metadata (title, URL, source, date, description). Zero cost, no API keys.

---

## Setup (one time)

```bash
git clone <repo-url>
cd news-fetcher
uv sync
```

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

---

## How to use

### Option A: Python import (recommended)

```python
from news_fetcher import fetch_news

articles = fetch_news("config.yaml")
```

`articles` is a `list[dict]`. Each dict has these keys:

| Key           | Type   | Description                              |
|---------------|--------|------------------------------------------|
| `title`       | `str`  | Article headline                         |
| `url`         | `str`  | Direct article URL (not a redirect)      |
| `source`      | `str`  | Source name from config                  |
| `published`   | `str`  | ISO datetime (`YYYY-MM-DDTHH:MM:SS`) or empty |
| `description` | `str`  | Short plain-text summary (max 500 chars) |

**Behavior:**
- No files are written. No `.seen_urls` is updated. No console output.
- Raises `FileNotFoundError` if config path is missing.
- Raises `OSError` on config read errors.
- Google News redirect URLs are resolved to real article URLs when possible.

### Option B: CLI with JSON stdout

```bash
uv run news-fetcher --json
```

Prints the same `list[dict]` as JSON to stdout. No file is written.

Capture in a script:

```bash
articles=$(uv run news-fetcher --json)
```

### Option C: CLI with file output

```bash
uv run news-fetcher
```

Writes to `output/news.json`. Appends by default; use `--fresh` to overwrite.

---

## Config

Edit `config.yaml` (or pass `--config path/to/config.yaml`).

```yaml
keywords:
  - "artificial intelligence"
  - "startup funding"

sources:
  - name: "TechCrunch"
    url: "https://techcrunch.com/feed/"
  - name: "Hacker News"
    url: "https://hnrss.org/frontpage"
  - name: "Google News — AI"
    type: google_news
    query: "artificial intelligence"
```

- **keywords**: only articles matching at least one keyword (in title or description) are returned. Empty list = no filter (all articles returned).
- **sources**: RSS feeds need `name` + `url` (HTTPS only). Google News needs `name` + `type: google_news` + `query`.

---

## Typical agent workflow

```python
from news_fetcher import fetch_news

articles = fetch_news("config.yaml")

urls_to_research = [a["url"] for a in articles]
# Now pass urls_to_research to your browsing/research tool.

# Or get titles + URLs for summarization:
for a in articles:
    print(f"{a['title']} -> {a['url']}")
```

---

## Error handling

```python
try:
    articles = fetch_news("config.yaml")
except FileNotFoundError:
    # config.yaml not found at given path
except OSError as e:
    # config file unreadable
```

---

## Constraints

- Feed URLs in config must be HTTPS.
- Article URLs are validated: no `file:`, `javascript:`, or private/localhost IPs.
- Google News URLs that resolve to consent pages are kept as-is (the original Google redirect URL).
- No authentication or API keys are needed or supported.
