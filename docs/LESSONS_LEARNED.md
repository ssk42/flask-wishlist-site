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

### 4. Test Isolation vs Caching
- **Issue:** Using `SimpleCache` (in-memory) with a global `Cache` extension object can lead to state bleeding between tests if the cache isn't explicitly cleared.
- **Symptom:** Tests failing with "AssertionError" because the view returns cached content from a previous test's user session.
- **Solution:** Add `cache.clear()` to the `autouse` database cleanup fixture in `conftest.py`.

### 5. Local vs Docker Database Conflicts
- **Issue:** `FATAL: role "user" does not exist` when connecting to `localhost:5432` might mean you are connecting to a local system Postgres instead of the Docker container, especially on macOS where port 5432 might be taken.
- **Solution:** Map the Docker container to a non-standard port (e.g., `5433:5432`) in `docker-compose.yml` and update connection strings to match.

### 6. Pytest Teardown Errors (SQLAlchemy 1.4/2.0)
- **Issue:** Tests pass (Green), but CI fails with `ExceptionGroup` during session teardown, citing "2 sub-exceptions".
- **Cause:** Unclosed SQLAlchemy database connections or engines at the end of the test session. Pytest's error reporting for session-scoped fixtures can be brittle.
- **Solution:**
  1. Add a `pytest_sessionfinish` hook in `conftest.py` to explicitly remove sessions and dispose engines (`db.engine.dispose()`).
  2. Update CI workflow to parse JUnit XML results (`pytest --junitxml=results.xml`) and check for actual *failures* (`failures="0"`) rather than relying solely on the exit code, which might be 1 due to teardown noise.

## 📱 PWA (Progressive Web App)

### 1. Verification
- **Learning:** You don't need a mobile device to test PWA basics. A browser test checking for `manifest.json` returning 200 OK and valid JSON is a strong verification step.
- **Favicons:** Browsers look for `favicon.ico` or `<link rel="icon">`. PWA manifests define the *home screen* icon, but the browser tab icon must still be defined in HTML for desktop consistency.

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

## 🔄 CI/CD & Dependabot

### 1. Dependabot Grouped Updates
- **Strategy:** Configure `groups` in `dependabot.yml` (e.g., `python-minor`) to bundle updates. This reduces PR noise significantly (one PR for 25+ updates instead of 25 PRs).
- **Auto-merge:** GitHub Actions auto-merge requires specific repository settings. If not enabled, manual merge is needed, which can cause conflicts with other open PRs.

---

## 🏗️ Architecture Patterns

### 1. Surprise Protection Pattern (Critical!)
- **What it is:** The core principle that gift recipients should NEVER see who claimed/purchased their items.
- **Where it applies:**
  - Item status display: Owners see their items as "Available" even when claimed/purchased
  - Summary stats: Owners' claimed/purchased counts excluded from totals
  - Comments: Hidden from item owner (shown as "Hidden from owner" to others)
  - `last_updated_by` field: Never exposed to item owner
- **Implementation locations:**
  - `blueprints/items.py` (lines ~125-133) - Summary totals calculation
  - `templates/partials/_item_card.html` - Conditional display logic
- **When extending:** Any new feature involving item status MUST consider surprise protection. If adding a new status (e.g., "Splitting"), ensure owners see it as "Available".

### 2. Claim System Architecture
- **Current model:** Single-claim system where one user claims an item
- **Key fields:**
  - `Item.status`: "Available", "Claimed", "Purchased"
  - `Item.last_updated_by_id`: Tracks who claimed/purchased (FK to User)
- **Constraints:**
  - Users cannot claim their own items
  - Only the claimer can unclaim
  - Only the claimer can change status to "Purchased"
- **HTMX integration:** Claim/unclaim actions return partial HTML for seamless updates
- **When extending:** The Split Gifts PRD introduces a new "Splitting" status with a `Contribution` model for multiple contributors. This maintains backward compatibility with single claims.

### 3. Unused `is_private` Field
- **Location:** `User.is_private` (Boolean, default=False) in `models.py`
- **Status:** Field exists in database but NO code reads it
- **Purpose:** Placeholder for future privacy controls (see PRD_WISHLIST_SHARING.md)
- **When to use:** The Wishlist Sharing feature will activate this field to hide wishlists from family members
- **Do not:** Add logic that reads this field until implementing the full privacy feature

### 4. Blueprint Organization
- **Structure:** 6 blueprints in `blueprints/` directory
  - `auth.py` - All authentication routes (login, register, logout, forgot_email)
  - `items.py` - Item CRUD, claiming, filtering (the largest blueprint)
  - `events.py` - Event CRUD for gift occasions
  - `dashboard.py` - Home page, welcome screen
  - `social.py` - Comments, notifications
  - `api.py` - JSON endpoints (currently just metadata fetching)
- **URL prefixes:** Blueprints use their name as prefix (e.g., `/items/`, `/events/`)
- **Template references:** Always use `blueprint.route_name` format: `url_for('items.items_list')`
- **When adding routes:** Place in appropriate blueprint. If creating a new domain, consider a new blueprint.

### 5. Filter Persistence Pattern
- **What it does:** Maintains user's filter selections (user, status, priority, etc.) across navigation
- **Storage:** Flask session (`session['items_filters']`)
- **Helper function:** `get_items_url_with_filters()` in `blueprints/items.py`
- **Clear mechanism:** `?clear_filters=true` query parameter
- **When extending:** Any new filter option should be added to the session storage pattern

### 6. Two-Layer Task System
- **Sync layer:** `services/tasks.py` - Functions callable directly (used by Flask CLI)
- **Async layer:** `services/celery_tasks.py` - Celery wrappers that call sync functions
- **Why both:** CLI commands work without Redis/Celery (good for Heroku Scheduler). Celery provides async when worker is running.
- **When adding tasks:** Write sync version first in `tasks.py`, then add Celery wrapper in `celery_tasks.py`
