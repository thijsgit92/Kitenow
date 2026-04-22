import streamlit as st
import requests
from datetime import datetime, timezone

API_URL = "https://waterwebservices.rijkswaterstaat.nl/ONLINEWAARNEMINGENSERVICES_DBO/OphalenLaatsteWaarnemingen"
STATION_CODE = "HOEKVHLD"

# =========================
# ALWAYS FIRST: UI
# =========================
st.title("🏄 KiteNow – Hoek van Holland")

placeholder = st.empty()

# =========================
# SAFE DATA FUNCTION
# =========================

def fetch_single(code):
    payload = {
        "AquoPlusWaarnemingMetadata": {
            "AquoMetadata": {
                "Grootheid": {
                    "Code": code
                }
            }
        },
        "LocatieIdentificatie": {
            "Code": "HOEKVHLD"
        }
    }

    r = requests.post(API_URL, json=payload, timeout=10)

    if r.status_code != 200:
        print(r.text)
        return None

    data = r.json()

    try:
        for item in data.get("WaarnemingenLijst", []):
            for m in item.get("MetingenLijst", []):
                v = m.get("Meetwaarde", {}).get("Waarde_Numeriek")
                if v is not None:
                    return float(v)
    except:
        return None

    return None


# =========================
# STATUS LOGIC
# =========================
def status(speed, direction):
    if speed is None or direction is None:
        return "⚪ NO DATA"

    good_dir = (0 <= direction <= 50) or (230 <= direction <= 359)

    if speed > 8 and good_dir:
        return "🟢 GO"
    elif speed > 6:
        return "🟠 BORDERLINE"
    return "🔴 NO GO"


# =========================
# MAIN LOOP (SAFE)
# =========================
def render():
    speed = fetch_single("WINDSNELHEID")
    direction = fetch_single("WINDRICHTING")

    placeholder.markdown(f"""
    ## 💨 Wind: {speed} m/s  
    ## 🧭 Direction: {direction}°  
    ## Status: {status(speed, direction)}  

    ⏱ Updated: {datetime.now(timezone.utc).strftime("%H:%M:%S UTC")}
    """)


# =========================
# RUN
# =========================
render()
