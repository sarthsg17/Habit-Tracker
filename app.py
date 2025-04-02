from flask import Flask, render_template
from config import Config
from models import db, Admin, User, Activity
from routes import main_bp
from flask_migrate import Migrate
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler

# Initialize Flask App
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Database and Migration
db.init_app(app)
migrate = Migrate(app, db)  # Attach Flask-Migrate

# Register Blueprints
app.register_blueprint(main_bp)

# Initialize Mail and Scheduler
mail = Mail(app)
scheduler = BackgroundScheduler()
scheduler.start()

# Schedule Jobs After App Context is Ready
with app.app_context():
    from email_tasks import schedule_jobs  # Import only after app is initialized
    schedule_jobs(app, mail, scheduler)
    Admin.create_default_admin()  # Create admin if not exists
    print("Admin account checked/created.")

# Home Route for Testing
@app.route('/')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True)
