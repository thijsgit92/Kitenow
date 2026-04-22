import streamlit as st
import requests
from datetime import datetime

# =========================
# CONFIG
# =========================

st.set_page_config(page_title="KiteNow - Hoek van Holland", layout="centered")

LAT = 52.01
LON = 4.12

# =========================
# FETCH WIND DATA (OPEN-METEO)
# =========================

def get_wind():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}"
        f"&longitude={LON}"
        "&hourly=windspeed_10m,winddirection_10m"
        "&forecast_days=1"
        "&timezone=UTC"
    )

    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        speed_kmh = data["hourly"]["windspeed_10m"][0]
        direction = data["hourly"]["winddirection_10m"][0]

        speed_ms = speed_kmh / 3.6 if speed_kmh is not None else None

        return speed_ms, direction

    except Exception:
        return None, None


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

    if 6 <= speed <= 14:
        score += 6
    elif speed > 14:
        score += 4
    else:
        score += 1

    if (0 <= direction <= 50) or (230 <= direction <= 359):
        score += 4
    else:
        score += 1

    return min(score, 10)


# =========================
# UI
# =========================

st.title("🏄 KiteNow – Hoek van Holland")
st.caption("Live wind data (Open-Meteo) – stable & cloud-safe")

# Fetch data
speed, direction = get_wind()

status = kite_status(speed, direction)
score = kite_score(speed, direction)

# =========================
# MAIN DISPLAY (BIG CENTER)
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

col1, col2 = st.columns(2)

col1.metric("Wind speed (m/s)", f"{speed:.1f}" if speed else "N/A")
col2.metric("Kite score", score)

# =========================
# TIMESTAMP
# =========================

st.caption(f"Last update: {datetime.utcnow().strftime('%H:%M:%S UTC')}")

# =========================
# MANUAL REFRESH
# =========================

if st.button("🔄 Refresh"):
    st.rerun()
