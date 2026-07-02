"""
Project 24. Weather Display - KMA Public Data Portal API version
Prerequisites:
  1. Apply for 'Ultra Short-term Forecast Service' at https://www.data.go.kr
  2. Enter your issued service key in SERVICE_KEY below
  3. pip install requests

Grid coordinate (NX, NY) reference:
  See: https://www.kma.go.kr/kma/info/neighborhoodInfo.jsp
  Gwangju Gwangsan-gu Songjeong-dong -> NX=57, NY=74
"""

import requests
import tkinter
import tkinter.font
from datetime import datetime

# ── Settings ──────────────────────────────────────────────────────────────────
SERVICE_KEY = "Enter_your_service_key_here"   # <- Required
NX = 57    # Grid X (Gwangju example)
NY = 74    # Grid Y
# Sejong: NX=66, NY=100
# Seoul:  NX=60, NY=127
# ─────────────────────────────────────────────────────────────────────────────

def get_base_time():
    """
    Calculate latest forecast base time (02, 05, 08, 11, 14, 17, 20, 23)
    Data becomes stable 10 min after release, so apply 10 min margin.
    """
    now = datetime.now()
    base_hours = [2, 5, 8, 11, 14, 17, 20, 23]
    cur_hour = now.hour if now.minute >= 10 else now.hour - 1
    valid = [h for h in base_hours if h <= cur_hour]
    if not valid:
        # Use last release time of previous day
        from datetime import timedelta
        now -= timedelta(days=1)
        return now.strftime("%Y%m%d"), "2300"
    bh = valid[-1]
    return now.strftime("%Y%m%d"), f"{bh:02d}00"


def fetch_weather():
    base_date, base_time = get_base_time()
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    params = {
        "serviceKey": SERVICE_KEY,
        "pageNo": "1",
        "numOfRows": "10",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": NX,
        "ny": NY,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    items = resp.json()["response"]["body"]["items"]["item"]

    result = {}
    for item in items:
        result[item["category"]] = item["obsrValue"]

    # T1H: temperature, REH: humidity, RN1: precipitation (1hr)
    temp = float(result.get("T1H", 0))
    humi = int(result.get("REH", 0))
    rain = result.get("RN1", "0")
    return temp, humi, rain


def tick1Min():
    try:
        temp, humi, rain = fetch_weather()
        rain_str = f"   Rain {rain}mm" if rain not in ("0", "No rain") else ""
        display = f"{temp:.1f}°C   Humi {humi}%{rain_str}"
        label.config(text=display, fg="#00BFFF")
    except Exception as e:
        label.config(text=f"Error: {e}", fg="red")
    window.after(60000, tick1Min)


# ── GUI ───────────────────────────────────────────────────────────────────────
window = tkinter.Tk()
window.title("TEMP HUMI DISPLAY")
window.geometry("660x110")
window.resizable(False, False)
window.configure(bg="#1a1a2e")

font_main  = tkinter.font.Font(family="Consolas", size=24, weight="bold")
font_title = tkinter.font.Font(family="Consolas", size=10)

title_label = tkinter.Label(
    window, text="KMA Live Weather",
    font=font_title, bg="#1a1a2e", fg="#888888"
)
title_label.pack(pady=(6, 0))

label = tkinter.Label(
    window, text="Loading...",
    font=font_main, bg="#1a1a2e", fg="#CCCCCC",
    wraplength=640, anchor="center"
)
label.pack(pady=4)

tick1Min()
window.mainloop()
