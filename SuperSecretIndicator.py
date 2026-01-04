from binance.client import Client
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ================= CONFIG =================
SYMBOL = "ETHUSDT"

TIMEFRAMES = {
    "1m": Client.KLINE_INTERVAL_1MINUTE,
    "5m": Client.KLINE_INTERVAL_5MINUTE,
    "15m": Client.KLINE_INTERVAL_15MINUTE
}

EMA_PERIOD = 200
CANDLE_LIMIT = 300
UPDATE_INTERVAL_MS = 8000  # refresh every 8 seconds

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

# ================= EMA =================
def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

# ================= STATE-BASED BIAS =================
def compute_bias(price, ema200):
    bias = np.zeros(len(price), dtype=int)

    # initial state
    bias[0] = 1 if price.iloc[0] > ema200.iloc[0] else -1

    for i in range(1, len(price)):
        if price.iloc[i-1] <= ema200.iloc[i-1] and price.iloc[i] > ema200.iloc[i]:
            bias[i] = 1   # bullish flip
        elif price.iloc[i-1] >= ema200.iloc[i-1] and price.iloc[i] < ema200.iloc[i]:
            bias[i] = -1  # bearish flip
        else:
            bias[i] = bias[i-1]  # HOLD STATE

    return bias

# ================= PLOT =================
fig, axes = plt.subplots(3, 1, figsize=(16, 10), sharex=False)
fig.suptitle("ETHUSDT – Super Secret EMA 200 (1m / 5m / 15m)", fontsize=15)

def update(frame):
    for ax, (tf_name, tf_interval) in zip(axes, TIMEFRAMES.items()):
        df = fetch_data(tf_interval)

        price = df["close"]
        ema200 = ema(price, EMA_PERIOD)
        bias = compute_bias(price, ema200)

        ax.clear()

        # ---- Background (TradingView-style solid zones) ----
        ax.fill_between(
            range(len(price)),
            price.min(),
            price.max(),
            where=(bias == 1),
            color="#2962FF",
            alpha=0.12
        )

        ax.fill_between(
            range(len(price)),
            price.min(),
            price.max(),
            where=(bias == -1),
            color="#D32F2F",
            alpha=0.12
        )

        # ---- Price ----
        ax.plot(price.values, color="white", linewidth=1, label="Price")

        # ---- EMA 200 colored by STATE ----
        for i in range(1, len(price)):
            ax.plot(
                [i-1, i],
                [ema200.iloc[i-1], ema200.iloc[i]],
                color="#2962FF" if bias[i] == 1 else "#D32F2F",
                linewidth=2
            )

        # ---- Title ----
        state = "BULLISH ZONE (LONG BIAS)" if bias[-1] == 1 else "BEARISH ZONE (SHORT BIAS)"
        title_color = "green" if bias[-1] == 1 else "red"

        ax.set_title(f"{tf_name} | {state}", color=title_color, fontsize=11)
        ax.grid(alpha=0.25)
        ax.legend(loc="upper left")

ani = FuncAnimation(fig, update, interval=UPDATE_INTERVAL_MS)

plt.tight_layout()
plt.show()
