# 🧠 Lessons Learned & Technical Insights

**Last Updated:** 2026-01-04 (Session 7)

This document is for and by Agents such as Claude and Gemini. It's goal is that this document captures key technical learnings, "gotchas," and architectural decisions encountered during the development of the Family Wishlist App, so that Agents can avoid common pitfalls and make informed decisions.

## 🚀 Deployment & Infrastructure (Heroku)

### 1. `uv.lock` vs `requirements.txt`
- **Issue:** Heroku Python buildpack (heroku/python) can get confused if both `uv.lock` and `requirements.txt` exist, sometimes failing to install dependencies correctly (like `sentry-sdk` or `redis`) even if they are listed.
- **Solution:** For robust Heroku deployments, rely on standard `requirements.txt`. If using `uv` locally, ensure the lock file isn't interfering or is explicitly handled. In our case, removing `uv.lock` and relying on pip/requirements.txt fixed the "ModuleNotFoundError".

### 2. Redis SSL (`rediss://`)
- **Issue:** Heroku Redis (and many cloud providers) mandate SSL/TLS connections (`rediss://`).
- **Gotcha:** `Flask-Limiter` and `Celery` might fail with certificate verification errors because Heroku uses self-signed certificates.
- **Solution:** Connect with `ssl_cert_reqs=None` (or `CERT_NONE`) in the connection URL or client arguments to bypass strict verification for these managed services.

### 3. Slug Size Limits
- **Issue:** Including browser binaries (Playwright) in the application slug increases size significantly (~300MB+).
- **Impact:** Checks might warn about "soft limits" (300MB), but the app still runs.
- **Mitigation:** Only install necessary browser engines (e.g., `playwright install chromium`). Clean up cached files if possible.

## 🧪 Testing

### 1. Database Isolation (`flask run` vs `pytest`)
- **Issue:** The `create_app()` factory can accidentally pick up the **Server** (Production/Dev) configuration when running tests if env vars are present. We had tests connecting to the live AWS database!
- **Solution:** In `conftest.py`, strictly enforce `FLASK_ENV='testing'` and unset `DATABASE_URL` *before* the app is created to ensure the test suite uses its own isolated (SQLAlchemy/SQLite) database.

### 2. Rate Limiting in Tests
- **Issue:** Browser tests hitting `/login` repeatedly trigger `429 Too Many Requests`.
- **Solution:** Disable rate limiting in the `TestingConfig` (`RATELIMIT_ENABLED = False`). Do not test rate limiting logic in the main functional flows; test it separately with specific unit tests if needed.

### 3. Playwright & Port Conflicts
- **Issue:** Hardcoding `port=5001` for the `live_server` fixture causes "Address already in use" if a previous test run didn't exit cleanly or the dev server is running.
- **Solution:** Use `port=0` to let the OS assign a random free ephemeral port for parallel/robust testing.

## 📱 PWA (Progressive Web App)

### 1. Verification
- **Learning:** You don't need a mobile device to test PWA basics. A browser test checking for `manifest.json` returning 200 OK and valid JSON is a strong verification step.
- **Favicons:** Browsers look for `favicon.ico` or `<link rel="icon">`. PWA manifests define the *home screen* icon, but the browser tab icon must still be defined in HTML for desktop consistency.

### 4. Test Isolation vs Caching
- **Issue:** Using `SimpleCache` (in-memory) with a global `Cache` extension object can lead to state bleeding between tests if the cache isn't explicitly cleared.
- **Symptom:** Tests failing with "AssertionError" because the view returns cached content from a previous test's user session.
- **Solution:** Add `cache.clear()` to the `autouse` database cleanup fixture in `conftest.py`.

### 5. Local vs Docker Database Conflicts
- **Issue:** `FATAL: role "user" does not exist` when connecting to `localhost:5432` might mean you are connecting to a local system Postgres instead of the Docker container, especially on macOS where port 5432 might be taken.
- **Solution:** Map the Docker container to a non-standard port (e.g., `5433:5432`) in `docker-compose.yml` and update connection strings to match.

## ⚙️ Background Tasks

### 1. Two Task Implementations Exist
- **Gotcha:** This project has TWO implementations of background tasks:
  - `services/tasks.py` - Synchronous, used by Flask CLI (`flask send-reminders`, `flask update-prices`)
  - `services/celery_tasks.py` - Async Celery wrappers that call the sync versions
- **Why:** The CLI commands work without Redis/Celery (useful for Heroku Scheduler or cron). Celery tasks provide true async execution when the worker is running.
- **Which to use:** For scheduled jobs via Heroku Scheduler, use the CLI. For on-demand async processing, use Celery.

### 2. Flask-Limiter `init_app()` API Changed
- **Issue:** Heroku deploy failed with `TypeError: Limiter.init_app() got an unexpected keyword argument 'storage_options'`.
- **Cause:** Local Flask-Limiter version accepted `storage_options` in `init_app()`, but Heroku's version (different Python/package version) did not.
- **Solution:** Don't pass `storage_options` to `init_app()`. Configure via `RATELIMIT_STORAGE_URI` config key instead (already includes `?ssl_cert_reqs=none` for Heroku Redis).
