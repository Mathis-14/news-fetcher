# Security

## What this project does

- Reads `config.yaml` (sources and keywords). No secrets are required for the default setup (RSS + Google News RSS).
- Writes `output/news.json` and `.seen_urls` in the project directory.
- All network requests use public feeds; no authentication is used by default.

## Keeping the project secure

1. **Do not commit secrets**
   - If you add API keys or tokens later, put them in a `.env` file (or environment variables) and **do not commit** `.env`. It is listed in `.gitignore`.
   - Do not add passwords or keys to `config.yaml` if you share or publish the repo.

2. **Ignored files**
   - `.venv/`, `output/`, `.seen_urls`, and `.env` are ignored so local state and secrets stay off version control.

3. **Config and dependencies**
   - Only `config.yaml` is read from disk; use `--config` to point to a specific file. The app does not execute code from config (YAML is loaded with `safe_load`). Config structure is validated (e.g. `sources` must be a list of dicts).
   - Dependencies are managed with `uv`; run `uv sync` only from this project and review `pyproject.toml` before adding new packages. To check for known vulnerabilities, run `uv pip install pip-audit && uv run pip-audit` (or use your preferred vulnerability scanner).

## URL verification (audit)

Only **verified** URLs can enter or be stored anywhere in the project:

- **Allowed schemes:** `https` (required for feed URLs in config), `https` and `http` for article URLs. All other schemes (`file:`, `javascript:`, `data:`, etc.) are rejected.
- **Blocked hosts:** localhost, `.local`, private IP ranges, loopback, link-local, and reserved addresses. This prevents SSRF and accidental use of internal URLs.
- **Where it is applied:**
  - **Config:** Feed URLs in `sources[].url` must be safe and HTTPS; invalid entries are skipped and a warning is printed.
  - **Fetcher:** Only safe feed URLs are requested. Article URLs coming from RSS are validated before being added to results; invalid ones are dropped.
  - **Output:** Only articles with safe URLs are written to `output/news.json`. When appending, existing entries are re-checked so no unsafe URL is ever written.
  - **`.seen_urls`:** Only safe URLs are read (invalid lines are ignored) and only safe URLs are written.

Implementation: `src/news_fetcher/url_safety.py` (`is_safe_feed_url`, `is_safe_article_url`). No malicious or internal URL can be stored in config, output, or `.seen_urls`.

## Code and security practices (verified)

- **Config:** YAML loaded with `safe_load` only; `keywords` and `sources` type-checked; only dict entries in `sources` are used; invalid feed URLs are skipped with a warning.
- **Network:** Only HTTPS feed URLs are requested; after redirects the final URL is re-checked (no SSRF via redirect). Timeouts (15s) and per-feed try/except prevent one bad source from failing the whole run.
- **Files:** All file I/O uses explicit `encoding="utf-8"`. Config read, output write, and `.seen_urls` read/write handle `OSError`; failures exit with a clear message or are skipped without crashing.
- **Exceptions:** URL parsing catches only `ValueError`, `TypeError`, `AttributeError`; no bare `except`.
- **Imports:** `argparse` and other stdlib at top level; no dynamic code execution from config or URLs.

## Reporting issues

If you find a security concern, please report it privately (e.g. via a private issue or direct contact) rather than in a public issue.
