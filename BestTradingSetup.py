# ================= FORCE STABLE GUI BACKEND =================
import matplotlib
matplotlib.use("Qt5Agg")   # IMPORTANT for Windows stability

from binance.client import Client
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ================= CONFIG =================
SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_1MINUTE
CANDLE_LIMIT = 300
UPDATE_INTERVAL_MS = 8000

# ---- HULL SETTINGS (TESTED) ----
HULL_MODE = "Ehma"
HULL_LENGTH = 70
LENGTH_MULT = 1.0
EMA_PERIOD = 200

# ---- DONCHIAN SETTINGS (TESTED) ----
DONCHIAN_LEN = 20
RIBBON_LEVELS = list(range(5, 55, 5))

client = Client()

# ================= DATA =================
def fetch_data():
    klines = client.futures_klines(
        symbol=SYMBOL,
        interval=INTERVAL,
        limit=CANDLE_LIMIT
    )
    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume",
        "c1","c2","c3","c4","c5","c6"
    ])
    df[["high","low","close"]] = df[["high","low","close"]].astype(float)
    return df

# ================= MOVING AVERAGES =================
def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def wma(series, length):
    weights = np.arange(1, length + 1)
    return series.rolling(length).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )

# ================= HULL (EHMA) =================
def EHMA(src, length):
    return ema(
        2 * ema(src, length // 2) - ema(src, length),
        int(np.sqrt(length))
    )

def hull_selector(src):
    length = int(HULL_LENGTH * LENGTH_MULT)
    return EHMA(src, length)

# ================= DONCHIAN TREND =================
def donchian_trend(df, length):
    hh = df["high"].rolling(length).max()
    ll = df["low"].rolling(length).min()

    trend = np.zeros(len(df))
    for i in range(1, len(df)):
        if df["close"].iloc[i] > hh.iloc[i-1]:
            trend[i] = 1
        elif df["close"].iloc[i] < ll.iloc[i-1]:
            trend[i] = -1
        else:
            trend[i] = trend[i-1]
    return trend

def ribbon_color(sub, main):
    if main == 1:
        return (0, 1, 0, 1.0 if sub == 1 else 0.5)
    if main == -1:
        return (1, 0, 0, 1.0 if sub == -1 else 0.5)
    return (0, 0, 0, 0)

# ================= PLOT LAYOUT =================
fig = plt.figure(figsize=(16, 9))
gs = fig.add_gridspec(2, 1, height_ratios=[3, 1])

ax_top = fig.add_subplot(gs[0])   # Hull + EMA
ax_bot = fig.add_subplot(gs[1])   # Donchian Ribbon

fig.suptitle(
    "1m Scalping – EHMA 70 + EMA 200 + Donchian Trend Ribbon",
    fontsize=15
)

# Maximize window (Windows)
mng = plt.get_current_fig_manager()
try:
    mng.window.state('zoomed')
except Exception:
    pass

# ================= UPDATE =================
def update(frame):
    df = fetch_data()
    close = df["close"]

    # ===== HULL + EMA =====
    hull = hull_selector(close)
    MHULL = hull
    SHULL = hull.shift(2)
    ema200 = ema(close, EMA_PERIOD)

    hull_up = MHULL > SHULL
    hull_color = np.where(hull_up, "#00ff00", "#ff0000")

    ax_top.clear()

    # EMA 200
    ax_top.plot(ema200.values, color="yellow", linewidth=2, label="EMA 200")

    # Hull band
    for i in range(2, len(close)):
        ax_top.plot([i-1, i], [MHULL.iloc[i-1], MHULL.iloc[i]],
                    color=hull_color[i], linewidth=2)
        ax_top.plot([i-1, i], [SHULL.iloc[i-1], SHULL.iloc[i]],
                    color=hull_color[i], linewidth=2, alpha=0.6)

    ax_top.fill_between(
        range(len(close)), MHULL, SHULL,
        where=hull_up, color="#00ff00", alpha=0.15
    )
    ax_top.fill_between(
        range(len(close)), MHULL, SHULL,
        where=~hull_up, color="#ff0000", alpha=0.15
    )

    trend = "HULL UP" if hull_up.iloc[-1] else "HULL DOWN"
    ax_top.set_title(
        f"1m | {trend}",
        color="green" if hull_up.iloc[-1] else "red"
    )
    ax_top.grid(alpha=0.25)
    ax_top.legend(loc="upper left")

    # ===== DONCHIAN RIBBON =====
    ax_bot.clear()

    main = donchian_trend(df, DONCHIAN_LEN)
    x = np.arange(len(df))

    for idx, level in enumerate(RIBBON_LEVELS):
        sub = donchian_trend(df, DONCHIAN_LEN - idx)
        colors = [ribbon_color(sub[i], main[i]) for i in range(len(df))]
        ax_bot.bar(x, height=4, bottom=idx * 4, color=colors, width=1.0)

    ax_bot.set_xlim(0, len(df))
    ax_bot.set_ylim(0, 40)
    ax_bot.set_yticks(RIBBON_LEVELS)
    ax_bot.grid(False)

# ================= RUN =================
ani = FuncAnimation(fig, update, interval=UPDATE_INTERVAL_MS)

print("✅ Script running. Close the chart window or press Ctrl + C in terminal.")
plt.show()
