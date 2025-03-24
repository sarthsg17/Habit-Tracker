from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone

db = SQLAlchemy()

### USER MODEL ###
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)  # Ensure password column exists

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


### HABIT MODEL (Activity) ###
class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    streak = db.Column(db.Integer, default=0)
    last_completed = db.Column(db.DateTime, default=None)
    date_added = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(10), default='active')

    def complete_habit(self):
        today = datetime.now(timezone.utc).date()

        # Prevent multiple completions in one day
        if self.last_completed and self.last_completed.date() == today:
            return  

        # If completed yesterday, increment streak
        if self.last_completed and self.last_completed.date() == (today - timedelta(days=1)):
            self.streak += 1
        else:
            self.streak = 1  # Reset streak if a day is missed

        self.last_completed = datetime.now(timezone.utc)
        db.session.commit()

        # Award badge if conditions match
        self.check_and_award_badges()

    def check_and_award_badges(self):
        badges = Badge.query.filter(Badge.streak_required == self.streak).all()
        for badge in badges:
            existing_badge = UserBadge.query.filter_by(user_id=self.user_id, habit_id=self.id, badge_id=badge.id).first()
            if not existing_badge:  # Avoid duplicate badge
                new_user_badge = UserBadge(user_id=self.user_id, habit_id=self.id, badge_id=badge.id)
                db.session.add(new_user_badge)
                db.session.commit()

### CALENDAR EVENT MODEL ###
class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  # "habit" or "note"
    habit_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=True)  # Link to habits
    note = db.Column(db.Text, nullable=True)  # Allow users to add custom notes
    user = db.relationship('User', backref=db.backref('calendar_notes', lazy=True))

### BADGE MODEL (Created by Admin) ###
class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # Badge name
    description = db.Column(db.Text, nullable=True)  # Description
    streak_required = db.Column(db.Integer, nullable=False)  # Streak condition
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image_filename = db.Column(db.String(255), nullable=False)


### USER BADGE MODEL (Tracks Earned Badges) ###
class UserBadge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    habit_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)
    habit_name = db.Column(db.String(100))  # New column to store habit name
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=False)
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('earned_badges', lazy=True))
    badge = db.relationship('Badge', backref=db.backref('awarded_to', lazy=True))


### ADMIN MODEL ###
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, default="admin")
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def create_default_admin():
        admin = Admin.query.filter_by(username="admin").first()
        if not admin:
            hashed_password = generate_password_hash("admin")  # Default password is 'admin'
            new_admin = Admin(username="admin", password_hash=hashed_password)
            db.session.add(new_admin)
            db.session.commit()
