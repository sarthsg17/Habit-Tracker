from flask import Flask, render_template
from config import Config
from models import db, Admin
from routes import main_bp
from flask_migrate import Migrate

# Initialize Flask App
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Database and Migration
db.init_app(app)
migrate = Migrate(app, db)  # Attach Flask-Migrate

# Register Blueprints
app.register_blueprint(main_bp)

# Home Route for Testing
@app.route('/')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    with app.app_context():
        # Only create the default admin if it doesn’t exist
        Admin.create_default_admin()
        print("Admin account checked/created.")
    app.run(debug=True)
