"""Authentication blueprint for user registration, login, and logout."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required

from models import db, User
from extensions import limiter

bp = Blueprint('auth', __name__)


@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    """Handle user registration."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()

        # Verify Family Code
        password = request.form.get('password')
        if password != current_app.config.get('FAMILY_PASSWORD'):
            flash('Incorrect Family Code. Please ask the family admin.', 'danger')
            return render_template('registration.html', name=name, email=email)

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with that email already exists. Try logging in instead.', 'warning')
            return render_template('registration.html', name=name, email=email)

        try:
            new_user = User(name=name, email=email)
            db.session.add(new_user)
            db.session.commit()
            current_app.logger.info(f'New user registered: {email}')
            flash('Registration successful! Please log in to continue.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            current_app.logger.error(f'Registration failed for {email}: {str(e)}', exc_info=True)
            db.session.rollback()
            flash('An unexpected error occurred during registration. Please try again.', 'danger')
            return render_template('registration.html', name=name, email=email)

    return render_template('registration.html')


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """Handle user login."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        # Verify Family Code
        password = request.form.get('password')
        if password != current_app.config.get('FAMILY_PASSWORD'):
            flash('Incorrect Family Code.', 'danger')
            return render_template('login.html', email=email)

        user = User.query.filter_by(email=email).first()
        if user:
            login_user(user)
            current_app.logger.info(f'User logged in: {email} (user_id={user.id})')
            flash(f'Welcome back, {user.name}!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            current_app.logger.warning(f'Failed login attempt for email: {email}')
            flash('We could not find an account with that email address.', 'danger')
            return render_template('login.html', email=email)
    return render_template('login.html')


@bp.route('/forgot_email', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_email():
    """Handle email recovery via name lookup."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Please enter your name.', 'warning')
            return render_template('forgot_email.html', name=name)

        # Search for users with matching name (case-insensitive)
        users = User.query.filter(User.name.ilike(name)).all()

        if len(users) == 1:
            # Exact match found
            user = users[0]
            current_app.logger.info(f'Email recovery successful for: {user.name}')
            return render_template('forgot_email.html', found_email=user.email, found_name=user.name)
        elif len(users) > 1:
            # Multiple matches found
            flash(f'We found {len(users)} accounts with similar names. Please contact support.', 'warning')
            return render_template('forgot_email.html', name=name)
        else:
            # No match found
            current_app.logger.warning(f'Email recovery failed for name: {name}')
            flash('We could not find an account with that name. Please check your spelling or sign up.', 'danger')
            return render_template('forgot_email.html', name=name)

    return render_template('forgot_email.html')


@bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('dashboard.index'))
