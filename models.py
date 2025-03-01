from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)  # Ensure password column exists

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    streak = db.Column(db.Integer, default=0)
    last_completed = db.Column(db.DateTime, default=None)
    def complete_habit(self):
        today = datetime.now(timezone.utc).date()

        if self.last_completed and self.last_completed.date() == today:
            return  # Already completed today

        if self.last_completed and self.last_completed.date() == (today - timedelta(days=1)):
            self.streak += 1  # Increment streak if completed consecutively
        else:
            self.streak = 1  # Reset streak if a day is missed

        self.last_completed = datetime.now(timezone.utc)
        db.session.commit()

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))