from flask import Flask 
from models import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habit_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Create a route for testing
@app.route('/')
def home():
    return "Habit Tracker App"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables based on models
        print("Database and tables created!")
    app.run(debug=True)
