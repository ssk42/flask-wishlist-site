from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import datetime
import pandas as pd

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wishlist.db'
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = 'your-secret-key'
migrate = Migrate(app, db)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    items = db.relationship('Item', backref='user', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(50), nullable=False)
    link = db.Column(db.String(50))
    comment = db.Column(db.String(100))
    price = db.Column(db.Float)
    status = db.Column(db.String(20), nullable=False, default='Available')
    question = db.Column(db.String(100))
    year = db.Column(db.Integer, default=datetime.datetime.now().year)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50))  # New field for category
    image_url = db.Column(db.String(255))  # New field for image URL
    priority = db.Column(db.String(50))

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

        new_user = User(name=name, email=email)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('index'))
    return render_template('registration.html')


@app.route('/submit_item', methods=['GET', 'POST'])
@login_required
def submit_item():
    if request.method == 'POST':
        description = request.form['description']
        link = request.form['link']
        price = float(request.form['price'])
        user_id = current_user.id  


        new_item = Item(description=description, link=link, price=price, 
                        category=request.form['category'], 
                        image_url=request.form['image_url'],
                        priority = request.form['priority'],
                        status=request.form['status'], user_id=current_user.id)
        db.session.add(new_item)
        db.session.commit()

        return redirect(url_for('items'))
    return render_template('submit_item.html')


@app.route('/items')
@login_required
def items():
    sort_by = request.args.get('sort_by', 'user')  # Default sort by user
    sort_order = request.args.get('sort_order', 'asc')  # Default sort order

    if sort_by == 'price':
        # Sorting logic by price
        all_items = Item.query.order_by(Item.price.asc() if sort_order == 'asc' else Item.price.desc()).all()
    else:
        # Default sorting by user and status
        all_items = Item.query.order_by(Item.user_id, Item.status).all()
        # Calculate total price by user and status
        total_price_by_user_status = db.session.query(
            Item.user_id, Item.status, db.func.sum(Item.price).label('total_price')
        ).group_by(Item.user_id, Item.status).all()

        # Convert to a more accessible format if necessary, e.g., a dictionary
        totals_dict = {(total.user_id, total.status): total.total_price for total in total_price_by_user_status}

    return render_template('items_list.html', items=all_items, current_user=current_user, totals=totals_dict)

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
    item = Item.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        if request.method == 'POST':
           item.status = request.form['status'] 
           db.session.commit()
           return redirect(url_for('items'))

    if request.method == 'POST':
        # Update item details with data from the form
        item.description = request.form['description']
        item.link = request.form['link']
        item.price = float(request.form['price'])
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
    item = Item.query.get_or_404(item_id)
    if item.user_id != current_user.id:
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



login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


if __name__ == '__main__':
    app.run(debug=True)



