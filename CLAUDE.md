# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📚 Key Documentation

| Document | Purpose |
|----------|--------|
| [docs/IMPROVEMENTS.md](docs/IMPROVEMENTS.md) | **Project Roadmap** - Comprehensive tracking of all planned/completed improvements (50 items, ~56% complete). Use this to understand priorities and find your next task. |
| [docs/LESSONS_LEARNED.md](docs/LESSONS_LEARNED.md) | **Technical Gotchas** - Common pitfalls, environment quirks, and solutions discovered during development. Read this before diving into infrastructure or testing work. |

### 📋 Product Requirements Documents (PRDs)

| PRD | Feature | Status |
|-----|---------|--------|
| [docs/PRD_ITEM_VARIANTS.md](docs/PRD_ITEM_VARIANTS.md) | Size, color, quantity fields for items (#25) | Draft |
| [docs/PRD_SPLIT_GIFTS.md](docs/PRD_SPLIT_GIFTS.md) | Multiple contributors for expensive gifts (#32) | Draft |
| [docs/PRD_WISHLIST_SHARING.md](docs/PRD_WISHLIST_SHARING.md) | Privacy controls & external share links (#22, #47, #48) | Draft |
| [docs/PRD_SECRET_SANTA.md](docs/PRD_SECRET_SANTA.md) | Random gift assignments for events (#50) | Draft |
| [docs/PRD_PRICE_CRAWLER.md](docs/PRD_PRICE_CRAWLER.md) | Reliability, history & performance (#35+) | Draft |

## Development Commands

### Initial Setup
```bash
# Activate virtual environment
source venv/bin/activate  # Unix/MacOS
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask db upgrade

# Install Playwright browsers (for browser tests)
playwright install --with-deps chromium
```

### Running the Application
```bash
# Set environment variables (if not already set)
export FLASK_APP=app.py
export FLASK_ENV=development

# Run local development server
flask run
```

### Testing
```bash
# Run all tests (unit + browser regression) with coverage
pytest

# Run only unit tests
pytest tests/unit/

# Run only browser tests
pytest tests/browser/

# Run a single test file
pytest tests/unit/test_routes.py

# Run a specific test
pytest tests/unit/test_routes.py::test_register_creates_user
```

**Important:** Coverage is enforced at 75% or greater. The pytest configuration in `pytest.ini` automatically generates coverage reports.

### Database Migrations
```bash
# Apply migrations
flask db upgrade

# Create a new migration after model changes
flask db migrate -m "Description of changes"
```

## Coding Standards

### 1. DateTime Handling
- **Deprecated:** `datetime.datetime.utcnow()` (Scheduled for removal)
- **Use:** `datetime.datetime.now(datetime.timezone.utc)`
- **Models:** Use lambda for defaults: `default=lambda: datetime.datetime.now(datetime.timezone.utc)`

### 2. SQLAlchemy
- **Deprecated:** `Model.query.get(id)`
- **Use:** `db.session.get(Model, id)`

## Architecture Overview

### Application Structure
This is a **Flask application** using the Application Factory pattern with Blueprints:
- **App factory** in [app.py](app.py) - `create_app()` function, extensions initialization
- **Blueprints** in `blueprints/`:
  - `auth.py` - Login, registration, logout, forgot email
  - `items.py` - Wishlist items CRUD, claiming, filtering
  - `events.py` - Events CRUD for gift occasions
  - `dashboard.py` - Home page, dashboard stats
  - `social.py` - Comments, notifications
  - `api.py` - JSON API endpoints (metadata fetching, price history)
- **Models** in [models.py](models.py) - User, Item, Event, Comment, Notification, PriceHistory, Contribution
- **Services** in `services/`:
  - `price_service.py` - Product price fetching and metadata extraction
  - `email_service.py` - Email sending via Flask-Mail
  - `tasks.py` - Background tasks (event reminders)
  - `celery_tasks.py` - Async Celery wrappers
  - `logging_config.py` - Structured logging setup
- **Templates** in `templates/` directory (partials in `templates/partials/`)
- **Database migrations** managed by Flask-Migrate in `migrations/` directory
- **Documentation** in `docs/` directory

### Template Variants
- `templates/partials/_item_card.html` - Full item card with price, sparkline, actions (used on `/items`)
- `templates/partials/_dashboard_item_card.html` - Compact card for dashboard (used on `/`)
- When adding UI features, consider which template(s) need the component

### Database Models
- **User**: Model with name, email, and `is_private` flag (unused placeholder for future privacy controls)
- **Item**: Wishlist items with relationships to User:
  - `user_id`: The owner of the wishlist item
  - `last_updated_by_id`: Tracks who last updated the item (important for claim/purchase tracking)
- **Event**: Gift occasions (birthdays, holidays) with date and reminder tracking
- **Comment**: Hidden coordination comments between gift-givers (invisible to item owner)
- **Notification**: User alerts for claims, comments, etc.
- **PriceHistory**: Historical prices for items (for sparkline visualization)
- **Contribution**: Split gift contributions from multiple users

### Key Features & Behaviors

#### Session-Based Filter Persistence
The items list view ([app.py:160-322](app.py#L160)) implements filter persistence:
- Filters (user, status, priority, category, search query, sort options) are stored in Flask session
- Filters persist across page navigation (add item, edit item, claim item) via `get_items_url_with_filters()`
- Clear filters with `?clear_filters=true` parameter
- This allows users to maintain their view state when performing actions

#### Surprise Protection
The application prevents gift receivers from seeing who claimed/purchased their items ([app.py:255-263](app.py#L255)):
- When viewing summaries, users cannot see claimed/purchased counts for their own items
- This preserves gift surprises while allowing gift-givers to coordinate
- The protection is implemented in the items summary totals calculation

#### Login System
- **Family Code authentication**: Shared secret code for family access (configured via `FAMILY_CODE` env var)
- Email + Family Code required for login (no individual passwords)
- Uses Flask-Login for session management
- Rate limited: 5 requests/minute on auth endpoints

#### Database Configuration
- Local development: SQLite database stored in `instance/wishlist.sqlite`
- Production (Heroku): PostgreSQL via `DATABASE_URL` environment variable
- Automatic postgres:// to postgresql:// URI conversion for Heroku compatibility

### Testing Architecture
- **Unit tests** (`tests/unit/`): Use Flask test client with temporary SQLite database
- **Browser tests** (`tests/browser/`): Playwright-based end-to-end tests with live test server on port 5001
- **Fixtures** in `tests/conftest.py`:
  - `app`: Session-scoped test app with temporary database
  - `client`: Flask test client
  - `user`, `other_user`: Test user fixtures
  - `login`: Automatically logs in a test user
  - `live_server`: Runs Flask app on localhost:5001 for browser tests
- **Auto-cleanup**: Database is automatically cleaned between tests via `_clean_database` fixture

### Test Coverage
- **Total Tests:** 317 (224 unit + 93 browser)
- **Overall Coverage:** 95.12%
- **Enforced Minimum:** 90%

#### Screen & Component Coverage
| Screen / Blueprint | Coverage | Notes |
|--------------------|----------|-------|
| **Dashboard** | 100% | Home page stats, welcome screen |
| **All Gifts / Items** | 96% | Filtering, CRUD, variants, sparklines |
| **Auth** | 100% | Login, Registration, Forgot Email |
| **Events** | 100% | Event CRUD, item associations |
| **Social** | 100% | Comments, Notifications |
| **API** | 88% | Price history, metadata endpoints |
| **Models** | 92% | core logic and relationships |
| **Email Service** | 100% | Reminders and notifications |
| **Tasks** | 98% | Event reminders and price updates |
| **Utils** | 100% | URL filters and helper functions |

**Performance:** Browser tests use Playwright and hit a live local server. Total suite runtime is ~6 minutes.

### Deployment (Heroku)
- `Procfile` defines web process (gunicorn) and release process (database migrations)
- Automatic migrations run on every Heroku deployment
- Environment variables: `DATABASE_URL`, `SECRET_KEY` (see `.env.example` for template)
- CI/CD via GitHub Actions (`.github/workflows/tests.yml`) - tests must pass before merge

## Current State (2026-01-04)

### Completed Features ✅
- **Blueprint Architecture**: App split into 6 blueprints (auth, items, events, dashboard, social, api)
- **Family Code Auth**: Secure shared authentication for family groups
- **Events Management**: Create gift occasions, associate items with events
- **Price Tracking**: Auto-fetch prices from URLs, refresh buttons
- **My Claims Page**: Track items claimed/purchased for others
- **Comments**: Hidden coordination between gift-givers
- **PWA Support**: Installable app with offline capabilities

### Security ✅
- CSRF protection on all forms
- Security headers configured
- Rate limiting on auth endpoints (Flask-Limiter)
- Surprise protection (owners can't see claim status)

### Infrastructure ✅
- Docker + docker-compose setup
- Redis caching layer
- Celery for async tasks
- Sentry error tracking
- GitHub Actions CI/CD
- Heroku deployment with auto-migrations

### Test Coverage
- 211 tests (151 unit + 60 browser)
- 96% code coverage
- Playwright browser tests
