import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from cryptography.fernet import Fernet

app = Flask(__name__)
# Secret key for sessions
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-super-secret-key-for-session')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Setup Fernet key for encrypting game passwords
KEY_FILE = 'secret.key'
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'wb') as f:
        f.write(Fernet.generate_key())

with open(KEY_FILE, 'rb') as f:
    FERNET_KEY = f.read()

fernet = Fernet(FERNET_KEY)

# =======================
# UTILITY ENCRYPTION FUNC
# =======================
def encrypt_password(plain_text: str) -> str:
    return fernet.encrypt(plain_text.encode('utf-8')).decode('utf-8')

def decrypt_password(cipher_text: str) -> str:
    try:
        return fernet.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except Exception:
        return "Decryption Error"

# =======================
# DATABASE MODELS
# =======================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

class GameAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    level = db.Column(db.Integer, nullable=True)
    uid = db.Column(db.String(12), nullable=False)
    game_email = db.Column(db.String(150), nullable=True)
    encrypted_pass = db.Column(db.Text, nullable=False)
    player_name = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Active') # Active, Banned, Blacklisted
    unban_time = db.Column(db.DateTime, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =======================
# APPLICATION ROUTES
# =======================
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash("Email is already registered! Please login.", "danger")
            return redirect(url_for('register'))
        
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(email=email, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Login failed. Check your email and password.", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Only fetch accounts belonging to the current user (Private Data Isolation)
    accounts = GameAccount.query.filter_by(user_id=current_user.id).order_by(GameAccount.last_updated.desc()).all()
    # Adding a clean decrypted password property for the template
    for acc in accounts:
        acc.decrypted_password = decrypt_password(acc.encrypted_pass)
    return render_template('dashboard.html', accounts=accounts, now=datetime.utcnow())

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_account():
    if request.method == 'POST':
        uid = request.form.get('uid')
        level = request.form.get('level')
        game_email = request.form.get('game_email')
        user_password = request.form.get('gpassword')
        player_name = request.form.get('player_name')
        status = request.form.get('status')
        ban_date_str = request.form.get('ban_date') # e.g. "2026-04-10T12:00"
        
        if len(uid) > 12 or not uid.isdigit():
            flash("UID must be a number with a maximum of 12 digits.", "danger")
            return redirect(url_for('add_account'))

        unban_time = None
        if status in ['Banned', 'Blacklisted'] and ban_date_str:
            try:
                ban_date = datetime.strptime(ban_date_str, '%Y-%m-%dT%H:%M')
                unban_time = ban_date + timedelta(days=30)
            except ValueError:
                flash("Invalid Date Format for Ban Date", "danger")

        # Encrypt the Game Password before storing
        encrypted_pw = encrypt_password(user_password)
        
        new_account = GameAccount(
            user_id=current_user.id,
            level=int(level) if level else None,
            uid=uid,
            game_email=game_email,
            encrypted_pass=encrypted_pw,
            player_name=player_name,
            status=status,
            unban_time=unban_time
        )
        db.session.add(new_account)
        db.session.commit()
        flash("Game account safely added!", "success")
        return redirect(url_for('dashboard'))
    
    return render_template('add_edit.html', action='Add', account=None)

@app.route('/edit/<int:account_id>', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    account = GameAccount.query.get_or_404(account_id)
    # Ensure privacy: Only owner can edit
    if account.user_id != current_user.id:
        flash("Unauthorized command.", "danger")
        return redirect(url_for('dashboard'))

    account.decrypted_password = decrypt_password(account.encrypted_pass)
    
    # Calculate original ban date for the frontend form
    if account.unban_time:
        account.ban_date = account.unban_time - timedelta(days=30)

    if request.method == 'POST':
        uid = request.form.get('uid')
        level = request.form.get('level')
        game_email = request.form.get('game_email')
        user_password = request.form.get('gpassword')
        player_name = request.form.get('player_name')
        status = request.form.get('status')
        ban_date_str = request.form.get('ban_date')
        
        if len(uid) > 12 or not uid.isdigit():
            flash("UID must be a numeric value up to 12 digits.", "danger")
            return redirect(url_for('edit_account', account_id=account.id))

        unban_time = None
        if status in ['Banned', 'Blacklisted'] and ban_date_str:
            try:
                ban_date = datetime.strptime(ban_date_str, '%Y-%m-%dT%H:%M')
                unban_time = ban_date + timedelta(days=30)
            except ValueError:
                pass
        account.level = int(level) if level else None
        account.uid = uid
        account.game_email = game_email
        if user_password and user_password != account.decrypted_password:
             account.encrypted_pass = encrypt_password(user_password)
        account.player_name = player_name
        account.status = status
        account.unban_time = unban_time
        
        db.session.commit()
        flash("Game account updated!", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_edit.html', action='Edit', account=account)

@app.route('/delete/<int:account_id>', methods=['POST'])
@login_required
def delete_account(account_id):
    account = GameAccount.query.get_or_404(account_id)
    if account.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('dashboard'))
    
    db.session.delete(account)
    db.session.commit()
    flash("Account deleted securely.", "success")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Host="0.0.0.0" is used so it can be tested nicely.
    app.run(debug=True, host="0.0.0.0", port=5000)
