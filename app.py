from flask import Flask, render_template
from config import Config
from models import db, Admin
from routes import main_bp
from flask_migrate import Migrate
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
import os
import atexit

# Initialize Flask App
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Database and Migration
db.init_app(app)
migrate = Migrate(app, db)

# Register Blueprints
app.register_blueprint(main_bp)

# Initialize Mail
mail = Mail(app)

# Initialize Scheduler only once
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    scheduler = BackgroundScheduler()
    scheduler.start()
    
    with app.app_context():
        from email_tasks import schedule_jobs
        schedule_jobs(app, mail, scheduler)
        Admin.create_default_admin()
        print("[INIT] Scheduler and admin setup complete")
    
    # Proper shutdown handler
    atexit.register(lambda: scheduler.shutdown())

# Home Route
@app.route('/')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)