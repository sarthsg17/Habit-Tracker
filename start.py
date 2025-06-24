# start.py
import threading
import subprocess
from cron_task import keep_alive

# Start pinging in a background thread
threading.Thread(target=keep_alive, daemon=True).start()

# Start your app with Gunicorn
subprocess.call(["gunicorn", "app:app"])
