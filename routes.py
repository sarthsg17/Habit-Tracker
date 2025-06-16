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

    # Escape descriptions for JavaScript and link habits
    for badge in user_badges:
        badge.badge.name_escaped = json.dumps(badge.badge.name)
        badge.badge.description_escaped = json.dumps(badge.badge.description)
        badge.habit = Activity.query.get(badge.habit_id)

    # Group badges by streak requirement
    streak_groups = {
        360: [],
        180: [],
        30: [],
        7: [],
        1: []
    }

    for badge in user_badges:
        if badge.badge and badge.badge.streak_required:
            if badge.badge.streak_required in streak_groups:
                streak_groups[badge.badge.streak_required].append(badge)

    # Sort streak groups by highest streak first
    sorted_streak_groups = {
        k: streak_groups[k] for k in sorted(streak_groups.keys(), reverse=True)
    }

    return render_template(
        'badges.html',
        username=session['username'],
        streak_groups=sorted_streak_groups
    )


# Add a New Habit
@main_bp.route('/add_habit', methods=['POST'])
def add_habit():
    if 'user_id' not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for('main.login'))

    habit_name = request.form.get('habit_name')
    reminder_time_str = request.form.get('reminder_time')  # Get time input as string

    if not habit_name:
        flash("Habit name cannot be empty.", "danger")
        return redirect(url_for('main.dashboard'))

    # Convert string input to Python time object
    reminder_time = None
    if reminder_time_str:
        try:
            reminder_time = datetime.strptime(reminder_time_str, "%H:%M").time()
        except ValueError:
            flash("Invalid time format!", "danger")
            return redirect(url_for('main.dashboard'))

    # Create new habit
    new_habit = Activity(name=habit_name, reminder_time=reminder_time, user_id=session['user_id'])
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
    habits = Activity.query.filter(Activity.user_id == user_id, Activity.status == "active").all()

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
        return redirect(url_for('main.manage_habits'))

    # Update streak
    if habit.last_completed and habit.last_completed.date() == today - timedelta(days=1):
        habit.streak += 1
        habit.days_completed += 1
    else:
        habit.streak = 1
        habit.days_completed += 1
    
    if habit.streak > habit.highest_streak:
            habit.highest_streak = habit.streak

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
    return redirect(url_for('main.manage_habits'))

@main_bp.route('/habit-history')
def habit_history():
    if 'user_id' not in session:
        flash("Please log in to view your habit history.", "danger")
        return redirect(url_for('main.login'))

    user_id = session['user_id']
    habits = Activity.query.filter_by(user_id=user_id).all()

    return render_template('habit_history.html', habits=habits)


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
            user_badge.habit_id = None  # ✅ Set to None instead of -1 to avoid FK violation

        # Now delete the habit itself (soft delete)
        if habit:
            habit.status = "deleted"
        
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
        new_name = request.form.get('new_name', '').strip()
        reminder_time_str = request.form.get('reminder_time', '').strip()

        if not new_name:
            flash("Habit name cannot be empty!", "warning")
            return redirect(url_for('main.edit_habit', habit_id=habit_id))

        # Validate and update reminder time if provided
        if reminder_time_str:
            try:
                reminder_time = datetime.strptime(reminder_time_str, "%H:%M").time()
                habit.reminder_time = reminder_time
            except ValueError:
                flash("Invalid time format! Use HH:MM.", "danger")
                return redirect(url_for('main.edit_habit', habit_id=habit_id))

        habit.name = new_name
        db.session.commit()
        flash("Habit updated successfully!", "success")
        return redirect(url_for('main.dashboard'))

    return render_template('edit_habit.html', habit=habit)


### DISPLAY CALENDAR PAGE ###
@main_bp.route('/calendar')
def calendar():
    if 'user_id' not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for('main.login'))
    return render_template('calendar.html')


### FETCH USER-SPECIFIC CALENDAR EVENTS ###
@main_bp.route('/calendar/events', methods=['GET'])
def get_calendar_events():
    """
    Fetch all calendar events (completed habits and notes) for the logged-in user.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session['user_id']

    # Fetch calendar notes
    events = CalendarEvent.query.filter_by(user_id=user_id).all()

    # Fetch user habits
    habits = Activity.query.filter_by(user_id=user_id).all()

    event_list = []

    # Add notes to the event list
    for event in events:
        event_list.append({
            "id": event.id,
            "date": event.date.strftime("%Y-%m-%d"),
            "event_type": event.event_type,
            "habit_id": event.habit_id,
            "note": event.note
        })

    # Add habits to the event list (for date added and last completed)
    for habit in habits:
        # Add event for habit creation date
        event_list.append({
            "id": habit.id,
            "date": habit.date_added.strftime("%Y-%m-%d"),
            "event_type": "habit_added",
            "habit_name": habit.name,
            "streak": habit.streak
        })

        # Add event for last completed date (if any)
        if habit.last_completed:
            event_list.append({
                "id": habit.id,
                "date": habit.last_completed.strftime("%Y-%m-%d"),
                "event_type": "habit_completed",
                "habit_name": habit.name,
                "streak": habit.streak
            })

    return jsonify({"events": event_list}), 200



### FETCH USER-SPECIFIC HABIT HISTORY ###
@main_bp.route('/calendar/habits', methods=['GET'])
def get_habit_history():
    """
    Get all habit completion records for the logged-in user.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session['user_id']
    habits = Activity.query.filter_by(user_id=user_id).all()

    habit_history = [
        {
            "habit_id": habit.id,
            "name": habit.name,
            "last_completed": habit.last_completed.strftime("%Y-%m-%d") if habit.last_completed else None,
            "streak": habit.streak
        }
        for habit in habits
    ]

    return jsonify({"habit_history": habit_history}), 200


### ADD NOTE TO CALENDAR ###
@main_bp.route('/calendar/add_note', methods=['POST'])
def add_calendar_note():
    """
    Add a user-specific note to the calendar.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    date_str = data.get("date")
    note = data.get("note")

    if not date_str or not note:
        return jsonify({"error": "Missing required fields"}), 400

    # Convert string to date
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    user_id = session['user_id']
    new_note = CalendarEvent(user_id=user_id, date=date, event_type="note", note=note)
    db.session.add(new_note)
    db.session.commit()

    return jsonify({"message": "Note added successfully"}), 201


### EDIT EXISTING NOTE ###
@main_bp.route('/calendar/edit_note/<int:note_id>', methods=['PUT'])
def edit_calendar_note(note_id):
    """
    Edit an existing note for the logged-in user.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session['user_id']
    note = CalendarEvent.query.filter_by(id=note_id, user_id=user_id, event_type="note").first()

    if not note:
        return jsonify({"error": "Note not found"}), 404

    data = request.get_json()
    updated_note = data.get("note")

    if not updated_note:
        return jsonify({"error": "Note content is required"}), 400

    note.note = updated_note
    db.session.commit()

    return jsonify({"message": "Note updated successfully"}), 200


### DELETE A NOTE ###
@main_bp.route('/calendar/delete_note/<int:note_id>', methods=['DELETE'])
def delete_calendar_note(note_id):
    """
    Delete a note for the logged-in user.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session['user_id']
    note = CalendarEvent.query.filter_by(id=note_id, user_id=user_id, event_type="note").first()

    if not note:
        return jsonify({"error": "Note not found"}), 404

    db.session.delete(note)
    db.session.commit()

    return jsonify({"message": "Note deleted successfully"}), 200

@main_bp.route('/calendar/events_by_date', methods=['GET'])
def get_events_by_date():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session['user_id']
    selected_date = request.args.get('date')  # Get the date from the request

    # Fetch notes for the selected date
    events = CalendarEvent.query.filter_by(user_id=user_id, date=selected_date).all()

    # Fetch habits for the selected date
    habits = Activity.query.filter_by(user_id=user_id).all()

    event_list = []

    # Add notes to the list
    for event in events:
        event_list.append({
            "id": event.id,
            "date": event.date.strftime("%Y-%m-%d"),
            "event_type": event.event_type,
            "habit_id": event.habit_id,
            "note": event.note
        })

    # Add habits that were added or completed on the selected date
    for habit in habits:
        if habit.date_added.strftime("%Y-%m-%d") == selected_date:
            event_list.append({
                "id": habit.id,
                "date": habit.date_added.strftime("%Y-%m-%d"),
                "event_type": "habit_added",
                "habit_name": habit.name,
                "streak": habit.streak
            })
        if habit.last_completed and habit.last_completed.strftime("%Y-%m-%d") == selected_date:
            event_list.append({
                "id": habit.id,
                "date": habit.last_completed.strftime("%Y-%m-%d"),
                "event_type": "habit_completed",
                "habit_name": habit.name,
                "streak": habit.streak
            })

    return jsonify({"events": event_list}), 200

@main_bp.route('/update_reminder/<int:habit_id>', methods=['POST'])
def update_reminder(habit_id):
    habit = Activity.query.get_or_404(habit_id)

    if habit.user_id != session.get('user_id'):
        flash("Unauthorized action!", "danger")
        return redirect(url_for('main.dashboard'))

    reminder_time_str = request.form.get('reminder_time', '').strip()

    if not reminder_time_str:
        flash("Reminder time cannot be empty!", "warning")
        return redirect(url_for('main.dashboard'))

    try:
        reminder_time = datetime.strptime(reminder_time_str, "%H:%M").time()
        habit.reminder_time = reminder_time
        db.session.commit()
        flash("Reminder time updated successfully!", "success")
    except ValueError:
        flash("Invalid time format! Use HH:MM.", "danger")

    return redirect(url_for('main.dashboard'))
