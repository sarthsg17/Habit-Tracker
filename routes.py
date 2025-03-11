from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, User, Activity, Badge, Admin, UserBadge, CalendarEvent
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from flask import current_app
from werkzeug.utils import secure_filename
import json
import os
UPLOAD_FOLDER = "static/badges/"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Blueprint for all routes
main_bp = Blueprint('main', __name__)

# Home Page
@main_bp.route('/')
def home():
    return render_template('home.html')

# Register User
@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Please use a different one.', 'danger')
            return redirect(url_for('main.register'))

        new_user = User(username=username, email=email, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html')

# Login User/Admin
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']

        # Check if user is an admin
        admin = Admin.query.filter_by(username=identifier).first()
        if admin and check_password_hash(admin.password_hash, password):
            session['user_id'] = admin.id
            session['username'] = admin.username
            session['is_admin'] = True  # Set admin flag
            flash('Admin login successful!', 'success')
            return redirect(url_for('main.admin_dashboard'))

        # Check if user is a regular user
        user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = False  # Regular user
            flash('Login successful!', 'success')
            return redirect(url_for('main.dashboard'))

        flash('Invalid credentials. Please try again.', 'danger')

    return render_template('login.html')

# User Dashboard
@main_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("You need to log in first.", "danger")
        return redirect(url_for('main.login'))

    if session.get('is_admin'):
        return redirect(url_for('main.admin_dashboard'))  # Redirect admins to admin dashboard

    return render_template('dashboard.html', username=session['username'])

# Admin Dashboard
@main_bp.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        flash("Access denied. Admins only!", "danger")
        return redirect(url_for('main.dashboard'))
    
    badges = Badge.query.all()

    return render_template('admin_dashboard.html', username=session['username'], badges=badges)

# Logout
@main_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('main.home'))

# View User Badges
@main_bp.route('/badges')
def badges():
    if 'user_id' not in session:
        flash("You need to log in first.", "danger")
        return redirect(url_for('main.login'))

    user_id = session['user_id']
    user_badges = UserBadge.query.filter_by(user_id=user_id).all()

    # Escape descriptions for JavaScript
    for badge in user_badges:
        badge.badge.name_escaped = json.dumps(badge.badge.name)
        badge.badge.description_escaped = json.dumps(badge.badge.description)
        badge.habit = Activity.query.get(badge.habit_id)

    return render_template('badges.html', username=session['username'], badges=user_badges)

# Add a New Habit
@main_bp.route('/add_habit', methods=['POST'])
def add_habit():
    if 'user_id' not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for('main.login'))

    habit_name = request.form.get('habit_name')
    if not habit_name:
        flash("Habit name cannot be empty.", "danger")
        return redirect(url_for('main.dashboard'))

    new_habit = Activity(name=habit_name, user_id=session['user_id'])
    db.session.add(new_habit)
    db.session.commit()

    flash("Habit added successfully!", "success")
    return redirect(url_for('main.manage_habits'))

# Manage User Habits
@main_bp.route('/manage-habits')
def manage_habits():
    if 'user_id' not in session:
        flash("Please log in to view your habits.", "danger")
        return redirect(url_for('main.login'))

    user_id = session['user_id']
    habits = Activity.query.filter_by(user_id=user_id).all()

    return render_template('manage_habits.html', activities=habits)

# Complete a Habit and Update Streak
@main_bp.route('/complete_habit/<int:habit_id>', methods=['POST'])
def complete_habit(habit_id):
    if 'user_id' not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for('main.login'))

    habit = Activity.query.get_or_404(habit_id)
    user_id = session['user_id']

    if habit.user_id != user_id:
        flash("Unauthorized action!", "danger")
        return redirect(url_for('main.dashboard'))

    today = datetime.utcnow().date()

    if habit.last_completed and habit.last_completed.date() == today:
        flash("You have already completed this habit today.", "warning")
        return redirect(url_for('main.dashboard'))

    # Update streak
    if habit.last_completed and habit.last_completed.date() == today - timedelta(days=1):
        habit.streak += 1
    else:
        habit.streak = 1

    habit.last_completed = datetime.utcnow()

    # Check for badge rewards
    eligible_badges = Badge.query.filter(Badge.streak_required == habit.streak).all()
    for badge in eligible_badges:
        existing_badge = UserBadge.query.filter_by(user_id=user_id, habit_id=habit.id, badge_id=badge.id).first()
        if not existing_badge:
            new_user_badge = UserBadge(user_id=user_id, habit_id=habit.id, badge_id=badge.id)
            db.session.add(new_user_badge)
            flash(f"🎉 You earned a new badge: {badge.name}!", "success")

    db.session.commit()
    return redirect(url_for('main.dashboard'))

# Create a Badge (Admin Only)
@main_bp.route('/admin/create_badge', methods=['POST'])
def create_badge():
    if "badge_image" not in request.files:
        flash("No image uploaded", "error")
        return redirect(url_for("main.admin_dashboard"))

    file = request.files["badge_image"]
    if file.filename == "" or not allowed_file(file.filename):
        flash("Invalid file type", "error")
        return redirect(url_for("main.admin_dashboard"))

    filename = secure_filename(file.filename)
    file.save(os.path.join(UPLOAD_FOLDER, filename))

    new_badge = Badge(
        name=request.form["name"],
        description=request.form["description"],
        streak_required=int(request.form["streak_required"]),
        image_filename=filename
    )
    db.session.add(new_badge)
    db.session.commit()

    flash("Badge created successfully!", "success")
    return redirect(url_for("main.admin_dashboard"))

@main_bp.route('/confirm_delete/<int:habit_id>', methods=['GET', 'POST'])
def confirm_delete(habit_id):
    habit = Activity.query.get_or_404(habit_id)

    if request.method == 'POST':

        user_badges = UserBadge.query.filter_by(habit_id=habit_id).all()
        for user_badge in user_badges:
            user_badge.habit_name = habit.name
            user_badge.habit_id = -1  # Remove habit reference but keep badge
        # Now delete the habit itself
        db.session.delete(habit)
        db.session.commit()

        flash('Habit deleted successfully!', 'success')
        return redirect(url_for('main.manage_habits'))

    return render_template('confirm_delete.html', habit=habit)


@main_bp.route('/edit_habit/<int:habit_id>', methods=['GET', 'POST'])
def edit_habit(habit_id):
    habit = Activity.query.get_or_404(habit_id)
    
    if habit.user_id != session.get('user_id'):
        flash("Unauthorized action!", "danger")
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        new_name = request.form.get('new_name').strip()
        if not new_name:
            flash("Habit name cannot be empty!", "warning")
            return redirect(url_for('main.edit_habit', habit_id=habit_id))

        habit.name = new_name
        db.session.commit()
        flash("Habit updated successfully!", "success")
        return redirect(url_for('main.dashboard'))

    return render_template('edit_habit.html', habit=habit)

@main_bp.route('/calendar')
def calendar():
    if 'user_id' not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for('main.login'))
    return render_template('calendar.html')

### FETCH ALL CALENDAR EVENTS FOR A USER ###
@main_bp.route('/calendar/<int:user_id>', methods=['GET'])
def get_calendar_events(user_id):
    """
    Get all calendar events (habits and notes) for a specific user.
    """
    events = CalendarEvent.query.filter_by(user_id=user_id).all()

    event_list = []
    for event in events:
        event_list.append({
            "id": event.id,
            "date": event.date.strftime("%Y-%m-%d"),
            "event_type": event.event_type,
            "habit_id": event.habit_id,
            "note": event.note
        })

    return jsonify({"events": event_list}), 200


### FETCH HABIT COMPLETION HISTORY ###
@main_bp.route('/calendar/habits/<int:user_id>', methods=['GET'])
def get_habit_history(user_id):
    """
    Get all habit completion records for a user.
    """
    habits = Activity.query.filter_by(user_id=user_id).all()

    habit_history = []
    for habit in habits:
        habit_history.append({
            "habit_id": habit.id,
            "name": habit.name,
            "last_completed": habit.last_completed.strftime("%Y-%m-%d") if habit.last_completed else None,
            "streak": habit.streak
        })

    return jsonify({"habit_history": habit_history}), 200


### ADD NOTES TO THE CALENDAR ###
@main_bp.route('/calendar/add_note', methods=['POST'])
def add_calendar_note():
    """
    Add a custom note to the user's calendar.
    """
    data = request.get_json()
    user_id = data.get("user_id")
    date_str = data.get("date")
    note = data.get("note")

    if not user_id or not date_str or not note:
        return jsonify({"error": "Missing required fields"}), 400

    # Convert string to date
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    new_note = CalendarEvent(user_id=user_id, date=date, event_type="note", note=note)
    db.session.add(new_note)
    db.session.commit()

    return jsonify({"message": "Note added successfully"}), 201