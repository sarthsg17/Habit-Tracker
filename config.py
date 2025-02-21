import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')  # Change this in production
    SQLALCHEMY_DATABASE_URI = 'sqlite:///habit_tracker.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False