from binance.client import Client
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ================= CONFIG =================
SYMBOL = "SOLUSDT"

# 🔹 ONLY 1-MINUTE FOR SCALPING
TIMEFRAMES = {
    "1m": Client.KLINE_INTERVAL_1MINUTE
}

CANDLE_LIMIT = 300
UPDATE_INTERVAL_MS = 8000

# 🔹 SCALPING SETTINGS (MODIFIED)
HULL_MODE = "Ehma"     # changed from Hma → Ehma
HULL_LENGTH = 70       # changed from 55 → 70
LENGTH_MULT = 1.0
EMA_PERIOD = 200

client = Client()

# ================= DATA =================
def fetch_data(interval):
    klines = client.futures_klines(
        symbol=SYMBOL,
        interval=interval,
        limit=CANDLE_LIMIT
    )
    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume",
        "c1","c2","c3","c4","c5","c6"
    ])
    df["close"] = df["close"].astype(float)
    return df

# ================= MOVING AVERAGES =================
def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def wma(series, length):
    weights = np.arange(1, length + 1)
    return series.rolling(length).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )

# ================= HULL VARIANTS =================
def HMA(src, length):
    return wma(
        2 * wma(src, length // 2) - wma(src, length),
        int(np.sqrt(length))
    )

def EHMA(src, length):
    return ema(
        2 * ema(src, length // 2) - ema(src, length),
        int(np.sqrt(length))
    )

def THMA(src, length):
    return wma(
        wma(src, length // 3) * 3 -
        wma(src, length // 2) -
        wma(src, length),
        length
    )

def hull_selector(src, length, mode):
    if mode == "Hma":
        return HMA(src, length)
    elif mode == "Ehma":
        return EHMA(src, length)
    elif mode == "Thma":
        return THMA(src, length // 2)
    else:
        return np.nan

# ================= PLOT =================
fig, ax = plt.subplots(figsize=(16, 6))
fig.suptitle("EHMA Hull Suite + EMA 200 (1m Scalping)", fontsize=15)

def update(frame):
    for tf_name, tf_interval in TIMEFRAMES.items():
        df = fetch_data(tf_interval)
        close = df["close"]

        hull_len = int(HULL_LENGTH * LENGTH_MULT)
        hull = hull_selector(close, hull_len, HULL_MODE)

        MHULL = hull
        SHULL = hull.shift(2)

        ema200 = ema(close, EMA_PERIOD)

        ax.clear()

        # ===== COLOR LOGIC (UNCHANGED) =====
        hull_up = MHULL > SHULL
        hull_color = np.where(hull_up, "#00ff00", "#ff0000")

        # ===== PRICE =====
        ax.plot(close.values, color="white", linewidth=1, label="Price")

        # ===== EMA 200 =====
        ax.plot(ema200.values, color="yellow", linewidth=2, label="EMA 200")

        # ===== HULL LINES =====
        for i in range(2, len(close)):
            ax.plot(
                [i-1, i],
                [MHULL.iloc[i-1], MHULL.iloc[i]],
                color=hull_color[i],
                linewidth=2
            )
            ax.plot(
                [i-1, i],
                [SHULL.iloc[i-1], SHULL.iloc[i]],
                color=hull_color[i],
                linewidth=2,
                alpha=0.6
            )

        # ===== BAND FILL =====
        ax.fill_between(
            range(len(close)),
            MHULL,
            SHULL,
            where=hull_up,
            color="#00ff00",
            alpha=0.15
        )

        ax.fill_between(
            range(len(close)),
            MHULL,
            SHULL,
            where=~hull_up,
            color="#ff0000",
            alpha=0.15
        )

        trend = "HULL TREND UP" if hull_up.iloc[-1] else "HULL TREND DOWN"
        title_color = "green" if hull_up.iloc[-1] else "red"

        ax.set_title(f"1m | {trend}", color=title_color, fontsize=11)
        ax.grid(alpha=0.25)
        ax.legend(loc="upper left")

ani = FuncAnimation(fig, update, interval=UPDATE_INTERVAL_MS)
plt.tight_layout()
plt.show()
