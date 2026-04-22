import requests
import json
from datetime import datetime, timedelta, timezone
import streamlit as st
import pandas as pd
import time

# auto-refresh every 60 seconds
time.sleep(60)
st.rerun()

st.title("🏄 KiteNow is running")
st.write("If you see this, the app is alive")

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = 0

st.session_state.last_refresh += 1

if st.session_state.last_refresh % 60 == 0:
    st.rerun()

# =========================
# CONFIG
# =========================
API_URL = "https://waterwebservices.rijkswaterstaat.nl/ONLINEWAARNEMINGENSERVICES_DBO/OphalenLaatsteWaarnemingen"
STATION_CODE = "HOEKVHLD"
LOG_FILE = "kite_log.json"

# refresh every 60 seconds (change to 120000 for 2 min if preferred)
st_autorefresh(interval=60000, key="kite_refresh")

# =========================
# DATA FETCH
# =========================

def fetch_single(code):
    payload = {
        "Locatie": {"Code": STATION_CODE},
        "AquoPlusWaarnemingMetadata": {
            "AquoMetadata": {
                "Grootheid": {"Code": code}
            }
        }
    }

    try:
        r = requests.post(API_URL, json=payload, timeout=20)
        if r.status_code != 200:
            return None

        data = r.json()

        for item in data.get("WaarnemingenLijst", []):
            for m in item.get("MetingenLijst", []):
                v = m.get("Meetwaarde", {}).get("Waarde_Numeriek")
                if v is not None:
                    return float(v)

    except Exception:
        return None

    return None


def fetch_wind():
    speed = fetch_single("WINDSNELHEID")
    direction = fetch_single("WINDRICHTING")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "speed": speed,
        "direction": direction,
        "status": status(speed, direction),
        "kite_score": kite_score(speed, direction)
    }


# =========================
# LOGIC
# =========================

def status(speed, direction):
    if speed is None or direction is None:
        return "unknown"

    good_dir = (0 <= direction <= 50) or (230 <= direction <= 359)

    if speed > 8 and good_dir:
        return "green"
    elif speed > 6 and good_dir:
        return "orange"
    return "red"


def kite_score(speed, direction):
    if speed is None or direction is None:
        return 0

    score = 0

    if 6 <= speed <= 14:
        score += 6
    elif speed > 14:
        score += 3
    else:
        score += 1

    if (0 <= direction <= 50) or (230 <= direction <= 359):
        score += 4
    else:
        score += 1

    return min(score, 10)


# =========================
# LOG HANDLING
# =========================

def load_log():
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def prune(log):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    cleaned = []

    for e in log:
        try:
            ts = datetime.fromisoformat(e["timestamp"]).replace(tzinfo=timezone.utc)
            if ts > cutoff:
                cleaned.append(e)
        except:
            pass

    return cleaned


# =========================
# UI
# =========================

st.set_page_config(page_title="Kitesurf Hoek van Holland", layout="centered")

st.title("🏄‍♂️ Kitesurf Dashboard – Hoek van Holland")

# Fetch current data
current = fetch_wind()

# Load + update log
log = load_log()
log.append(current)
log = prune(log)
save_log(log)

# =========================
# TOP CENTER WIND DISPLAY
# =========================

status_map = {
    "green": "🟢 GO",
    "orange": "🟠 BORDERLINE",
    "red": "🔴 NO GO",
    "unknown": "⚪ NO DATA"
}

st.markdown(
    f"""
    <div style='text-align: center;'>
        <h1>💨 {current['speed']} m/s</h1>
        <h3>🧭 {current['direction']}°</h3>
        <h2>{status_map.get(current['status'], 'UNKNOWN')}</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================
# METRICS
# =========================

col1, col2 = st.columns(2)
col1.metric("Wind speed", current["speed"])
col2.metric("Kite score", current["kite_score"])

# =========================
# HISTORY CHART
# =========================

st.subheader("Last 24h wind trend")

if len(log) > 1:
    df = pd.DataFrame(log)
    df["time"] = pd.to_datetime(df["timestamp"])
    st.line_chart(df.set_index("time")["speed"])

# =========================
# FOOTER
# =========================

st.caption("Data: Rijkswaterstaat HOEKVHLD | Auto-refresh enabled")
