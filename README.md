# Family Wishlist Application

## Overview

The Family Wishlist Application is a web-based platform designed for families to create, share, and manage their wishlists. It allows each family member to add items they wish for, along with details like description, price, and category. Family members can view each other's wishlists, making it easier to give meaningful gifts.

## Features

- User registration and login system.
- Ability to add, edit, and delete wishlist items.
- View wishlists of all family members.
- Sort items by different criteria (user, price, status).
- Export wishlist items to Excel.
- Responsive design for a better experience across various devices.

## Technologies Used

- Flask (Python web framework)
- Bootstrap (Front-end framework)
- SQLite/PostgreSQL (Database)
- Heroku (Hosting platform)

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

What things you need to install the software and how to install them:

> python>=3.8
> pip
> virtualenv (optional)


### Installing

A step-by-step series of examples that tell you how to get a development environment running:

1. Clone the repository:
> git clone https://github.com/ssk42/flask-wishlist-site.git

2. Navigate to the project directory:
> cd wishlist

3. Create a virtual environment (optional):
> virtualenv venv

4. Activate the virtual environment:
- On Windows:
  ```
  .\venv\Scripts\activate
  ```
- On Unix or MacOS:
  ```
  source venv/bin/activate
  ```
5. Install required packages:
> pip install -r requirements.txt


### Running the Application

1. Set environment variables:
> export FLASK_APP=app.py
> export FLASK_ENV=development

2. Initialize the database:
> flask db upgrade

3. Run the application:
> flask run


## Testing

The project includes unit tests that exercise the Flask application and automated
browser regression tests powered by Playwright. To run the full suite locally:

1. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Install the Playwright browsers (only required for the browser regression
   tests):

   ```bash
   playwright install --with-deps chromium
   ```

3. Execute the tests with `pytest`:

   ```bash
   pytest
   ```

Unit tests are located under `tests/unit/` and use Flask's testing client and a
temporary SQLite database. Browser regression tests live under
`tests/browser/` and validate the end-to-end registration workflow.

## Deployment

Instructions on how to deploy the app on Heroku:

1. Create a Heroku account and install Heroku CLI.
2. Log in to Heroku through the CLI.
3. Set up your Heroku git remote.
4. Push to Heroku:
>git push heroku main
5. Set up environment variables on Heroku.


## Authors

- **Steve Reitz** - 


## Acknowledgments

- Thx ChatGPT for helping me learn Flask!
