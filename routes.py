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

    # Call reset streaks before fetching habits
    
    return render_template('dashboard.html', username=session['username'])


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

@main_bp.route('/fetch-habits')
def fetch_habits():
    if 'user_id' not in session:
        flash("Please log in to view your habits.", "danger")
        return redirect(url_for('main.login'))

    # Fetch habits for the logged-in user
    habits = Activity.query.filter_by(user_id=session['user_id']).all()
    
    return render_template('manage_activities.html', activities=habits)


@main_bp.route('/complete_habit/<int:habit_id>', methods=['POST'])
def complete_habit(habit_id):
    habit = Activity.query.get(habit_id)
    if not habit:
        flash("Habit not found!", "error")
        return redirect(url_for('main.dashboard'))

    today = datetime.now(timezone.utc).date()
    print(f"Completing habit: {habit.name}, Last Completed: {habit.last_completed}, Current Streak: {habit.streak}")

    if habit.last_completed:
        last_date = habit.last_completed.date()

        if last_date == today:
            print("Already completed today, no changes.")
            flash("You already completed this habit today!", "info")
            return redirect(url_for('main.dashboard'))

        if last_date == today - timedelta(days=1):
            habit.streak += 1  # Increase streak
            print(f"🔥 Streak increased to: {habit.streak}")
        else:
            habit.streak = 1  # Reset streak if a day is missed
            print("❌ Missed a day, streak reset to 1")
    else:
        habit.streak = 1  # First-time completion
        print("✅ First completion, streak set to 1")

    habit.last_completed = datetime.now(timezone.utc)

    db.session.add(habit)  # Ensure it's tracked
    db.session.commit()
    db.session.refresh(habit)  # Force refresh from DB

    print(f"✅ Updated: Streak = {habit.streak}, Last Completed = {habit.last_completed}")

    return redirect(url_for('main.dashboard'))

def reset_streaks():
    with current_app.app_context():
        today = datetime.now(timezone.utc).date()
        habits = Activity.query.all()

        for habit in habits:
            if habit.last_completed:
                last_completed_date = habit.last_completed.date()
                
                # Reset streak if the habit wasn't completed yesterday
                if last_completed_date < (today - timedelta(days=1)):
                    habit.streak = 0
                    db.session.commit()

@main_bp.route('/confirm_delete/<int:habit_id>', methods=['GET', 'POST'])
def confirm_delete(habit_id):
    if 'user_id' not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for('main.login'))
    
    habit = Activity.query.get_or_404(habit_id)
    if habit.user_id != session['user_id']:
        flash("Unauthorized action!", "danger")
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        # If the user confirms deletion
        db.session.delete(habit)
        db.session.commit()
        flash("Habit deleted successfully!", "success")
        return redirect(url_for('main.dashboard'))
    
    # GET: Render a confirmation page
    return render_template('confirm_delete.html', habit=habit)

@main_bp.route('/edit_habit/<int:habit_id>', methods=['GET', 'POST'])
def edit_habit(habit_id):
    if 'user_id' not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for('main.login'))
    
    habit = Activity.query.get_or_404(habit_id)
    if habit.user_id != session['user_id']:
        flash("Unauthorized action!", "danger")
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        new_name = request.form.get('new_name')
        if new_name:
            habit.name = new_name  # Only updating the name, leaving streak intact.
            db.session.commit()
            flash("Habit updated successfully!", "success")
        else:
            flash("Habit name cannot be empty.", "danger")
        return redirect(url_for('main.dashboard'))
    
    return render_template('edit_habit.html', habit=habit)

@main_bp.route('/manage-habits')
def manage_habits():
    if 'user_id' not in session:
        flash("Please log in to view your habits.", "danger")
        return redirect(url_for('main.login'))

    user_id = session['user_id']
    habits = Activity.query.filter_by(user_id=user_id).all()

    if not habits:
        print("No habits found for this user.")  # Debugging output

    return render_template('manage_habits.html', activities=habits)

