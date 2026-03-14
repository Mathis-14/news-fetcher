# news-fetcher

> Zero-cost CLI that fetches news from RSS and Google News, filters by keywords, and writes article metadata to JSON for downstream agents (summarization, research).

No API keys required — uses public RSS and Google News RSS only.

---

## Table of contents

- [Quick start](#quick-start)
- [Requirements](#requirements)
- [Install](#install)
- [Usage](#usage)
- [Config](#config)
- [Output](#output)
- [Scheduling](#scheduling)
- [Security](#security)
- [License](#license)

---

## Quick start

```bash
uv sync
uv run news-fetcher
```

Output: `output/news.json` (article list). Edit `config.yaml` to change sources and keywords.

---

## Requirements

- **Python** 3.12+
- **uv** ([install](https://docs.astral.sh/uv/)) — recommended; or pip

---

## Install

```bash
git clone <repo-url>
cd news-fetcher
uv sync
```

---

## Usage

| Command | Description |
|--------|-------------|
| `uv run news-fetcher` | Run with default `config.yaml` (append to existing output). |
| `uv run news-fetcher --fresh` | Overwrite output and ignore `.seen_urls` history. |
| `uv run news-fetcher --config <path> --output <path>` | Use custom config and output file. |

---

## Config

Edit `config.yaml` in the project root (or pass `--config` to another file).

| Key | Description |
|-----|-------------|
| `keywords` | List of strings. Only articles matching at least one (in title/description) are kept. Empty = no filter. |
| `sources` | List of sources: RSS feeds or Google News searches. |

### RSS source

```yaml
- name: "TechCrunch"
  url: "https://techcrunch.com/feed/"
```

Feed URLs must be **HTTPS**. Invalid or non-HTTPS URLs are skipped.

### Google News source

```yaml
- name: "Google News — AI"
  type: google_news
  query: "artificial intelligence"
```

Article URLs from feeds are validated; only safe URLs (no `file:`, no private IPs) are stored. See [SECURITY.md](SECURITY.md).

---

## Output

| File | Description |
|------|-------------|
| `output/news.json` | List of articles: `title`, `url`, `source`, `published`, `description`. New runs **append** by default. |
| `.seen_urls` | One URL per line; used to avoid re-adding the same articles. Ignored with `--fresh`. |

---

## Scheduling

Example: run every 30 minutes with cron.

```bash
*/30 * * * * cd /path/to/news-fetcher && uv run news-fetcher
```

---

## Security

Only verified URLs (HTTPS for feeds, no localhost/private IPs) are fetched or stored.

See [SECURITY.md](SECURITY.md) for details and how to report issues.

---

## License

See the repository license file.
