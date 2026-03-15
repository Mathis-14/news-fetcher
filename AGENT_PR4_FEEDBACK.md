# Feedback for the agent: PR #4 (feat/refine-for-agent-clean)

---

## Message to the agent

The changes you shipped in **PR #4** (files `alerts.py`, `browse_news.py`, `pipeline.py`) were reviewed. They did not match the project’s standards or the existing design, so they have been refactored. Here is what was wrong and what you should do next.

### 1. What was not useful / what was wrong

- **The pipeline did not use the real news fetcher.**  
  `pipeline.py` defined its own mock `fetch_news()` that returned two hardcoded articles. The project already has a `news_fetcher` package that fetches from RSS and Google News. Your pipeline never called it, so it was a separate, non-integrated demo instead of part of the real flow.

- **Security: use of `eval()`.**  
  In `browse_news.py` you used `eval(bullet_points)` and `eval(market_implications)` to parse JSON-like strings. `eval()` runs arbitrary code and is unsafe on any data that could ever be untrusted (e.g. from DB or API). The correct way to parse JSON from the DB is `json.loads()`.

- **No link to the rest of the codebase.**  
  The app normally writes to `output/news.json` and does not use SQLite. You introduced a second pipeline (SQLite + new scripts) without reusing `news_fetcher.fetch_news()` or documenting how it fits with the existing JSON-based flow. That made the new scripts look like a throwaway prototype.

- **Best practices were not followed.**  
  - No type hints.  
  - Magic numbers (8, 7, 5, 6, 5) instead of named constants.  
  - `print()` instead of `logging`.  
  - DB connections not used as context managers (`with`), so connections could leak on errors.  
  - Duplicate DB path and connection logic in every file instead of a shared helper.  
  - In `browse_news.py`, tuple unpacking by position assumed a fixed column order instead of using `sqlite3.Row` for named access.

- **Hardcoded, non-extensible logic.**  
  In `pipeline.py`, summaries and importance scores were driven by substring checks (`'Meta' in title`, `'Apple' in title`) and fixed source lists. That does not scale and is not maintainable; it was replaced with defaults and a single integration point with the real fetcher.

### 2. What was changed (refactor)

- **`news_db.py` (new)**  
  Shared module for the DB path, importance thresholds, and a `get_connection()` helper so all scripts use the same DB and constants.

- **`pipeline.py`**  
  - Uses **`news_fetcher.fetch_news(config_path)`** for real RSS/Google News data.  
  - Type hints, logging, and named constants.  
  - Connections used with `with get_connection(...)`.  
  - Schema creation and insert logic kept; enrichment fields (summary, bullet_points, market_implications, importance_score) use defaults until you add an LLM or rules engine.

- **`browse_news.py`**  
  - **`eval()` replaced by `json.loads()`** inside a small `_parse_json_field()` helper that safely returns a list.  
  - Uses `sqlite3.Row` and column names instead of positional unpacking.  
  - Constants and limits from `news_db`; logging; `with get_connection(...)`.

- **`alerts.py`**  
  - Uses shared constants and `get_connection()`; `with` for the connection; `sqlite3.Row`; logging instead of `print()`.

### 3. What you should do next

1. **Pull the latest `main`** so you have the refactored code.
2. **Review the diff** for `alerts.py`, `browse_news.py`, `pipeline.py`, and the new `news_db.py`.
3. **Use this as a reference** for future changes in this repo:  
   - Reuse existing packages (`news_fetcher`) instead of reimplementing or mocking.  
   - No `eval()`; use `json.loads()` for JSON from DB or API.  
   - Type hints, logging, named constants, and context managers for resources.  
   - One place for shared config (e.g. DB path, thresholds) and one helper for DB access.

Please confirm once you have pulled and reviewed the code.
