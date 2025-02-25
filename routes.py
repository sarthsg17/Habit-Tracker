from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Activity, Badge
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


# Create a single Blueprint for all routes
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('home.html')

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Please use a different one.', 'danger')
            return redirect(url_for('main.register'))

        # Create new user
        new_user = User(username=username, email=email, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username  # Store username in session
            flash('Login successful!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('login.html')

@main_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("You need to log in first.", "danger")
        return redirect(url_for('main.login'))

    user_id = session['user_id']
    activities = Activity.query.filter_by(user_id=user_id).all()

    return render_template('dashboard.html', username=session['username'], activities=activities)

@main_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('main.home'))

@main_bp.route('/badges')
def badges():
    if 'user_id' not in session:
        flash("You need to log in first.", "danger")
        return redirect(url_for('main.login'))

    user_id = session['user_id']
    user_badges = Badge.query.filter_by(user_id=user_id).all()

    return render_template('badges.html', username=session['username'], badges=user_badges)

