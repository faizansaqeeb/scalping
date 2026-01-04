from binance.client import Client
import pandas as pd
import numpy as np
import time
import requests

# ================= TELEGRAM =================
TELEGRAM_TOKEN = "8565575662:AAGkqeUhSI0qXzXBFDdzIgEzR4gzm2iohAw"
TELEGRAM_CHAT_ID = "2137177601"

def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=5
        )
    except:
        pass

# ================= CONFIG =================
TOP_COINS = 500
CANDLE_LIMIT = 210
FRESH_SECONDS = 120          # max 2 minutes
HULL_LENGTH = 55
EMA_PERIOD = 200

client = Client()

# ================= SYMBOL LIST =================
def get_top_symbols():
    df = pd.DataFrame(client.futures_ticker())
    df = df[df["symbol"].str.endswith("USDT")]
    df["vol"] = df["quoteVolume"].astype(float)
    return df.sort_values("vol", ascending=False)["symbol"].head(TOP_COINS).tolist()

# ================= INDICATORS =================
def ema(s, l):
    return s.ewm(span=l, adjust=False).mean()

def wma(s, l):
    w = np.arange(1, l + 1)
    return s.rolling(l).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)

def hma(s, l):
    return wma(2 * wma(s, l // 2) - wma(s, l), int(np.sqrt(l)))

def atr(df, l=14):
    pc = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - pc).abs(),
        (df["low"] - pc).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/l, adjust=False).mean()

def adx(df, l=14):
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0)
    minus_dm = np.where((down > up) & (down > 0), down, 0)
    tr = atr(df, l)
    plus_di = 100 * pd.Series(plus_dm).ewm(alpha=1/l).mean() / tr
    minus_di = 100 * pd.Series(minus_dm).ewm(alpha=1/l).mean() / tr
    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
    return dx.ewm(alpha=1/l).mean()

def choppiness(df, length=14):
    tr = atr(df, 1)
    hl = df["high"].rolling(length).max() - df["low"].rolling(length).min()
    return 100 * np.log10(tr.rolling(length).sum() / hl) / np.log10(length)

# ================= SUCCESS RATE =================
def success_rate_1m(df):
    adx_val = adx(df).iloc[-1]
    chop_val = choppiness(df).iloc[-1]

    adx_score  = min(max((adx_val - 15) * 3, 0), 50)
    chop_score = min(max((60 - chop_val) * 2, 0), 50)

    return int(adx_score + chop_score)

# ================= MAIN LOOP =================
symbols = get_top_symbols()
print("⚡ PURE 1M HULL FLIP SCALPER (FIXED) STARTED")

while True:
    now = time.time()

    for symbol in symbols:
        try:
            df = pd.DataFrame(
                client.futures_klines(
                    symbol=symbol,
                    interval=Client.KLINE_INTERVAL_1MINUTE,
                    limit=CANDLE_LIMIT
                ),
                columns=["time","open","high","low","close","volume","x1","x2","x3","x4","x5","x6"]
            )

            df[["open","high","low","close","volume"]] = df[
                ["open","high","low","close","volume"]
            ].astype(float)

            # 🔑 DROP LIVE CANDLE (CRITICAL FIX)
            df = df.iloc[:-1]

            close = df["close"]
            ema200 = ema(close, EMA_PERIOD)
            hull = hma(close, HULL_LENGTH)
            shull = hull.shift(2)

            # ----- Hull color state -----
            prev_green = hull.iloc[-2] > shull.iloc[-2]
            curr_green = hull.iloc[-1] > shull.iloc[-1]

            # ----- Freshness (CLOSED candle only) -----
            last_close_time = df["time"].iloc[-1] / 1000 + 60
            age = int(now - last_close_time)

            if age < 0 or age > FRESH_SECONDS:
                continue

            # ----- ADX Filter -----
            if adx(df).iloc[-1] < 18:
                continue

            # ===== LONG SCALP =====
            if (
                close.iloc[-1] > ema200.iloc[-1] and
                not prev_green and curr_green
            ):
                direction = "LONG"

            # ===== SHORT SCALP =====
            elif (
                close.iloc[-1] < ema200.iloc[-1] and
                prev_green and not curr_green
            ):
                direction = "SHORT"
            else:
                continue

            # ----- Success Rate -----
            score = success_rate_1m(df)
            if score < 60:
                continue

            size = "2.5%" if score < 70 else "3.5%" if score < 85 else "5%"
            lev  = "5x" if score < 70 else "7x" if score < 85 else "10x"

            msg = (
                f"⚡ {direction} SCALP (1M)\n\n"
                f"🪙 Coin: {symbol}\n"
                f"📊 Hull Flip: {'RED→GREEN' if direction=='LONG' else 'GREEN→RED'}\n"
                f"📈 Price vs EMA200: {'ABOVE' if direction=='LONG' else 'BELOW'}\n"
                f"🎯 Score: {score}%\n"
                f"📦 Size: {size}\n"
                f"⚡ Leverage: {lev}\n"
                f"⏳ Fresh: {age}s"
            )

            print(msg)
            send_telegram(msg)

        except Exception as e:
            print(symbol, e)

    time.sleep(5)
