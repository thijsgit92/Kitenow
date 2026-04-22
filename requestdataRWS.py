import requests
import json
import time
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================

API_URL = "https://waterwebservices.rijkswaterstaat.nl/ONLINEWAARNEMINGENSERVICES_DBO/OphalenLaatsteWaarnemingen"
LOG_FILE = "hoek_van_holland_wind_log.json"

STATION_CODE = "HOEKVHLD"

SLEEP_SECONDS = 600  # 10 minutes


# =========================
# CORE API CALL
# =========================

def fetch_single_parameter(parameter_code):
    """
    Fetch one parameter (RWS expects 1 Grootheid per request)
    """

    payload = {
        "Locatie": {
            "Code": STATION_CODE
        },
        "AquoPlusWaarnemingMetadata": {
            "AquoMetadata": {
                "Grootheid": {
                    "Code": parameter_code
                }
            }
        }
    }

    try:
        r = requests.post(API_URL, json=payload, timeout=20)

        if r.status_code != 200:
            print(f"[ERROR] HTTP {r.status_code}: {r.text}")
            return None

        data = r.json()

        return safe_extract_value(data)

    except Exception as e:
        print("[ERROR] Request failed:", e)
        return None


# =========================
# SAFE PARSER (RWS variability fix)
# =========================

def safe_extract_value(data):
    """
    RWS responses are nested and inconsistent → this safely extracts first numeric value
    """

    try:
        if "WaarnemingenLijst" not in data:
            return None

        for item in data["WaarnemingenLijst"]:
            metingen = item.get("MetingenLijst", [])

            for m in metingen:
                value = m.get("Meetwaarde", {}).get("Waarde_Numeriek")

                if value is not None:
                    return float(value)

        return None

    except Exception as e:
        print("[PARSE ERROR]", e)
        return None


# =========================
# WIND FETCH
# =========================

def fetch_wind():
    speed = fetch_single_parameter("WINDSNELHEID")
    direction = fetch_single_parameter("WINDRICHTING")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "station": STATION_CODE,
        "wind_speed": speed,
        "wind_direction": direction,
        "status": get_status(speed, direction),
        "kite_index": kite_index(speed, direction)
    }


# =========================
# TRAFFIC LIGHT LOGIC
# =========================

def get_status(speed, direction):
    if speed is None or direction is None:
        return "unknown"

    good_direction = (
        (0 <= direction <= 50) or
        (230 <= direction <= 359)
    )

    if speed > 8 and good_direction:
        return "green"
    elif speed > 6 and good_direction:
        return "orange"
    else:
        return "red"


# =========================
# KITESURF INDEX (0–10)
# =========================

def kite_index(speed, direction):
    if speed is None or direction is None:
        return 0

    score = 0

    # wind strength scoring
    if 6 <= speed <= 14:
        score += 6
    elif 14 < speed <= 18:
        score += 4
    elif speed > 18:
        score += 2
    else:
        score += 1

    # direction bonus
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


def prune_24h(log):
    cutoff = datetime.utcnow() - timedelta(hours=24)

    cleaned = []
    for entry in log:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts > cutoff:
                cleaned.append(entry)
        except:
            continue

    return cleaned


# =========================
# MAIN LOOP
# =========================

def run():
    print("Starting Hoek van Holland kite logger...")

    while True:
        print("\nFetching wind data...")

        entry = fetch_wind()

        print(entry)

        log = load_log()
        log.append(entry)

        log = prune_24h(log)
        save_log(log)

        print(f"Entries stored (24h): {len(log)}")
        print(f"Status: {entry['status']} | Kite index: {entry['kite_index']}")

        time.sleep(SLEEP_SECONDS)


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    run()