from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Store hashed password

    # Set password method
    def set_password(self, password):
        """Hashes the password and stores it"""
        self.password_hash = generate_password_hash(password)

    # Check password method
    def check_password(self, password):
        """Verifies if the entered password matches the stored hash"""
        return check_password_hash(self.password_hash, password)


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    streak = db.Column(db.Integer, default=0)
    last_completed = db.Column(db.DateTime)

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
