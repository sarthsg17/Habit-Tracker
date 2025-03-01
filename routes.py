from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Activity, Badge
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from flask import current_app


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
        identifier = request.form['identifier'] 
        password = request.form['password']

        user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username  # Store username in session
            flash('Login successful!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('login.html')

@main_bp.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        flash("You need to log in first.", "danger")
        return redirect(url_for('main.login'))

    user_id = session['user_id']

    if request.method == 'POST':
        habit_name = request.form.get('habit_name')

        if habit_name:
            new_habit = Activity(name=habit_name, user_id=user_id, streak=0, last_completed=None)
            db.session.add(new_habit)
            db.session.commit()
            flash("Habit added successfully!", "success")

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

@main_bp.route('/complete_habit/<int:habit_id>', methods=['POST'])
def complete_habit(habit_id):
    if 'user_id' not in session:
        flash("You must be logged in to complete a habit!", "danger")
        return redirect(url_for('main.login'))

    habit = Activity.query.get(habit_id)
    if habit and habit.user_id == session['user_id']:
        habit.complete_habit()
        flash("Habit marked as complete!", "success")
    else:
        flash("Habit not found or unauthorized!", "danger")

    return redirect(url_for('main.dashboard'))

def reset_streaks():
    with current_app.app_context():
        today = datetime.now(timezone.utc).date()
        habits = Activity.query.all()

        for habit in habits:
            if habit.last_completed and habit.last_completed.date() < (today - timedelta(days=1)):
                habit.streak = 0  # Reset streak if missed
                db.session.commit()

