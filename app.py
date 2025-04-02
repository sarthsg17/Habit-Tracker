from flask import Flask, render_template
from config import Config
from models import db, Admin, User, Activity
from routes import main_bp
from flask_migrate import Migrate
from flask_mail import Mail, Message
from flask_apscheduler import APScheduler
from datetime import datetime
import pytz

# Initialize Flask App
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Database and Migration
db.init_app(app)
migrate = Migrate(app, db)  # Attach Flask-Migrate

# Initialize Mail
mail = Mail(app)

# Register Blueprints
app.register_blueprint(main_bp)

# Home Route for Testing
@app.route('/')
def home():
    return render_template('home.html')

# Scheduler Setup
scheduler = APScheduler()

def send_daily_report():
    with app.app_context():
        users = User.query.all()
        ist = pytz.timezone('Asia/Kolkata')
        today = datetime.now(ist).date()

        for user in users:
            habits = Activity.query.filter_by(user_id=user.id).all()
            
            completed_habits = [h.name for h in habits if h.last_completed and h.last_completed.date() == today]
            missed_habits = [h.name for h in habits if h.name not in completed_habits]  # Remaining habits are missed

            completed_count = len(completed_habits)
            missed_count = len(missed_habits)

            msg = Message("Your Habit Tracker Report",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[user.email])

            msg.body = (
                f"Hello {user.username},\n\n"
                f"You completed {completed_count} habits today and missed {missed_count}.\n\n"
                f"✅ Completed Habits:\n" +
                (", ".join(completed_habits) if completed_habits else "None") + "\n\n"
                f"❌ Missed Habits:\n" +
                (", ".join(missed_habits) if missed_habits else "None") + "\n"
                "Keep up the good work!"
            )

            mail.send(msg)


# Schedule the email job at 10 PM IST
scheduler.add_job(id="daily_email",
                  func=send_daily_report,
                  trigger="cron",
                  hour=22,
                  minute=00,
                  timezone="Asia/Kolkata")
scheduler.start()

if __name__ == '__main__':
    with app.app_context():
        Admin.create_default_admin()
        print("Admin account checked/created.")
    app.run(debug=True)
