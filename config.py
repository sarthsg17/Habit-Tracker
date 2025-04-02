import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')  # Change this in production
    SQLALCHEMY_DATABASE_URI = 'sqlite:///habit_tracker.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = 'filesystem'

    # Flask-Mail Configuration
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'ashande29@gmail.com'
    MAIL_PASSWORD = 'yequetiqbwqyztyc'
    MAIL_DEFAULT_SENDER = 'ashande29@gmail.com'
    MAIL_USE_SSL = False