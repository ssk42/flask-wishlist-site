from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wishlist.db'
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = 'your-secret-key'

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
    status = db.Column(db.String(20), nullable=False)
    question = db.Column(db.String(100))
    year = db.Column(db.Integer, default=datetime.datetime.now().year)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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
        # Assuming a placeholder for the current user's ID
        user_id = 1  # Replace this with the actual logic to get the current user's ID

        new_item = Item(description=description, link=link, price=price, 
                        status='Available', user_id=current_user.id)
        db.session.add(new_item)
        db.session.commit()

        return redirect(url_for('items'))
    return render_template('submit_item.html')


@app.route('/items')
@login_required
def items():
    all_items = Item.query.all()
    return render_template('items_list.html', items=all_items, current_user=current_user)

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

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


if __name__ == '__main__':
    app.run(debug=True)



