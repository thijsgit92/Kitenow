import streamlit as st
import requests
from datetime import datetime

# =========================
# CONFIG
# =========================

st.set_page_config(page_title="Kite Intelligence - Noorderpier", layout="centered")

LAT = 52.01
LON = 4.12

# =========================
# CONVERSIONS
# =========================

def kmh_to_knots(kmh):
    return kmh * 0.539957


# =========================
# FETCH FORECAST
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
# GUST FACTOR
# =========================

def gust_factor(speed, gust):
    if speed == 0 or speed is None:
        return 0
    return gust / speed


def gust_label(gf):
    if gf < 1.2:
        return "🟢 Clean"
    elif gf < 1.5:
        return "🟠 Gusty"
    return "🔴 Dangerous"


# =========================
# SIMPLE "TIDE PROXY"
# (Noorderpier weighting)
# =========================

def tide_score(hour_index):
    # rough heuristic:
    # morning + late afternoon = better flow near Noordpier
    if 6 <= hour_index <= 10:
        return 2
    elif 16 <= hour_index <= 20:
        return 2
    return 1


# =========================
# BEST 2-HOUR WINDOW
# =========================

def best_window(hourly):
    speeds = hourly["windspeed_10m"]
    gusts = hourly["windgusts_10m"]

    best_score = -999
    best_start = 0

    for i in range(len(speeds) - 2):

        s1 = kmh_to_knots(speeds[i])
        s2 = kmh_to_knots(speeds[i + 1])

        g1 = kmh_to_knots(gusts[i])
        g2 = kmh_to_knots(gusts[i + 1])

        avg_speed = (s1 + s2) / 2
        avg_gust = (g1 + g2) / 2

        gf = gust_factor(avg_speed, avg_gust)

        score = 0

        # wind quality
        if 12 <= avg_speed <= 25:
            score += 5
        elif avg_speed > 25:
            score += 3
        else:
            score += 1

        # stability
        if gf < 1.3:
            score += 4
        elif gf < 1.6:
            score += 2
        else:
            score -= 2

        # tide proxy
        score += tide_score(i)

        if score > best_score:
            best_score = score
            best_start = i

    return best_start, best_score


# =========================
# WIND TREND
# =========================

def trend(values):
    v = values[:5]
    if v[-1] > v[0] + 2:
        return "📈 Building"
    elif v[-1] < v[0] - 2:
        return "📉 Dropping"
    return "➡ Stable"


# =========================
# DATA
# =========================

hourly = get_forecast()

wind = hourly["windspeed_10m"]
dir = hourly["winddirection_10m"]
gust = hourly["windgusts_10m"]
time = hourly["time"]

# CURRENT (knots)
current_speed = kmh_to_knots(wind[0])
current_gust = kmh_to_knots(gust[0])
current_dir = dir[0]

gf = gust_factor(current_speed, current_gust)

t = trend([kmh_to_knots(x) for x in wind])

best_start, best_score = best_window(hourly)

# =========================
# UI
# =========================

st.title("🏄 Kite Intelligence – Noorderpier")
st.caption("Wind + gust + tide proxy + session optimizer")

# =========================
# CURRENT CONDITIONS
# =========================

st.markdown(
    f"""
    <div style="text-align:center;">
        <h1>💨 {current_speed:.1f} kn</h1>
        <h2>🧭 {current_dir:.0f}°</h2>
        <h3>🌬 Gust: {current_gust:.1f} kn</h3>
        <h3>{gust_label(gf)} (GF {gf:.2f})</h3>
        <h3>{t}</h3>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================
# BEST WINDOW OUTPUT
# =========================

start_time = time[best_start]
end_time = time[best_start + 2]

st.subheader("🌊 Best 2-hour kite window (Noorderpier optimized)")

st.success(f"""
🟢 BEST WINDOW:  
{start_time} → {end_time}  

🔥 Score: {best_score:.1f}
""")

# =========================
# SAFETY INSIGHT
# =========================

if gf > 1.6:
    st.error("⚠️ Very gusty — risky conditions")
elif current_speed > 18 and gf < 1.3:
    st.success("🔥 PERFECT KITE CONDITIONS NOW")
elif current_speed < 10:
    st.info("🌤 Underpowered — wait for wind")
else:
    st.warning("🟡 Rideable but not optimal")

# =========================
# REFRESH
# =========================

if st.button("🔄 Refresh"):
    st.rerun()
