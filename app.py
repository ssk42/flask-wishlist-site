from collections import OrderedDict, defaultdict
from types import SimpleNamespace
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, abort, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import case
from sqlalchemy.orm import joinedload
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
import datetime
import pandas as pd
import os
import logging

app = Flask(__name__)

# Setup logging
try:
    from logging_config import setup_logging
    setup_logging(app)
except ImportError:
    # Fallback to basic logging if logging_config not available
    logging.basicConfig(level=logging.INFO)
    app.logger.info('Using basic logging configuration')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None  # CSRF tokens don't expire

# Initialize CSRF protection
csrf = CSRFProtect(app)

uri = os.getenv("DATABASE_URL")
if uri:
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    os.environ['DATABASE_URL'] = uri
    app.config['SQLALCHEMY_DATABASE_URI'] = uri
else:
    os.makedirs(app.instance_path, exist_ok=True)
    sqlite_path = os.path.join(app.instance_path, 'wishlist.sqlite')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{sqlite_path}'

db = SQLAlchemy(app)

migrate = Migrate(app, db)


PRIORITY_CHOICES = ['High', 'Medium', 'Low']
STATUS_CHOICES = ['Available', 'Claimed', 'Purchased', 'Received']

def get_items_url_with_filters():
    """Helper function to build items URL with preserved filters from session"""
    filters = {}
    if session.get('user_filter'):
        filters['user_filter'] = session['user_filter']
    if session.get('status_filter'):
        filters['status_filter'] = session['status_filter']
    if session.get('priority_filter'):
        filters['priority_filter'] = session['priority_filter']
    if session.get('category_filter'):
        filters['category_filter'] = session['category_filter']
    if session.get('q'):
        filters['q'] = session['q']
    if session.get('sort_by'):
        filters['sort_by'] = session['sort_by']
    if session.get('sort_order'):
        filters['sort_order'] = session['sort_order']
    return url_for('items', **filters)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    is_private = db.Column(db.Boolean, nullable=False, default=False)
    items = db.relationship('Item', backref='user', lazy=True, foreign_keys='Item.user_id')
    

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(750), nullable=False)
    link = db.Column(db.String(2048), nullable=True)  # Increased from 500 to 2048 for long URLs with tracking params
    comment = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Available', index=True)
    question = db.Column(db.String(100))
    year = db.Column(db.Integer, default=datetime.datetime.now().year)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    category = db.Column(db.String(50), index=True)  # New field for category
    image_url = db.Column(db.String(2048))  # Increased from 255 to 2048 for long URLs with tracking params
    priority = db.Column(db.String(50), index=True)
    last_updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_updated_by = db.relationship('User', foreign_keys=[last_updated_by_id])

    # Composite index for common query pattern (user_id + status)
    __table_args__ = (
        db.Index('idx_item_user_status', 'user_id', 'status'),
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with that email already exists. Try logging in instead.', 'warning')
            return render_template('registration.html', name=name, email=email)

        try:
            new_user = User(name=name, email=email)  # Define new_user
            db.session.add(new_user)
            db.session.commit()
            app.logger.info(f'New user registered: {email}')
            flash('Registration successful! Please log in to continue.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            app.logger.error(f'Registration failed for {email}: {str(e)}', exc_info=True)
            db.session.rollback()
            flash('An unexpected error occurred during registration. Please try again.', 'danger')
            return render_template('registration.html', name=name, email=email)

    return render_template('registration.html')



@app.route('/submit_item', methods=['GET', 'POST'])
@login_required
def submit_item():
    if request.method == 'POST':
        form_data = request.form.to_dict()
        description = form_data.get('description', '').strip()
        if not description:
            flash('A description is required to create an item.', 'danger')
            return render_template('submit_item.html', status_choices=STATUS_CHOICES, priority_choices=PRIORITY_CHOICES, form_data=form_data)

        link = form_data.get('link', '').strip() or None
        image_url = form_data.get('image_url', '').strip() or None
        category = form_data.get('category', '').strip() or None
        priority = form_data.get('priority') if form_data.get('priority') in PRIORITY_CHOICES else PRIORITY_CHOICES[0]
        status = form_data.get('status') if form_data.get('status') in STATUS_CHOICES else STATUS_CHOICES[0]

        price_input = form_data.get('price', '').strip()
        try:
            price = float(price_input) if price_input else None
        except ValueError:
            flash('Price must be a valid number.', 'danger')
            return render_template('submit_item.html', status_choices=STATUS_CHOICES, priority_choices=PRIORITY_CHOICES, form_data=form_data)

        new_item = Item(
            description=description,
            link=link,
            price=price,
            category=category,
            image_url=image_url,
            priority=priority,
            status=status,
            user_id=current_user.id
        )

        try:
            db.session.add(new_item)
            db.session.commit()
            app.logger.info(f'Item created by user_id={current_user.id}: {description[:50]}')
            flash('Item added to your wishlist!', 'success')
            return redirect(get_items_url_with_filters())
        except Exception as exc:
            app.logger.error(f'Failed to create item for user_id={current_user.id}: {str(exc)}', exc_info=True)
            db.session.rollback()
            flash('There was a problem saving your item. Please try again.', 'danger')
            return render_template('submit_item.html', status_choices=STATUS_CHOICES, priority_choices=PRIORITY_CHOICES, form_data=form_data)

    return render_template('submit_item.html', status_choices=STATUS_CHOICES, priority_choices=PRIORITY_CHOICES, form_data={})


@app.route('/items')
@login_required
def items():
    # Check if we should clear filters (when explicitly requested)
    clear_filters = request.args.get('clear_filters') == 'true'
    
    if clear_filters:
        # Clear all filters from session
        session.pop('user_filter', None)
        session.pop('status_filter', None)
        session.pop('priority_filter', None)
        session.pop('category_filter', None)
        session.pop('q', None)
        session.pop('sort_by', None)
        session.pop('sort_order', None)
        return redirect(url_for('items'))
    
    # Get filters from request args (for new filter applications)
    user_filter = request.args.get('user_filter', type=int)
    status_filter = request.args.get('status_filter')
    priority_filter = request.args.get('priority_filter')
    category_filter = request.args.get('category_filter', '').strip()
    search_query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort_by', 'priority')
    sort_order = request.args.get('sort_order', 'asc')
    
    # If filters are provided in the request, save them to session
    if any([user_filter, status_filter, priority_filter, category_filter, search_query]) or request.args.get('sort_by') or request.args.get('sort_order'):
        session['user_filter'] = user_filter
        session['status_filter'] = status_filter
        session['priority_filter'] = priority_filter
        session['category_filter'] = category_filter
        session['q'] = search_query
        session['sort_by'] = sort_by
        session['sort_order'] = sort_order
    else:
        # Use filters from session if no new filters provided
        user_filter = session.get('user_filter')
        status_filter = session.get('status_filter')
        priority_filter = session.get('priority_filter')
        category_filter = session.get('category_filter', '')
        search_query = session.get('q', '')
        sort_by = session.get('sort_by', 'priority')
        sort_order = session.get('sort_order', 'asc')

    query = (
        Item.query.options(joinedload(Item.user), joinedload(Item.last_updated_by))
        .join(User, Item.user_id == User.id)
    )

    if user_filter:
        query = query.filter(Item.user_id == user_filter)

    if status_filter:
        query = query.filter(Item.status == status_filter)

    if priority_filter:
        query = query.filter(Item.priority == priority_filter)

    if category_filter:
        query = query.filter(Item.category.ilike(f"%{category_filter}%"))

    if search_query:
        ilike_query = f"%{search_query}%"
        query = query.filter(Item.description.ilike(ilike_query))

    priority_order = case(
        (Item.priority == 'High', 1),
        (Item.priority == 'Medium', 2),
        (Item.priority == 'Low', 3),
        else_=4
    )

    sort_columns = {
        'price': Item.price,
        'status': Item.status,
        'description': Item.description,
        'category': Item.category,
        'created': Item.id,
        'user': User.name
    }

    if sort_by == 'priority':
        order_criteria = priority_order.asc() if sort_order == 'asc' else priority_order.desc()
    else:
        column = sort_columns.get(sort_by, Item.price)
        order_criteria = column.asc() if sort_order == 'asc' else column.desc()

    query = query.order_by(order_criteria, Item.description.asc())

    all_items = query.all()

    totals_dict = defaultdict(lambda: {'count': 0, 'total': 0.0})
    grouped_items = OrderedDict()
    for item in all_items:
        # For summary totals, exclude the current user's own claimed/purchased items to preserve surprise
        if item.user_id == current_user.id and item.status in ['Claimed', 'Purchased']:
            # Skip adding to totals_dict for surprise protection
            pass
        else:
            key = (item.user_id, item.status)
            totals_dict[key]['count'] += 1
            if item.price:
                totals_dict[key]['total'] += float(item.price)

        group = grouped_items.setdefault(item.user_id, SimpleNamespace(user=item.user, items=[]))
        group.items.append(item)

    users = User.query.order_by(User.name).all()

    user_lookup = {user.id: user for user in users}
    summary_rows = []
    for (user_id, status), data in totals_dict.items():
        summary_rows.append({
            'user': user_lookup.get(user_id),
            'status': status,
            'count': data['count'],
            'total': data['total']
        })

    summary_rows.sort(key=lambda row: ((row['user'].name if row['user'] else ''), row['status']))

    category_options = [value for value, in db.session.query(Item.category).filter(Item.category.isnot(None)).distinct().order_by(Item.category)]
    if category_filter and category_filter not in category_options:
        category_options.append(category_filter)
        category_options.sort()
    status_options = [value for value, in db.session.query(Item.status).filter(Item.status.isnot(None)).distinct().order_by(Item.status)]
    status_options = sorted(set(status_options + STATUS_CHOICES))

    active_filters = {
        'user_filter': user_filter,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'category_filter': category_filter,
        'q': search_query,
        'sort_by': sort_by,
        'sort_order': sort_order
    }

    sort_options = [
        ('priority', 'Priority'),
        ('price', 'Price'),
        ('status', 'Status'),
        ('description', 'Description'),
        ('category', 'Category'),
        ('user', 'User'),
        ('created', 'Recently Added')
    ]

    default_image_url = 'https://via.placeholder.com/600x400?text=Wishlist+Item'

    return render_template(
        'items_list.html',
        grouped_items=list(grouped_items.values()),
        users=users,
        summary_rows=summary_rows,
        status_options=status_options,
        priority_choices=PRIORITY_CHOICES,
        category_options=category_options,
        active_filters=active_filters,
        sort_options=sort_options,
        default_image_url=default_image_url
    )



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            login_user(user)
            app.logger.info(f'User logged in: {email} (user_id={user.id})')
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('index'))
        else:
            app.logger.warning(f'Failed login attempt for email: {email}')
            flash('We could not find an account with that email address.', 'danger')
            return render_template('login.html', email=email)
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)
    if request.method == 'POST':
        form_data = request.form.to_dict()

        if item.user_id != current_user.id:
            status = form_data.get('status')
            if status not in STATUS_CHOICES:
                flash('Please choose a valid status.', 'danger')
            else:
                item.status = status
                item.last_updated_by_id = current_user.id
                db.session.commit()
                flash('Status updated successfully.', 'success')
                return redirect(get_items_url_with_filters())
        else:
            description = form_data.get('description', '').strip()
            if not description:
                flash('Description cannot be empty.', 'danger')
                return render_template('edit_item.html', item=item, current_user=current_user, status_choices=STATUS_CHOICES, priority_choices=PRIORITY_CHOICES)

            price_input = form_data.get('price', '').strip()
            try:
                price = float(price_input) if price_input else None
            except ValueError:
                flash('Price must be a valid number.', 'danger')
                return render_template('edit_item.html', item=item, current_user=current_user, status_choices=STATUS_CHOICES, priority_choices=PRIORITY_CHOICES)

            item.description = description
            item.link = form_data.get('link', '').strip() or None
            item.price = price
            item.category = form_data.get('category', '').strip() or None
            item.image_url = form_data.get('image_url', '').strip() or None
            priority = form_data.get('priority')
            if priority in PRIORITY_CHOICES:
                item.priority = priority

            db.session.commit()
            flash('Item updated successfully.', 'success')
            return redirect(get_items_url_with_filters())

    return render_template('edit_item.html', item=item, current_user=current_user, status_choices=STATUS_CHOICES, priority_choices=PRIORITY_CHOICES)


@app.route('/claim_item/<int:item_id>', methods=['POST'])
@login_required
def claim_item(item_id):
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)

    if item.user_id == current_user.id:
        flash('You cannot claim your own item.', 'warning')
        return redirect(get_items_url_with_filters())

    if item.status != 'Available':
        flash('This item is no longer available to claim.', 'warning')
        return redirect(get_items_url_with_filters())

    item.status = 'Claimed'
    item.last_updated_by_id = current_user.id
    db.session.commit()

    flash(f'You have claimed "{item.description}".', 'success')
    return redirect(get_items_url_with_filters())

@app.route('/delete_item/<int:item_id>')
@login_required
def delete_item(item_id):
    item = db.session.get(Item, item_id)
    if item is None or item.user_id != current_user.id:
        flash('You do not have permission to delete this item.', 'danger')
        return redirect(get_items_url_with_filters())

    db.session.delete(item)
    db.session.commit()
    flash('Item deleted.', 'info')
    return redirect(get_items_url_with_filters())


@app.route('/export_items')
def export_items():
    # Query your database for items
    items = Item.query.all()

    # Create a DataFrame
    data = {
        'User': [item.user.name for item in items],
        'Description': [item.description for item in items],
        'Link': [item.link for item in items],
        'Comment': [item.comment for item in items],
        'Price': [item.price for item in items],
        'Year': [item.year for item in items]
        # Add other fields as necessary
    }
    df = pd.DataFrame(data)

    # Convert DataFrame to Excel
    filename = 'allWishlistItems.xlsx'
    df.to_excel(filename, index=False)

    return send_file(filename, as_attachment=True)

@app.route('/export_my_status_updates')
@login_required
def export_my_status_updates():
    items = Item.query.filter_by(last_updated_by_id=current_user.id).all()

    # Prepare data for the DataFrame
    data = {
        'Description': [item.description for item in items],
        'Status': [item.status for item in items],
        'Price': [item.price for item in items],
        'Updated By': [item.last_updated_by.name for item in items]
    }
    df = pd.DataFrame(data)

    filename = f'status_updates_by_{current_user.name}.xlsx'
    df.to_excel(filename, index=False)

    return send_file(filename, as_attachment=True)




login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Security headers
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    headers = app.config.get('SECURITY_HEADERS', {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
    })
    for header, value in headers.items():
        response.headers[header] = value
    return response


if __name__ == '__main__':
    app.run()  # pragma: no cover



