# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests>=2.34.2",
# ]
# ///
import os
import sys
import requests
from datetime import datetime, timedelta

# Configuration from .env
KIMAI_URL = os.environ.get("KIMAI_URL")
KIMAI_TOKEN = os.environ.get("KIMAI_TOKEN")
TG_TOKEN = os.environ.get("KIMAI_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("CHAT_ID")

def get_headers():
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {KIMAI_TOKEN}"
    }

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"})

def get_user_id():
    res = requests.get(f"{KIMAI_URL}/api/users/me", headers=get_headers())
    return res.json().get("id")

def get_timesheets(user_id, begin, end):
    params = {"user": user_id, "begin": begin, "end": end}
    res = requests.get(f"{KIMAI_URL}/api/timesheets", headers=get_headers(), params=params)
    return res.json() if res.status_code == 200 else []

def get_projects():
    res = requests.get(f"{KIMAI_URL}/api/projects", headers=get_headers())
    return {p["id"]: p["name"] for p in res.json()} if res.status_code == 200 else {}

def generate_report(mode):
    user_id = get_user_id()
    now = datetime.now()
    
    if mode == "daily":
        begin_dt = now.replace(hour=0, minute=0, second=0)
        expected_sec = 28800  # 8 hours
        title = "🔔 *Daily Report*"
    elif mode == "weekly":
        monday = now - timedelta(days=now.weekday())
        begin_dt = monday.replace(hour=0, minute=0, second=0)
        expected_sec = 144000  # 40 hours
        title = "📊 *Weekly Report*"
    else:
        return

    begin = begin_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end = now.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%dT%H:%M:%S")
    
    entries = get_timesheets(user_id, begin, end)
    projects = get_projects()
    
    summary = {}
    total_seconds = 0
    work_seconds = 0
    non_work_projects = {"Commute", "Break Time"}
    
    for e in entries:
        dur = e.get("duration", 0)
        pid = e.get("project")
        pname = projects.get(pid, f"Project {pid}")
        
        summary[pname] = summary.get(pname, 0) + dur
        total_seconds += dur
        
        if pname not in non_work_projects:
            work_seconds += dur
            
    report = f"{title}\n\n"
    for pname, dur in summary.items():
        report += f"- {pname}: {dur/3600:.2f}h\n"
        
    ot_sec = work_seconds - expected_sec
    ot_str = f"{'-' if ot_sec < 0 else ''}{int(abs(ot_sec) // 60)}m ({abs(ot_sec) / 3600:.1f}h)"
        
    report += f"\n*Total Logged:* {total_seconds/3600:.2f}h"
    report += f"\n*Overtime:* {ot_str}"
    
    send_telegram(report)
    print(f"Successfully sent {mode} report.")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ["daily", "weekly"]:
        print("Usage: uv run src/kimai-report.py [daily|weekly]")
        sys.exit(1)
        
    generate_report(sys.argv[1])
