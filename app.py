from flask import Flask, render_template, request, session, flash, jsonify, Response, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import json
import os
from functools import wraps
import secrets
from flask_mail import Mail, Message
from flask_caching import Cache

secretKey = secrets.token_urlsafe(16)

cache = Cache()

app = Flask(__name__)

app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
cache.init_app(app)

app.secret_key = secretKey

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

class CartCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    card_id = db.Column(db.String(100), nullable=False)
    series = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=False, nullable=False)
    username = db.Column(db.String(100), unique=False, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    delivery_details = db.relationship('DeliveryDetails', backref='user', uselist=False)
    cart_cards = db.relationship('CartCard', backref='user', lazy=True)
    favorite_cards = db.relationship('FavoriteCard', backref='user', lazy=True)

class DeliveryDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    address1 = db.Column(db.String(100), nullable=False)
    address2 = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)

class FavoriteCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    card_id = db.Column(db.String(100), nullable=False)
    series = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    facts = db.Column(db.String(255), nullable=True)
    imageUrl = db.Column(db.String(255), nullable=True)

with app.app_context():
    db.create_all()

app.config.update(dict(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_TLS=False,
    MAIL_USE_SSL=True,
    MAIL_USERNAME = 'companygojim@gmail.com',
    MAIL_PASSWORD = 'znowewnnfmgdisvy',
))

mail = Mail(app)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        user_message = request.form.get('message')
        
        msg = Message("New message from your Flask app",
                      sender=email,
                      recipients=["ecommercepokemon@gmail.com"])
        msg.body = f"""
        From: {name} <{email}>
        {user_message}
        """
        mail.send(msg)

        formMessage = "Form submitted."
        return render_template('contact.html', formMessage=formMessage)
    return render_template('contact.html')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logged_in = session.get('logged_in', False)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/decrease_quantity', methods=['POST', 'GET'])
@login_required
@cache.cached(timeout=300, key_prefix='cart_items')
def decrease_quantity():
    if request.method == 'POST':
        card_id = request.form.get('card_id')
        print("Card ID:", card_id)
        email = session.get('email')
        user = User.query.filter_by(email=email).first()
        cart_items = user.cart_cards

        cart_card = CartCard.query.filter_by(card_id=card_id, user_id=user.id).first()

        if cart_card.quantity > 1:
            cart_card.quantity -= 1
            db.session.commit()
        else:
            db.session.delete(cart_card)
            db.session.commit()
    
        cart_items = cache.get('cart_items')
        if cart_items is None:
            cart_items = user.cart_cards
            cache.set('cart_items', cart_items)

        cart_count = sum(cart_item.quantity for cart_item in cart_items)

    file_path = os.path.join(app.static_folder, 'profiles.json')
    with open(file_path) as file:
        cards_data = json.load(file)

    return render_template('catalogueLogged.html', user=user, cards=cards_data, cart_items=cart_items, cart_count=cart_count)


@app.route('/increase_quantity', methods=['GET', 'POST'])
@login_required
def increase_quantity():
    if request.method == 'POST':
        email = session.get('email')
        user = User.query.filter_by(email=email).first()
        cart_items = user.cart_cards
        card_id = request.form.get('card_id')

        cart_card = CartCard.query.filter_by(card_id=card_id, user_id=user.id).first()

        cart_card.quantity += 1
        db.session.commit()

        cart_count = sum(cart_item.quantity for cart_item in cart_items)

    file_path = os.path.join(app.static_folder, 'profiles.json')
    with open(file_path) as file:
        cards_data = json.load(file)

    return render_template('catalogueLogged.html', user=user, cards=cards_data, cart_items=cart_items, cart_count=cart_count)

@app.route('/newPassword', methods=['POST'])
def reset_password():

    file_path = os.path.join(app.static_folder, 'profiles.json')
    with open(file_path) as file:
        cards_data = json.load(file)

    username_email = request.form.get('username-email')
    user = User.query.filter((User.username == username_email) | (User.email == username_email)).first()
    if request.method == 'POST':
        new_password = request.form.get('newpassword')
        if new_password:
            user.password = new_password
            db.session.commit()
    passwordChange = "Password was successfully changed!"
    return render_template('catalogue.html', cards=cards_data, passwordChange=passwordChange)

    
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    email = session.get('email')
    user = User.query.filter_by(email=email).first()

    if request.method == 'POST':
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_password = request.form.get('password')

        user.username = new_username
        user.email = new_email
        user.password = new_password
        db.session.commit()

    return render_template('settingsUser.html', user=user, favorite_cards=user.favorite_cards)

@app.route('/profiles/<card_id>', methods=['POST'])
@login_required
def add_to_favorites(card_id):
    email = session.get('email')
    user = User.query.filter_by(email=email).first()
    card_profile = get_card_profile(card_id)
    favorite_card = FavoriteCard(
        user_id=user.id,
        card_id=card_id,
        series=card_profile['series'],
        name=card_profile['name'],
        price=card_profile['marketValue'],
        facts=int(card_profile['facts'][0]),
        imageUrl=card_profile['imageUrl']
    )
    db.session.add(favorite_card)
    db.session.commit()
    file_path = os.path.join(app.static_folder, 'profiles.json')
    with open(file_path) as file:
        cards_data = json.load(file)
    return redirect(url_for('profiles', card_id=card_id))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/settings/delivery', methods=['POST'])
def save_settings():
    email = session.get('email')
    user = User.query.filter_by(email=email).first()

    if request.method == 'POST':
        address1 = request.form['address1']
        address2 = request.form['address2']
        country = request.form['country']
        city = request.form['city']
        zip_code = request.form['zip-code']
        phone_number = request.form['phone-number']

    delivery_details = DeliveryDetails(
        address1=address1,
        address2=address2,
        country=country,
        city=city,
        zip_code=zip_code,
        phone_number=phone_number
    )

    user.delivery_details = delivery_details

    db.session.commit()

    return render_template('settingsUser.html', user=user)

@app.route('/add_to_cart/<card_id>', methods=['POST'])
@login_required
def add_to_cart(card_id):
    email = session.get('email')
    user = User.query.filter_by(email=email).first()
    cart_card = CartCard.query.filter_by(card_id=card_id).first()
    cart_items = user.cart_cards

    if cart_card:
        cart_card.quantity += 1
    else:
        card_profile = get_card_profile(card_id)
        cart_card = CartCard(
            user_id=user.id,
            card_id=card_id,
            series=card_profile['series'],
            name=card_profile['name'],
            price=card_profile['marketValue'],
            quantity=1
        )
        db.session.add(cart_card)

    db.session.commit()

    cart_count = sum(cart_item.quantity for cart_item in cart_items)

    file_path = os.path.join(app.static_folder, 'profiles.json')
    with open(file_path) as file:
        cards_data = json.load(file)

    return render_template('catalogueLogged.html', user=user, cards=cards_data, cart_items=cart_items, cart_count=cart_count)


@app.route('/')
def index():
    file_path = os.path.join(app.static_folder, 'profiles.json')
    with open(file_path) as file:
        cards_data = json.load(file)

    logged_in = session.get('logged_in', False)
    email = session.get('email')
    
    if logged_in and email:
        user = User.query.filter_by(email=email).first()
        cart_items = user.cart_cards
        cart_count = len(cart_items)
    else:
        cart_items = []
        cart_count = 0

    return render_template('catalogue.html', cards=cards_data, logged_in=logged_in, cart_count=cart_count, cart_items=cart_items)


@app.route('/catalogue', methods=['POST'])
@login_required
def login():
    email = request.form['email']
    password = request.form['psw']

    file_path = os.path.join(app.static_folder, 'profiles.json')
    with open(file_path) as file:
        cards_data = json.load(file)

    userValidation = User.query.filter_by(email=email, password=password).first()

    if userValidation:
        user = User.query.filter_by(email=email).first()
        session['email'] = email
        session['username'] = user.username
        session['logged_in'] = True
        session['token'] = secrets.token_urlsafe(16)
        cart_items = user.cart_cards if 'email' in session else []
        cart_count = sum(cart_item.quantity for cart_item in cart_items)
        sucessful_message = "Welcome!"
        return render_template('catalogueLogged.html', cards=cards_data, sucessful_message=sucessful_message, user=user, cart_count=cart_count, cart_items=cart_items)
    else:
        error_message = "Password or email is incorrect. Please try again."
        return render_template('catalogue.html', cards=cards_data, error_message=error_message)
    
@app.route('/create_account', methods=['POST'])
def create_account():

    file_path = os.path.join(app.static_folder, 'profiles.json')
    with open(file_path) as file:
        cards_data = json.load(file)

    email = request.form['email']
    username = request.form['username']
    password = request.form['psw']

    new_user = User(email=email, username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    message = "Your account was created successfully!"
    return render_template('catalogue.html', message=message, cards=cards_data)

@app.route('/series/<series_name>')
@login_required
def series_catalogue(series_name):
    file_path = os.path.join(app.static_folder, 'profiles.json')
    with open(file_path) as file:
        cards_data = json.load(file)
    
    logged_in = session.get('logged_in', False)
    email = session.get('email')
    user = User.query.filter_by(email=email).first()
    cart_items = user.cart_cards
    cart_count = sum(cart_item.quantity for cart_item in cart_items)

    filtered_cards = [card for card in cards_data if card['series'] == series_name]

    return render_template('series_catalogue.html', cards=filtered_cards, series_name=series_name, logged_in=logged_in, cart_items=cart_items, user=user, cart_count=cart_count)

@app.route('/name/<pokemon_name>')
@login_required
def searched_catalogue(pokemon_name):
    file_path = os.path.join(app.static_folder, 'profiles.json')
    with open(file_path) as file:
        cards_data = json.load(file)

    logged_in = session.get('logged_in', False)
    email = session.get('email')
    
    if logged_in and email:
        user = User.query.filter_by(email=email).first()
        cart_items = user.cart_cards
        cart_count = sum(cart_item.quantity for cart_item in cart_items)
    else:
        cart_items = []
        cart_count = 0

    filtered_cards = [card for card in cards_data if card['name'] == pokemon_name]

    return render_template('searched_catalogue.html', cards=filtered_cards, pokemon_name=pokemon_name, logged_in=logged_in, cart_count=cart_count, cart_items=cart_items, user=user)

@app.route('/profiles/<card_id>')
@login_required
def profiles(card_id):
    card_profile = get_card_profile(card_id)

    logged_in = session.get('logged_in', False)
    email = session.get('email')
    
    if logged_in and email:
        user = User.query.filter_by(email=email).first()
        cart_items = user.cart_cards
        cart_count = sum(cart_item.quantity for cart_item in cart_items)
    else:
        cart_items = []
        cart_count = 0

    return render_template('profile.html', card=card_profile, logged_in=logged_in, cart_count=cart_count, user=user)

@app.route('/all_cards')
@login_required
def all_cards():
    file_path = os.path.join(app.static_folder, 'profiles.json')
    with open(file_path) as file:
        cards_data = json.load(file)
    
    logged_in = session.get('logged_in', False)
    email = session.get('email')
    
    if logged_in and email:
        user = User.query.filter_by(email=email).first()
        cart_items = user.cart_cards
        cart_count = sum(cart_item.quantity for cart_item in cart_items)
    else:
        cart_items = []
        cart_count = 0

    print(cart_count)
    return render_template('all_cards.html', cards=cards_data, logged_in=logged_in, cart_count=cart_count, cart_items=cart_items, user=user)


def get_card_profile(card_id):
    file_path = os.path.join(app.static_folder, 'profiles.json')
    with open(file_path) as file:
        cards_data = json.load(file)

    for card in cards_data:
        if card['id'] == card_id:
            return card

    return None

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

if __name__ == "__main__":
    app.run(debug=True)