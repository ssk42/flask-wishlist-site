# Development Guide

## Running Locally

To run the application in a local development environment:

```bash
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

The server will start at `http://127.0.0.1:5000`.

## Testing

The project uses `pytest` for testing.

### Running Tests

- **All Tests:**
  ```bash
  pytest
  ```

- **Unit Tests:**
  ```bash
  pytest tests/unit/
  ```

- **Browser Tests:**
  ```bash
  pytest tests/browser/
  ```

### Coverage
The project enforces a code coverage of **75%**. Coverage reports are automatically generated when running tests.

## Database Migrations

We use Flask-Migrate (Alembic) for handling database schema changes.

- **Apply Migrations:**
  ```bash
  flask db upgrade
  ```

- **Create Migration:**
  ```bash
  flask db migrate -m "Description of change"
  ```
