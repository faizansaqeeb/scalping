from binance.client import Client
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

SYMBOL = "BTCUSDT"
DONCHIAN_LEN = 20
CANDLE_LIMIT = 200
UPDATE_INTERVAL_MS = 8000

TIMEFRAMES = {
    "1m": Client.KLINE_INTERVAL_1MINUTE,
    "5m": Client.KLINE_INTERVAL_5MINUTE,
    "15m": Client.KLINE_INTERVAL_15MINUTE
}

client = Client()

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
    df[["high","low","close"]] = df[["high","low","close"]].astype(float)
    return df

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
    return (0, 0, 0, 0)  # transparent instead of None

fig, axes = plt.subplots(3, 1, figsize=(16, 7))
fig.suptitle("Donchian Trend Ribbon (1m / 5m / 15m)", fontsize=14)

RIBBON_LEVELS = list(range(5, 55, 5))

def update(frame):
    for ax, (tf_name, tf_interval) in zip(axes, TIMEFRAMES.items()):
        df = fetch_data(tf_interval)

        main = donchian_trend(df, DONCHIAN_LEN)
        x = np.arange(len(df))

        ax.clear()

        for idx, level in enumerate(RIBBON_LEVELS):
            sub = donchian_trend(df, DONCHIAN_LEN - idx)

            colors = [ribbon_color(sub[i], main[i]) for i in range(len(df))]

            ax.bar(
                x,
                height=4,
                bottom=idx * 4,
                color=colors,
                width=1.0
            )

        ax.set_xlim(0, len(df))
        ax.set_ylim(0, 40)
        ax.set_yticks(RIBBON_LEVELS)

        state = "BULLISH" if main[-1] == 1 else "BEARISH"
        ax.set_title(f"{tf_name} | {state}",
                     color="green" if main[-1] == 1 else "red")

        ax.grid(False)

ani = FuncAnimation(fig, update, interval=UPDATE_INTERVAL_MS)
plt.tight_layout()
plt.show()
