# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests>=2.32"
# ]
# ///
import os
import sys
import requests
import urllib3
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configs
CWA_API_KEY = os.environ.get("CWA_API_KEY")
TG_TOKEN = os.environ.get("WEATHER_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("CHAT_ID")

LOCATION_NAME = os.environ.get("LOCATION_NAME", "\u5167\u6e56\u5340")
OBS_STATION_ID = os.environ.get("OBS_STATION_ID", "C0A9F0")
WORK_START = int(os.environ.get("WORK_START", 7))
WORK_END = int(os.environ.get("WORK_END", 18))

FORECAST_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-061"
HISTORY_META_URL = "https://opendata.cwa.gov.tw/historyapi/v1/getMetadata/O-A0001-001"
OBS_NS = "urn:cwa:gov:tw:cwacommon:0.1"


def fetch_today_observed(target_date):
    meta_r = requests.get(HISTORY_META_URL, params={"Authorization": CWA_API_KEY}, verify=False)
    meta_r.raise_for_status()
    times = meta_r.json()["dataset"]["resources"]["resource"]["data"]["time"]

    tz_taipei = timezone(timedelta(hours=8))
    work_snapshots = []
    
    for t in times:
        try:
            local_dt = datetime.fromisoformat(t["DateTime"]).astimezone(tz_taipei)
            if local_dt.date() == target_date and WORK_START <= local_dt.hour < WORK_END:
                work_snapshots.append((local_dt, t["ProductURL"]))
        except (ValueError, TypeError):
            continue

    if not work_snapshots:
        return None

    readings = []
    nt = lambda tag: f"{{{OBS_NS}}}{tag}"
    
    for snap_dt, url in work_snapshots:
        try:
            r = requests.get(url, timeout=15, verify=False)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            
            station = next((s for s in root.iter(nt("Station")) 
                          if (s.findtext(nt("StationId")) or "").strip() == OBS_STATION_ID), None)
            if not station:
                continue
                
            temp_str = station.findtext(f".//{nt('AirTemperature')}")
            if temp_str and temp_str != "-99":
                readings.append((snap_dt, float(temp_str)))
        except Exception:
            continue

    if not readings:
        return None

    return {
        "max": max(readings, key=lambda x: x[1]),
        "min": min(readings, key=lambda x: x[1]),
    }


def fetch_forecast(target_date):
    r = requests.get(FORECAST_URL, params={
        "Authorization": CWA_API_KEY,
        "locationName": LOCATION_NAME,
        "elementName": "\u6eab\u5ea6",
        "format": "JSON",
    }, verify=False)
    r.raise_for_status()

    try:
        records = r.json()["records"]
        loc_wrap = records.get("Locations", records.get("locations", []))[0]
        loc = loc_wrap.get("Location", loc_wrap.get("location", []))[0]
        elements = loc.get("weatherElement", loc.get("WeatherElement", []))

        t_elem = next(e for e in elements if e.get("elementName", e.get("ElementName")) in ("T", "\u6eab\u5ea6"))
        time_list = t_elem.get("Time", t_elem.get("time", []))

        series = []
        for ts in time_list:
            start_str = ts.get("DataTime", ts.get("startTime", ts.get("StartTime", "")))
            ev = ts.get("ElementValue", ts.get("elementValue", []))
            
            if not start_str or not ev:
                continue
                
            dt = datetime.fromisoformat(start_str)
            temp = float(ev[0].get("Temperature", ev[0].get("value", ev[0].get("Value"))))
            
            if dt.date() == target_date and WORK_START <= dt.hour < WORK_END:
                series.append((dt, temp))

        if not series:
            return None

        return {
            "max": max(series, key=lambda x: x[1]),
            "min": min(series, key=lambda x: x[1]),
        }
    except Exception as e:
        print(f"Forecast parse error: {e}")
        return None


def build_message():
    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    today_data = fetch_today_observed(today)
    tomorrow_data = fetch_forecast(tomorrow)

    lines = [
        f"\U0001F321\uFE0F Weather Report",
        f"Work Hours: {WORK_START:02d}:00 - {WORK_END:02d}:00",
        ""
    ]

    lines.append(f"Today {today.strftime('%m/%d (%a)')} (Observed):")
    if today_data:
        lines.append(f"  Max: {today_data['max'][1]:.1f}°C at {today_data['max'][0].strftime('%H:%M')}")
        lines.append(f"  Min: {today_data['min'][1]:.1f}°C at {today_data['min'][0].strftime('%H:%M')}")
    else:
        lines.append("  No data available")

    lines.append("")
    lines.append(f"Tomorrow {tomorrow.strftime('%m/%d (%a)')} (Forecast):")
    if tomorrow_data:
        lines.append(f"  Max: {tomorrow_data['max'][1]:.1f}°C at {tomorrow_data['max'][0].strftime('%H:%M')}")
        lines.append(f"  Min: {tomorrow_data['min'][1]:.1f}°C at {tomorrow_data['min'][0].strftime('%H:%M')}")
    else:
        lines.append("  No data available")

    return "\n".join(lines)


def job():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running weather notification...")
    try:
        msg = build_message()
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TG_CHAT_ID, "text": msg}, timeout=10)
        r.raise_for_status()
        print("Success")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Weather Bot: Fetches CWA API data and sends Telegram notifications.")
        sys.exit(0)
        
    job()

