# System Architecture

## Technology Stack

- **Backend:** Flask (Python)
- **Database:** PostgreSQL (Production), SQLite (Development)
- **Frontend:** Jinja2 templates, Bootstrap 5.3, htmx
- **Containerization:** Docker, Docker Compose
- **Hosting:** Heroku

## Directory Structure

```
.
├── app.py                 # Main application (routes, models, config)
├── templates/             # Jinja2 templates
│   ├── base.html          # Base layout
│   ├── index.html         # Dashboard
│   └── ...
├── static/
│   ├── css/               # Custom styles
│   └── js/                # JavaScript files
├── tests/
│   ├── unit/              # Flask test client tests
│   └── browser/           # Playwright E2E tests
├── migrations/            # Alembic database migrations
└── docs/                  # Documentation
```

## Database Schema

The application uses SQLAlchemy ORM with the following core models:

### User
- `id`: Primary Key
- `email`: Unique identifier (used for login)
- `name`: Display name

### Item
- `id`: Primary Key
- `user_id`: Foreign Key to User (Web owner)
- `name`: Name of the item
- `description`: Optional details
- `link`: URL to purchase
- `price`: Estimated price
- `status`: Current status (e.g., 'available', 'claimed')
- `priority`: Priority level

## Key Concepts

### Monolithic Architecture
The entire application logic resides in a single `app.py` file without separate blueprints. This simplifies the structure for a project of this size.

### Surprise Protection
A core feature of the app is "Surprise Protection". It ensures that:
- Users **cannot** see the claim status of items on their own wishlist.
- Users **can** see who claimed items on other people's wishlists.
This logic is enforced in the Jinja2 templates and view functions.

### Session-Based Filtering
Filters on the items list (e.g., by user, status, priority) are stored in the user's session. This allows the filter state to persist across page navigations.
