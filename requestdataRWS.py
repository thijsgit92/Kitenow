import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone

from meteostat import Point
from meteostat.hourly import Hourly
# =========================
# CONFIG
# =========================

st.set_page_config(page_title="KiteNow - Hoek van Holland", layout="centered")

# Hoek van Holland coordinates
LOCATION = Point(52.01, 4.12)

# =========================
# KNMI / METEOSTAT DATA
# =========================

def get_wind_data():
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    end = datetime.now(timezone.utc)

    data = Hourly(LOCATION, start, end)
    df = data.fetch()

    if df.empty:
        return None, None, None

    # Meteostat:
    # wspd = wind speed (km/h)
    # wdir = wind direction (degrees)
    # gust = wind gust (km/h)

    wind_speed_kmh = df["wspd"].iloc[-1]
    wind_dir = df["wdir"].iloc[-1]
    gust_kmh = df["wpgt"].iloc[-1] if "wpgt" in df.columns else None

    wind_speed_ms = wind_speed_kmh / 3.6 if wind_speed_kmh else None
    gust_ms = gust_kmh / 3.6 if gust_kmh else None

    return wind_speed_ms, wind_dir, gust_ms


# =========================
# KITE LOGIC
# =========================

def kite_status(speed, direction):
    if speed is None or direction is None:
        return "⚪ NO DATA"

    good_direction = (0 <= direction <= 50) or (230 <= direction <= 359)

    if speed > 8 and good_direction:
        return "🟢 GO KITESURF"
    elif speed > 6 and good_direction:
        return "🟠 BORDERLINE"
    else:
        return "🔴 NO GO"


def kite_score(speed, direction):
    if speed is None or direction is None:
        return 0

    score = 0

    # wind strength
    if 6 <= speed <= 14:
        score += 6
    elif speed > 14:
        score += 4
    else:
        score += 1

    # direction
    if (0 <= direction <= 50) or (230 <= direction <= 359):
        score += 4
    else:
        score += 1

    return min(score, 10)


# =========================
# UI HEADER
# =========================

st.title("🏄 KiteNow – Hoek van Holland")

st.caption("Live KNMI-backed wind data (via Meteostat)")

# =========================
# FETCH DATA
# =========================

speed, direction, gust = get_wind_data()

status = kite_status(speed, direction)
score = kite_score(speed, direction)

# =========================
# BIG CENTER DISPLAY
# =========================

st.markdown(
    f"""
    <div style="text-align:center; padding: 10px;">
        <h1>💨 {speed:.1f} m/s</h1>
        <h2>🧭 {direction:.0f}°</h2>
        <h2>{status}</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================
# METRICS
# =========================

col1, col2, col3 = st.columns(3)

col1.metric("Wind (m/s)", f"{speed:.1f}" if speed else "N/A")
col2.metric("Gust (m/s)", f"{gust:.1f}" if gust else "N/A")
col3.metric("Kite score", score)

# =========================
# SIMPLE HISTORY (SESSION ONLY)
# =========================

if "history" not in st.session_state:
    st.session_state.history = []

st.session_state.history.append({
    "time": datetime.now().strftime("%H:%M"),
    "speed": speed,
    "direction": direction
})

df = pd.DataFrame(st.session_state.history)

st.subheader("📈 Live trend (session)")
st.line_chart(df.set_index("time")["speed"])

# =========================
# REFRESH BUTTON
# =========================

st.button("🔄 Refresh")
