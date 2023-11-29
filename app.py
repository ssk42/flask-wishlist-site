from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import session
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import datetime
import pandas as pd
import os
import re

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wishlist.db'


uri = os.getenv("DATABASE_URL")  # or other relevant config var
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
os.environ['DATABASE_URL'] = uri

app.config['SQLALCHEMY_DATABASE_URI'] = uri

db = SQLAlchemy(app)
app.config['SECRET_KEY'] = 'your-secret-key'

migrate = Migrate(app, db)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    items = db.relationship('Item', backref='user', lazy=True, foreign_keys='Item.user_id')
    

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(750), nullable=False)
    link = db.Column(db.String(500), nullable=True)
    comment = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Available')
    question = db.Column(db.String(100))
    year = db.Column(db.Integer, default=datetime.datetime.now().year)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50))  # New field for category
    image_url = db.Column(db.String(255))  # New field for image URL
    priority = db.Column(db.String(50))
    last_updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_updated_by = db.relationship('User', foreign_keys=[last_updated_by_id])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return 'User already exists!'

        try:
            new_user = User(name=name, email=email)  # Define new_user
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            print(e)  # Log the exception for debugging
            db.session.rollback()
            return 'An error occurred during registration.'

    return render_template('registration.html')



@app.route('/submit_item', methods=['GET', 'POST'])
@login_required
def submit_item():
    if request.method == 'POST':
        description = request.form['description']
        # if description.count() > 250:
        #     return 'The description is too long. Consider shortening it.'
        link = request.form['link'] if request.form['link'] else None
        price = float(request.form['price']) if request.form['price'] else None
        user_id = current_user.id  


        new_item = Item(description=description, link=link, price=price, 
                        category=request.form['category'], 
                        image_url=request.form['image_url'],
                        priority = request.form['priority'],
                        status=request.form['status'], user_id=user_id)
        db.session.add(new_item)
        db.session.commit()

        return redirect(url_for('items'))
    return render_template('submit_item.html')


@app.route('/items')
@login_required
def items():
    user_filter = request.args.get('user_filter')
    sort_by = request.args.get('sort_by', 'price')  # Default sort by price
    sort_order = request.args.get('sort_order', 'asc')  # Default sort order

    # Initialize totals_dict before the if-else blocks
    totals_dict = {}

    query = Item.query
    if user_filter:
        query = query.filter_by(user_id=user_filter)
    
    if sort_by == 'price':
        query = query.order_by(Item.price.asc() if sort_order == 'asc' else Item.price.desc())
    else:
        query = query.order_by(Item.user_id, Item.status)

    all_items = query.all()

    # Calculate total price by user and status
    # Note: Adjust this part if needed to work with the user filter
    total_price_by_user_status = db.session.query(
        Item.user_id, Item.status, db.func.sum(Item.price).label('total_price')
    ).group_by(Item.user_id, Item.status).all()
    totals_dict = {(total.user_id, total.status): total.total_price for total in total_price_by_user_status}

    # Fetch all users for the dropdown
    users = User.query.all()

    return render_template('items_list.html', items=all_items, users=users, current_user=current_user, totals=totals_dict)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        else:
            return 'Invalid email'
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)
    # Rest of your code...

    if item.user_id != current_user.id:
        if request.method == 'POST':
           item.status = request.form['status']
           item.last_updated_by_id = current_user.id 
           db.session.commit()
           return redirect(url_for('items'))

    if request.method == 'POST':
        # Update item details with data from the form
        item.description = request.form['description']
        item.link = request.form['link'] if request.form['link'] else None
        item.price = float(request.form['price']) if request.form['price'] else None
        # In /edit_item route
        item.category = request.form['category']
        item.image_url = request.form['image_url']
        item.priority = request.form['priority']
        # item.status = request.form['status']

        db.session.commit()
        return redirect(url_for('items'))

    return render_template('edit_item.html', item=item, current_user = current_user)

@app.route('/delete_item/<int:item_id>')
@login_required
def delete_item(item_id):
    item = db.session.get(Item, item_id)
    if item is None or item.user_id != current_user.id:
        return 'You do not have permission to delete this item.'
    
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('items'))


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

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


if __name__ == '__main__':
    app.run()



