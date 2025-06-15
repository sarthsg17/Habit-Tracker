import pytz
from datetime import datetime, timedelta
from flask_mail import Message
from models import db, User, Activity
from sqlalchemy import func
from sqlalchemy import cast, Time

def send_habit_reminder(app, mail, scheduler):
    with app.app_context():
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist).replace(second=0, microsecond=0).time()
        now_date = datetime.now(ist).date()

        # PostgreSQL-compatible query
        habits = Activity.query.filter(
            cast(Activity.reminder_time, Time) == now
        ).distinct(Activity.id).all()

        for habit in habits:
            if habit.last_completed and habit.last_completed.date() == now_date:
                print(f"[DEBUG] Skipping reminder for {habit.name}, already completed today.")
                continue

            user = User.query.get(habit.user_id)
            if user:
                print(f"[DEBUG] Sending reminder to {user.email} for habit: {habit.name}")
                msg = Message(
                    "Habit Reminder",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[user.email]
                )
                msg.body = f"Hello {user.username},\n\nDon't forget to complete your habit: {habit.name}!\n\nStay consistent!"

                try:
                    mail.send(msg)
                    print("[SUCCESS] Email sent successfully!")
                except Exception as e:
                    print(f"[ERROR] Email failed to send: {str(e)}")
                # Ensure unique job ID for follow-up reminders
                # followup_job_id = f"followup_{habit.id}_{user.id}"
                # if not scheduler.get_job(followup_job_id):
                #     scheduler.add_job(
                #         id=followup_job_id,
                #         func=send_followup_reminder,
                #         trigger="date",
                #         run_date=datetime.now(ist) + timedelta(hours=3),
                #         kwargs={"app": app, "mail": mail, "habit_id": habit.id, "user_email": user.email, "username": user.username}
                #     )
                #     print(f"[DEBUG] Follow-up reminder scheduled for {habit.name} in 3 hours.")

# def send_followup_reminder(app, mail, habit_id, user_email, username):
#     with app.app_context():
#         ist = pytz.timezone('Asia/Kolkata')
#         now_date = datetime.now(ist).date()

#         habit = Activity.query.get(habit_id)
#         if habit and (not habit.last_completed or habit.last_completed.date() != now_date):
#             print(f"[DEBUG] Sending follow-up email to {user_email} for habit: {habit.name}")
#             msg = Message(
#                 "Still Not Completed!",
#                 sender=app.config['MAIL_USERNAME'],
#                 recipients=[user_email]
#             )
#             msg.body = f"Hello {username},\n\nYou still haven't completed your habit: {habit.name}.\n\nYou can do it now!"
            
#             try:
#                 mail.send(msg)
#                 print("[SUCCESS] Follow-up email sent successfully!")
#             except Exception as e:
#                 print(f"[ERROR] Follow-up email failed to send: {str(e)}")

def send_missed_habits_report(app, mail):
    with app.app_context():
        ist = pytz.timezone('Asia/Kolkata')
        today = datetime.now(ist).date()

        users = User.query.all()
        for user in users:
            missed_habits = [
                h.name for h in Activity.query.filter_by(user_id=user.id, status='active').all()
                if not h.last_completed or h.last_completed.date() != today
            ]

            if missed_habits:
                print(f"[DEBUG] Sending missed habit report to {user.email}")
                msg = Message(
                    "Missed Habit Report",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[user.email]
                )
                msg.body = (
                    f"Hello {user.username},\n\n"
                    "You missed the following habits today:\n" +
                    "\n".join(f"❌ {habit}" for habit in missed_habits) +
                    "\n\nTry to complete them tomorrow!"
                )

                try:
                    mail.send(msg)
                    print("[SUCCESS] Missed habit report sent successfully!")
                except Exception as e:
                    print(f"[ERROR] Failed to send missed habit report: {str(e)}")

def schedule_jobs(app, mail, scheduler):
    try:
        # Only try to remove jobs if they exist
        if scheduler.get_job("habit_reminders"):
            scheduler.remove_job("habit_reminders")
        if scheduler.get_job("missed_habits_report"):
            scheduler.remove_job("missed_habits_report")
    except Exception as e:
        print(f"[INFO] No existing jobs to remove: {str(e)}")

    # Add jobs with coalesce=True and max_instances=1
    scheduler.add_job(
        id="habit_reminders",
        func=send_habit_reminder,
        trigger="cron",
        minute="*",
        timezone="Asia/Kolkata",
        args=[app, mail, scheduler],
        coalesce=True,
        max_instances=1,
        replace_existing=True  # This will handle cases where job exists
    )
    
    scheduler.add_job(
        id="missed_habits_report",
        func=send_missed_habits_report,
        trigger="cron",
        hour=21,
        minute=17,
        timezone="Asia/Kolkata",
        args=[app, mail],
        coalesce=True,
        max_instances=1,
        replace_existing=True
    )
    print("[INFO] Jobs scheduled successfully")
