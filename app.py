
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="BrG@ RSI-BB F&O Scanner", layout="wide")

st.title("BrG@ RSI-BB F&O Stocks Scanner")
st.caption("Yahoo Finance | 2-minute & 5-minute | Scanner only")

DEFAULT_SYMBOLS = """RELIANCE.NS
HDFCBANK.NS
ICICIBANK.NS
SBIN.NS
AXISBANK.NS
INFY.NS
TCS.NS
TATAMOTORS.NS
BHARTIARTL.NS
KOTAKBANK.NS
LT.NS
ITC.NS
TATASTEEL.NS
BAJFINANCE.NS
MARUTI.NS
ADANIENT.NS
SUNPHARMA.NS
NTPC.NS
POWERGRID.NS
ONGC.NS"""

symbols_text = st.text_area(
    "NSE symbols (one per line)",
    value=DEFAULT_SYMBOLS,
    height=180
)

timeframes = st.multiselect(
    "Timeframes",
    ["2m", "5m"],
    default=["2m", "5m"]
)

scan = st.button("🔎 Scan Now", type="primary")

def rsi(series, length=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(
        alpha=1 / length, min_periods=length, adjust=False
    ).mean()
    loss = (-delta.clip(upper=0)).ewm(
        alpha=1 / length, min_periods=length, adjust=False
    ).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def add_indicators(df):
    df = df.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    df["BB_Mid"] = close.rolling(20).mean()
    std = close.rolling(20).std(ddof=0)
    df["BB_Upper"] = df["BB_Mid"] + 2 * std
    df["BB_Lower"] = df["BB_Mid"] - 2 * std
    df["RSI"] = rsi(close, 14)

    typical = (high + low + close) / 3
    cum_vol = volume.cumsum()
    df["VWAP"] = (typical * volume).cumsum() / cum_vol.replace(0, np.nan)

    return df

def get_pivots(symbol):
    daily = yf.download(
        symbol, period="5d", interval="1d",
        auto_adjust=False, progress=False, threads=False
    )
    if daily is None or daily.empty or len(daily) < 2:
        return None, None
    if isinstance(daily.columns, pd.MultiIndex):
        daily.columns = daily.columns.get_level_values(0)

    prev = daily.iloc[-2]
    p = (float(prev["High"]) + float(prev["Low"]) + float(prev["Close"])) / 3
    r1 = 2 * p - float(prev["Low"])
    s1 = 2 * p - float(prev["High"])
    return r1, s1

def scan_symbol(symbol, timeframe):
    interval = "1m" if timeframe == "2m" else "5m"
    period = "5d" if timeframe == "2m" else "5d"

    data = yf.download(
        symbol, period=period, interval=interval,
        auto_adjust=False, progress=False, threads=False
    )
    if data is None or data.empty:
        return None

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna(subset=["Close", "High", "Low"])
    if timeframe == "2m":
        data = data.resample("2min").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna()

    # Exclude the most recent candle, which may still be forming.
    if len(data) < 25:
        return None
    data = data.iloc[:-1]

    data = add_indicators(data)
    row = data.iloc[-1]

    r1, s1 = get_pivots(symbol)
    if r1 is None:
        return None

    close = float(row["Close"])
    rsi_value = float(row["RSI"]) if pd.notna(row["RSI"]) else np.nan
    upper = float(row["BB_Upper"]) if pd.notna(row["BB_Upper"]) else np.nan
    lower = float(row["BB_Lower"]) if pd.notna(row["BB_Lower"]) else np.nan
    vwap = float(row["VWAP"]) if pd.notna(row["VWAP"]) else np.nan

    if np.isnan([rsi_value, upper, lower, vwap]).any():
        return None

    ce = close > upper and rsi_value > 60 and (
        close > vwap or close > r1
    )
    pe = close < lower and rsi_value < 40 and (
        close < vwap or close < s1
    )

    if not ce and not pe:
        return None

    return {
        "Symbol": symbol,
        "Timeframe": timeframe,
        "Signal": "CE" if ce else "PE",
        "Close": round(close, 2),
        "RSI": round(rsi_value, 2),
        "VWAP": round(vwap, 2),
        "Pivot R1": round(r1, 2),
        "Pivot S1": round(s1, 2),
        "Candle Time": str(data.index[-1])
    }

if scan:
    symbols = [
        s.strip().upper()
        for s in symbols_text.splitlines()
        if s.strip()
    ]
    results = []
    errors = []

    if not symbols:
        st.warning("Please enter at least one NSE symbol.")
    else:
        progress = st.progress(0)
        status = st.empty()
        total = len(symbols) * len(timeframes)
        completed = 0

        for symbol in symbols:
            for tf in timeframes:
                completed += 1
                status.write(f"Scanning {symbol} ({tf}) — {completed}/{total}")
                try:
                    result = scan_symbol(symbol, tf)
                    if result:
                        results.append(result)
                except Exception as exc:
                    errors.append(f"{symbol} {tf}: {exc}")
                progress.progress(completed / total)

        status.write("Scan completed.")
        st.caption("Scan time: " + datetime.now().strftime("%d-%m-%Y %H:%M:%S"))

        if results:
            df = pd.DataFrame(results)
            st.success(f"{len(df)} signal(s) found")
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download CSV",
                df.to_csv(index=False).encode("utf-8"),
                file_name="brg_rsi_bb_signals.csv",
                mime="text/csv"
            )
        else:
            st.info("No matching CE/PE signals found in the scanned symbols.")

        if errors:
            with st.expander(f"Data errors ({len(errors)})"):
                st.write(errors)

st.caption(
    "Educational scanner only. Yahoo Finance data may be delayed, "
    "incomplete, or rate-limited. Verify signals before trading."
)
