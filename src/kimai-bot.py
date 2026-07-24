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

def fmt_overtime(ot_sec):
    sign = "-" if ot_sec < 0 else "+"
    total_min = int(abs(ot_sec) // 60)
    h, m = divmod(total_min, 60)
    if h > 0:
        return f"{sign}{h}h{m:02d}m"
    return f"{sign}{m}m"

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

    # Skip sending report if daily work time is 0
    if mode == "daily" and work_seconds == 0:
        print("No work logged today. Report skipped.")
        return
            
    report = f"{title}\n\n"
    for pname, dur in summary.items():
        report += f"- {pname}: {dur/3600:.2f}h\n"
        
    if mode == "weekly":
        # Per-day overtime breakdown
        DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        DAILY_EXPECTED = 28800  # 8 hours
        monday = now - timedelta(days=now.weekday())

        day_work = {}
        for e in entries:
            dur = e.get("duration", 0)
            pid = e.get("project")
            pname = projects.get(pid, f"Project {pid}")
            if pname in non_work_projects:
                continue
            try:
                entry_dt = datetime.fromisoformat(e.get("begin", ""))
            except (ValueError, TypeError):
                continue
            day_idx = entry_dt.weekday()
            day_work[day_idx] = day_work.get(day_idx, 0) + dur

        report += "\n*Daily Overtime:*\n"
        for i in range(now.weekday() + 1):
            day_date = (monday + timedelta(days=i)).strftime("%m/%d")
            ot = day_work.get(i, 0) - DAILY_EXPECTED
            report += f"  {DAY_NAMES[i]} {day_date}: {fmt_overtime(ot)}\n"

    ot_sec = work_seconds - expected_sec
    ot_str = fmt_overtime(ot_sec)

    report += f"\n*Total Logged:* {total_seconds/3600:.2f}h"
    report += f"\n*Overtime:* {ot_str}"
    
    send_telegram(report)
    print(f"Successfully sent {mode} report.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Kimai Report Bot: Generates timesheet summaries and sends Telegram reports.")
        print("Usage: uv run src/kimai-report.py [daily|weekly]")
        sys.exit(0)
        
    if len(sys.argv) < 2 or sys.argv[1] not in ["daily", "weekly"]:
        print("Usage: uv run src/kimai-report.py [daily|weekly]")
        sys.exit(1)
        
    generate_report(sys.argv[1])
