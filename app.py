from flask import Flask, render_template
from config import Config
from models import db, Admin
from routes import main_bp

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

app.register_blueprint(main_bp)

# Create a route for testing
@app.route('/')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables based on models
        Admin.create_default_admin()
        print("Database and tables created!")
    app.run(debug=True)
