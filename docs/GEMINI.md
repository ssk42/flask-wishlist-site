# Project Overview

This is a Flask-based web application for managing a family wishlist. Users can register, log in, and manage their wishlist items. The application uses a PostgreSQL database for data storage and is set up to be run in a Docker container.

**Key Technologies:**

*   **Backend:** Flask (Python)
*   **Database:** PostgreSQL (with SQLAlchemy ORM and Alembic for migrations)
*   **Frontend:** Jinja2 templates with Bootstrap CSS
*   **Testing:** pytest, Playwright for browser tests
*   **Containerization:** Docker, Docker Compose

# Building and Running

The project uses Docker Compose to manage the application and its services.

**Common Commands:**

*   **Build the Docker images:**
    ```bash
    make build
    ```
*   **Start the application (in detached mode):**
    ```bash
    make up
    ```
    The application will be available at `http://localhost:5000`.
*   **Stop the application:**
    ```bash
    make down
    ```
*   **View logs:**
    ```bash
    make logs
    ```
*   **Run tests:**
    ```bash
    make test
    ```
*   **Run database migrations:**
    ```bash
    make migrate
    ```

For a full list of commands, see the `Makefile`.

# Development Conventions

*   **Configuration:** Application configuration is handled in `config.py` and can be overridden with environment variables.
*   **Database Migrations:** Database schema changes are managed with `flask db` commands (via Alembic).
*   **Testing:**
    *   Unit tests are located in `tests/unit`.
    *   Browser tests are in `tests/browser`.
    *   Tests are run with `pytest`.
*   **Dependencies:** Python dependencies are managed in `requirements.txt`.
