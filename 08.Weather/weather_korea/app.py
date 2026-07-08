"""
Korea Weather Map - Flask Backend
Uses Open-Meteo API (no API key required)
"""

from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)

# ── Major Korean cities ───────────────────────────────────────────────────────
CITIES = [
    {"name": "Seoul",    "name_kr": "서울",  "lat": 37.5665, "lon": 126.9780},
    {"name": "Incheon",  "name_kr": "인천",  "lat": 37.4563, "lon": 126.7052},
    {"name": "Daejeon",  "name_kr": "대전",  "lat": 36.3504, "lon": 127.3845},
    {"name": "Gwangju",  "name_kr": "광주",  "lat": 35.1595, "lon": 126.8526},
    {"name": "Daegu",    "name_kr": "대구",  "lat": 35.8714, "lon": 128.6014},
    {"name": "Busan",    "name_kr": "부산",  "lat": 35.1796, "lon": 129.0756},
]

def fetch_city_weather(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature"
        "&timezone=Asia%2FSeoul"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()["current"]
    return {
        "temp":  round(data["temperature_2m"], 1),
        "humi":  data["relative_humidity_2m"],
        "feels": round(data["apparent_temperature"], 1),
        "time":  data["time"],
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/weather")
def weather():
    results = []
    for city in CITIES:
        try:
            w = fetch_city_weather(city["lat"], city["lon"])
            results.append({**city, **w, "error": False})
        except Exception as e:
            results.append({**city, "error": True, "msg": str(e)})
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
