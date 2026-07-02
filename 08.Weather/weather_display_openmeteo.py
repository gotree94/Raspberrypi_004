"""
Project 24. Weather Display - Open-Meteo version
No API key required, free, ready to use
Location: Gwangju (lat=35.1595, lon=126.8526)
Change LAT, LON values to use a different location.
"""

import requests
import tkinter
import tkinter.font

# ── Location settings (lat/lon) ───────────────────────────────────────────────
LAT = 35.1595   # Gwangju
LON = 126.8526

# Sejong: LAT=36.4800, LON=127.2890
# Seoul:  LAT=37.5665, LON=126.9780
# ─────────────────────────────────────────────────────────────────────────────

def fetch_weather():
    """
    Open-Meteo API call
    - temperature_2m      : temperature (C)
    - relative_humidity_2m: relative humidity (%)
    - apparent_temperature : feels-like temperature (C)
    """
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature"
        "&timezone=Asia%2FSeoul"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    current = data["current"]
    temp  = current["temperature_2m"]
    humi  = current["relative_humidity_2m"]
    feel  = current["apparent_temperature"]
    return temp, humi, feel


def tick1Min():
    try:
        temp, humi, feel = fetch_weather()
        display = f"{temp:.1f}°C   Humi {humi}%   Feels {feel:.1f}°C"
        label.config(text=display, fg="#00BFFF")
    except Exception as e:
        label.config(text=f"Error: {e}", fg="red")
    window.after(60000, tick1Min)   # refresh every 1 min


# ── GUI ───────────────────────────────────────────────────────────────────────
window = tkinter.Tk()
window.title("TEMP HUMI DISPLAY")
window.geometry("660x110")
window.resizable(False, False)
window.configure(bg="#1a1a2e")

# Font setup (Consolas for clean numeric display)
font_main  = tkinter.font.Font(family="Consolas", size=24, weight="bold")
font_title = tkinter.font.Font(family="Consolas", size=10)

title_label = tkinter.Label(
    window, text="Open-Meteo Live Weather",
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
