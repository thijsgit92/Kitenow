import streamlit as st
import requests
from datetime import datetime

# =========================
# CONFIG
# =========================

st.set_page_config(page_title="KiteNow Intelligence", layout="centered")

LAT = 52.01
LON = 4.12

# =========================
# FETCH FORECAST (OPEN-METEO)
# =========================

def get_forecast():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}"
        f"&longitude={LON}"
        "&hourly=windspeed_10m,winddirection_10m,windgusts_10m"
        "&forecast_days=1"
        "&timezone=UTC"
    )

    r = requests.get(url, timeout=10)
    data = r.json()

    return data["hourly"]


# =========================
# GUST FACTOR (SAFETY)
# =========================

def gust_factor(speed, gust):
    if speed is None or gust is None or speed == 0:
        return 0

    return gust / speed  # ratio


def gust_risk_label(gf):
    if gf < 1.2:
        return "🟢 Stable"
    elif gf < 1.5:
        return "🟠 Gusty"
    else:
        return "🔴 Dangerous"


# =========================
# WIND TREND
# =========================

def wind_trend(speeds):
    if len(speeds) < 3:
        return "⚪ Unknown"

    recent = speeds[-3:]

    if recent[-1] > recent[0] + 1:
        return "📈 Increasing"
    elif recent[-1] < recent[0] - 1:
        return "📉 Decreasing"
    else:
        return "➡ Stable"


# =========================
# BEST 2-HOUR WINDOW
# =========================

def find_best_window(hourly):
    speeds = hourly["windspeed_10m"]

    best_score = 0
    best_start = 0

    # 2-hour sliding window
    for i in range(len(speeds) - 2):
        window = speeds[i:i+2]

        avg = sum(window) / 2

        # scoring function (simple but effective)
        score = 0
        if 6 <= avg <= 14:
            score += avg
        if min(window) > 5:
            score += 3

        if score > best_score:
            best_score = score
            best_start = i

    return best_start


# =========================
# CURRENT DATA
# =========================

hourly = get_forecast()

speeds = hourly["windspeed_10m"]
dirs = hourly["winddirection_10m"]
gusts = hourly["windgusts_10m"]
times = hourly["time"]

current_speed = speeds[0] / 3.6
current_dir = dirs[0]
current_gust = gusts[0] / 3.6

gf = gust_factor(current_speed, current_gust)

trend = wind_trend([s / 3.6 for s in speeds[:6]])

best_start = find_best_window(hourly)

# =========================
# UI HEADER
# =========================

st.title("🏄 KiteNow Intelligence")
st.caption("Wind + gust safety + session prediction")

# =========================
# CURRENT CONDITIONS
# =========================

st.markdown(
    f"""
    <div style="text-align:center;">
        <h1>💨 {current_speed:.1f} m/s</h1>
        <h2>🧭 {current_dir:.0f}°</h2>
        <h3>{gust_risk_label(gf)} (GF {gf:.2f})</h3>
        <h3>{trend}</h3>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================
# BEST WINDOW
# =========================

st.subheader("🌊 Best 2-hour kite window")

start_time = times[best_start]
end_time = times[best_start + 2]

st.success(
    f"Best window: {start_time} → {end_time}"
)

# =========================
# SIMPLE INSIGHT ENGINE
# =========================

if gf > 1.5:
    st.error("⚠️ High gust variability — risky for beginners")
elif current_speed > 8 and 0.8 < gf < 1.4:
    st.success("🔥 Ideal kite conditions NOW")
else:
    st.info("🌤 Wait or monitor conditions")

# =========================
# REFRESH
# =========================

if st.button("🔄 Refresh"):
    st.rerun()
