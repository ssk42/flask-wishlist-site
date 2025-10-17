# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

## Architecture Overview

### Application Structure
This is a **monolithic Flask application** where all code lives in a single `app.py` file:
- All routes, database models, and configuration are in [app.py](app.py)
- No separate blueprints or modules
- Templates are in `templates/` directory
- Database migrations managed by Flask-Migrate in `migrations/` directory

### Database Models
- **User**: Simple model with name and email (no password - uses email-based login only)
- **Item**: Wishlist items with relationships to User:
  - `user_id`: The owner of the wishlist item
  - `last_updated_by_id`: Tracks who last updated the item (important for claim/purchase tracking)

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
- Email-based authentication only (no passwords)
- Uses Flask-Login for session management
- Login manager configured at [app.py:476-483](app.py#L476)

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

### Deployment (Heroku)
- `Procfile` defines web process (gunicorn) and release process (database migrations)
- Automatic migrations run on every Heroku deployment
- Environment variables: `DATABASE_URL`, `SECRET_KEY`
- CI/CD via GitHub Actions (`.github/workflows/tests.yml`) - tests must pass before merge
