# cron_task.py
import requests
import time

def keep_alive():
    url = "https://habit-tracker-lytx.onrender.com/"  # ✅ replace with your deployed URL
    headers = {"User-Agent": "BugnBuild-Cron"}
    while True:
        try:
            res = requests.get(url, headers=headers)
            print(f"[CRON] Pinged: {url} | Status: {res.status_code}")
        except Exception as e:
            print(f"[CRON ERROR] {e}")
        time.sleep(240)  # wait 4 minutes
