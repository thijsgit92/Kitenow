import streamlit as st
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================

st.set_page_config(page_title="Kite Intelligence Pro", layout="wide")

LAT = 52.01
LON = 4.12

# =========================
# CONVERSIONS
# =========================

def kmh_to_knots(x):
    return x * 0.539957


# =========================
# WIND DATA
# =========================

def get_forecast():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}"
        f"&longitude={LON}"
        "&hourly=windspeed_10m,winddirection_10m,windgusts_10m"
        "&forecast_days=7"
        "&timezone=UTC"
    )

    r = requests.get(url, timeout=10)
    return r.json()["hourly"]


# =========================
# TIDE (FALLBACK MODEL)
# =========================

def tide_cycle(hour):
    # simple harmonic tide approximation
    # 12h cycle high/low
    return np.sin((hour / 12) * np.pi)


def tide_label(value):
    if value > 0.6:
        return "🌊 High tide"
    elif value < -0.6:
        return "🌊 Low tide"
    return "🌊 Mid tide"


# =========================
# KITE SCORE MODEL
# =========================

def kite_score(speed, gust, direction, tide):
    score = 0

    # wind strength
    if 12 <= speed <= 25:
        score += 5
    elif speed > 25:
        score += 3
    else:
        score += 1

    # gust stability
    gf = gust / speed if speed > 0 else 10
    if gf < 1.3:
        score += 4
    elif gf < 1.6:
        score += 2
    else:
        score -= 2

    # tide bonus (Noorderpier effect)
    if abs(tide) > 0.6:
        score += 2

    # direction (simple west coast logic)
    if 200 <= direction <= 320:
        score += 2

    return max(0, min(10, score))


# =========================
# FETCH DATA
# =========================

hourly = get_forecast()

wind = hourly["windspeed_10m"]
gust = hourly["windgusts_10m"]
dir = hourly["winddirection_10m"]
time = hourly["time"]

# =========================
# CURRENT CONDITIONS
# =========================

now_speed = kmh_to_knots(wind[0])
now_gust = kmh_to_knots(gust[0])
now_dir = dir[0]

now_tide = tide_cycle(0)
now_score = kite_score(now_speed, now_gust, now_dir, now_tide)

# =========================
# WEEK SCORE SERIES
# =========================

scores = []
tides = []

for i in range(len(wind)):
    s = kmh_to_knots(wind[i])
    g = kmh_to_knots(gust[i])
    d = dir[i]
    t = tide_cycle(i)

    scores.append(kite_score(s, g, d, t))
    tides.append(t)


df = pd.DataFrame({
    "time": time,
    "score": scores,
    "wind": [kmh_to_knots(x) for x in wind],
})


# =========================
# BEST WINDOW
# =========================

best_i = int(np.argmax(scores))
best_time = time[best_i]

# =========================
# UI
# =========================

st.title("🏄 Kite Intelligence Pro – Noorderpier")

col1, col2, col3 = st.columns(3)

col1.metric("Wind", f"{now_speed:.1f} kn")
col2.metric("Gust", f"{now_gust:.1f} kn")
col3.metric("Kite score", now_score)

st.subheader("🌊 Tide state")
st.success(tide_label(now_tide))

st.subheader("🔥 Best moment this week")
st.success(f"Peak kite time: {best_time} (score {scores[best_i]:.1f})")

# =========================
# SCORE TIMELINE
# =========================

st.subheader("📈 Weekly kite score timeline")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["time"],
    y=df["score"],
    mode="lines",
    name="Kite score"
))

fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))

st.plotly_chart(fig, use_container_width=True)


# =========================
# WIND FIELD MAP (SIMPLE GRID)
# =========================

st.subheader("🗺️ Wind field (local area)")

grid_lats = np.linspace(51.95, 52.10, 6)
grid_lons = np.linspace(4.0, 4.25, 6)

lats, lons, u, v = [], [], [], []

for la in grid_lats:
    for lo in grid_lons:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={la}"
            f"&longitude={lo}"
            "&hourly=windspeed_10m,winddirection_10m"
            "&forecast_days=1"
        )

        r = requests.get(url)
        data = r.json()["hourly"]

        speed = kmh_to_knots(data["windspeed_10m"][0])
        direction = data["winddirection_10m"][0]

        rad = np.radians(direction)

        u.append(speed * np.sin(rad))
        v.append(speed * np.cos(rad))

        lats.append(la)
        lons.append(lo)


fig2 = go.Figure()

fig2.add_trace(go.Cone(
    x=lons,
    y=lats,
    u=u,
    v=v,
    sizemode="absolute",
    sizeref=0.3,
    anchor="tail"
))

fig2.update_layout(height=500)

st.plotly_chart(fig2, use_container_width=True)


# =========================
# REFRESH
# =========================

if st.button("🔄 Refresh"):
    st.rerun()
