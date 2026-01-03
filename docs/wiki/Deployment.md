# Deployment Guide

## Heroku Deployment

This application is designed to be deployed on Heroku.

### Prerequisites
- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
- Valid Heroku account

### Steps

1.  **Login to Heroku**
    ```bash
    heroku login
    ```

2.  **Create App**
    ```bash
    heroku create your-app-name
    ```

3.  **Configure Environment Variables**
    ```bash
    heroku config:set SECRET_KEY=your-secret-key-here
    ```
    The `DATABASE_URL` is automatically set by Heroku when adding the Postgres add-on.

4.  **Add Postgres Add-on** (if not already added)
    ```bash
    heroku addons:create heroku-postgresql:hobby-dev
    ```

5.  **Deploy**
    ```bash
    git push heroku main
    ```

### Automatic Migrations
The `Procfile` is configured to automatically run database migrations on every release:

```
release: flask db upgrade
web: gunicorn app:app
```

This ensures that your production database is always in sync with your code.
