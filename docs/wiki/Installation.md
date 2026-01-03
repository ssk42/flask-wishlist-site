# Installation Guide

## Prerequisites

- [Python 3.8+](https://www.python.org/downloads/)
- [pip](https://pip.pypa.io/en/stable/installation/)
- [Docker](https://www.docker.com/products/docker-desktop) (optional, for containerized run)

## Local Setup

1.  **Clone the repository**
    ```bash
    git clone https://github.com/ssk42/flask-wishlist-site.git
    cd flask-wishlist-site
    ```

2.  **Create and activate virtual environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Unix/macOS
    # or
    .\venv\Scripts\activate   # Windows
    ```

3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize the database**
    ```bash
    flask db upgrade
    ```

5.  **Run the application**
    ```bash
    flask run
    ```
    Visit `http://localhost:5000` in your browser.

## Docker Setup

for a simpler setup using Docker:

1.  **Build the Docker images**
    ```bash
    make build
    ```

2.  **Start the application**
    ```bash
    make up
    ```
    The application will be available at `http://localhost:5000`.

3.  **Stop the application**
    ```bash
    make down
    ```

## Environment Configuration

Copy `.env.example` to `.env` and configure the following variables:

```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://...  # For production
```
