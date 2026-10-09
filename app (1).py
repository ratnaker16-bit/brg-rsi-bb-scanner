
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from flask import Flask, render_template_string, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

IST = ZoneInfo("Asia/Kolkata")
DHAN_API_BASE = "https://api.dhan.co/v2"

# व्यापक शुरुआती NSE F&O stock list.
# वर्तमान आधिकारिक सूची से हर symbol की पात्रता अलग से सत्यापित करें.
DEFAULT_SYMBOLS = """
360ONE ABB APLAPOLLO AUBANK ADANIENSOL ADANIENT ADANIGREEN ADANIPORTS
ADANIPOWER ABCAPITAL ALKEM AMBER AMBUJACEM ANANDRATHI ANGELONE APOLLOHOSP
ASHOKLEY ASIANPAINT ASTRAL ATHERENERG AUROPHARMA DMART AXISBANK BSE
BAJAJ-AUTO BAJFINANCE BAJAJFINSV BAJAJHLDNG BANDHANBNK BANKBARODA
BANKINDIA MAHABANK BDL BEL BHARATFORG BHEL BPCL BHARTIARTL BIOCON
BLUESTARCO BOSCHLTD BRITANNIA CGPOWER CANBK CDSL CHOLAFIN CIPLA
COALINDIA COCHINSHIP COFORGE COLPAL CAMS CONCOR CROMPTON CUMMINSIND
DLF DABUR DELHIVERY DIVISLAB DIXON DRREDDY ETERNAL EICHERMOT FORCEMOT
NYKAA FORTIS GAIL GVT&D GMRAIRPORT GLENMARK GODFRYPHLP GODREJCP
GODREJPROP GRASIM HCLTECH HDFCAMC HDFCBANK HDFCLIFE HAVELLS HEROMOTOCO
HINDALCO HAL HINDPETRO HINDUNILVR HINDZINC POWERINDIA HYUNDAI ICICIBANK
ICICIGI ICICIPRULI IDFCFIRSTB ITC INDIANB IEX IOC IRFC IREDA INDUSTOWER
INDUSINDBK NAUKRI INFY INOXWIND INDIGO JINDALSTEL JSWENERGY JSWSTEEL
JIOFIN JUBLFOOD KEI KPITTECH KALYANKJIL KAYNES KFINTECH KOTAKBANK
LTF LICHSGFIN LTM LT LAURUSLABS LICI LODHA LUPIN M&M MANAPPURAM
MANKIND MARICO MARUTI MFSL MAXHEALTH MAZDOCK MOTILALOFS MPHASIS MCX
MUTHOOTFIN NBCC NHPC NMDC NTPC NATIONALUM NESTLEIND OBEROIRLTY OFSS
ONGC OIL OLAELEC PAYTM PERSISTENT PETRONET PIDILITIND PIIND PNB
POLICYBZR POLYCAB POONAWALLA POWERGRID PRESTIGE PFC PGEL RBLBANK
RECLTD RELIANCE RVNL SAIL SAMMAANCAP SHRIRAMFIN SIEMENS SJVN SOLARINDS
SONACOMS SRF SBIN SUNDARMFIN SUNPHARMA SUPREMEIND SUZLON SYNGENE
TATACHEM TATACOMM TATACONSUM TATAELXSI TATAMOTORS TATAPOWER TATASTEEL
TATATECH TCS TECHM FEDERALBNK INDHOTEL PHOENIXLTD TITAN TORNTPHARM
TRENT TIINDIA UNOMINDA UPL UJJIVANSFB ULTRACEMCO UNIONBANK UNITDSPR
VBL VEDL VMM IDEA VOLTAS WAAREEENER WIPRO YESBANK ZYDUSLIFE AARTIIND
ABBOTINDIA ACC ALIVUS APOLLOTYRE ATGL BAJAJHFL BALKRISIND BATAINDIA
BEML BERGEPAINT BIRLACORPN BSOFT CANFINHOME CASTROLIND CESC CHAMBLFERT
CHENNPETRO COROMANDEL CREDITACC DEEPAKNTR DELTACORP ECLERX ESCORTS EXIDEIND
"""
DEFAULT_SYMBOLS = ",".join(DEFAULT_SYMBOLS.split())

HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BrG@ RSI-BB F&O Stocks</title>
<style>
:root {
  color-scheme: dark;
  --bg:#0b1220; --panel:#111c2e; --line:#26364d;
  --muted:#9fb0c5;
}
* { box-sizing:border-box; }
body {
  margin:0; font-family:Arial,sans-serif;
  background:var(--bg); color:#edf3fb;
}
main { max-width:1400px; margin:auto; padding:22px; }
h1 { margin-bottom:6px; font-size:28px; }
.sub { color:var(--muted); margin-bottom:22px; }
.panel {
  background:var(--panel); border:1px solid var(--line);
  border-radius:14px; padding:18px; margin-bottom:18px;
}
label {
  display:block; margin:12px 0 6px;
  color:#c9d6e6; font-size:14px;
}
input[type=text], input[type=password], textarea, select {
  width:100%; padding:11px; border-radius:8px;
  border:1px solid #334861; background:#0b1525; color:#fff;
}
textarea { min-height:100px; }
button {
  margin-top:15px; padding:11px 18px; border:0;
  border-radius:8px; background:#2f80ed; color:white;
  font-weight:bold; cursor:pointer;
}
button:hover { background:#1767d2; }
.grid {
  display:grid; grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
}
.metric {
  background:#0b1525; border:1px solid var(--line);
  border-radius:10px; padding:14px;
}
.metric small { color:var(--muted); display:block; }
.metric strong { font-size:25px; display:block; margin-top:7px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th,td {
  padding:10px 8px; text-align:left;
  border-bottom:1px solid var(--line); white-space:nowrap;
}
th { color:#b9c9dc; background:#0b1525; }
.table-wrap { overflow:auto; }
.ce { color:#5ce0a0; font-weight:bold; }
.pe { color:#ff7f86; font-weight:bold; }
.none { color:#aab9cb; }
.error { color:#ff9b9b; }
.ok { color:#65e6a4; }
.hint { color:var(--muted); font-size:13px; line-height:1.5; }
@media(max-width:700px) {
  main {padding:12px;}
  .grid {grid-template-columns:1fr;}
  h1 {font-size:23px;}
}
</style>
</head>
<body>
<main>
<h1>📈 BrG@ RSI-BB F&amp;O Stocks</h1>
<div class="sub">
DhanHQ • NSE F&amp;O stock scanner • 2-minute and 5-minute CE/PE signals
</div>

<div class="panel">
<h2>Scanner Settings</h2>
<form method="post" enctype="multipart/form-data">
<label>Dhan Client ID</label>
<input type="text" name="client_id" value="{{ client_id }}"
placeholder="Your Dhan Client ID" autocomplete="off">

<label>Dhan Access Token</label>
<input type="password" name="access_token" value=""
placeholder="Enter Dhan access token" autocomplete="new-password">

<p class="hint">
सुरक्षा के लिए token को public code या chat में साझा न करें।
आप चाहें तो environment variables का उपयोग कर सकते हैं।
</p>

<label>F&amp;O Stock Symbols</label>
<textarea name="symbols">{{ symbols_text }}</textarea>

<label>Dhan Scrip-Master CSV (recommended)</label>
<input type="file" name="master_csv" accept=".csv">

<p class="hint">
CSV से symbols और Dhan Security IDs का मिलान किया जाएगा।
</p>

<label>Manual Security IDs (वैकल्पिक)</label>
<input type="text" name="security_ids" value="{{ security_ids }}"
placeholder="RELIANCE:2885,HDFCBANK:1333">

<label>Timeframes</label>
<select name="timeframes" multiple size="2">
<option value="2 minute" {% if '2 minute' in timeframes %}selected{% endif %}>
2 minute
</option>
<option value="5 minute" {% if '5 minute' in timeframes %}selected{% endif %}>
5 minute
</option>
</select>

<p class="hint">
दोनों timeframe चुनने के लिए मोबाइल पर एक विकल्प चुनकर दूसरे पर
टैप करें। जरूरत हो तो दोनों को चुनकर रखें।
</p>
<button type="submit">Scan Stocks</button>
</form>
</div>

{% if message %}
<div class="panel">
<div class="{{ message_class }}">{{ message }}</div>
</div>
{% endif %}

{% if rows %}
<div class="panel">
<div class="grid">
<div class="metric">
<small>CE Signals</small>
<strong class="ce">{{ ce_count }}</strong>
</div>
<div class="metric">
<small>PE Signals</small>
<strong class="pe">{{ pe_count }}</strong>
</div>
<div class="metric">
<small>Stocks Scanned</small>
<strong>{{ stocks_count }}</strong>
</div>
</div>

<h2 style="margin-top:24px">Scan Results</h2>
<div class="table-wrap">
<table>
<thead><tr>
{% for col in columns %}<th>{{ col }}</th>{% endfor %}
</tr></thead>
<tbody>
{% for row in rows %}
<tr>
{% for col in columns %}
<td class="{% if col == 'Signal' and row[col] == 'CE' %}ce{% elif col == 'Signal' and row[col] == 'PE' %}pe{% elif col == 'Signal' %}none{% endif %}">
{{ row[col] }}
</td>
{% endfor %}
</tr>
{% endfor %}
</tbody>
</table>
</div>
<p class="hint">Signal केवल पूरी हो चुकी candle पर आधारित है। समय IST में है।</p>
</div>
{% endif %}

{% if errors %}
<div class="panel">
<h2>Data/API Errors</h2>
<div class="table-wrap">
<table>
<thead><tr><th>Stock</th><th>Timeframe</th><th>Error</th></tr></thead>
<tbody>
{% for e in errors %}
<tr>
<td>{{ e.Stock }}</td>
<td>{{ e.Timeframe }}</td>
<td class="error">{{ e.Error }}</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
</div>
{% endif %}

<div class="panel">
<h2>Signal Rules</h2>
<p><span class="ce">CE:</span>
Close Upper Bollinger Band से ऊपर, RSI(14) &gt; 60,
और Close VWAP या Pivot R1 से ऊपर।
</p>
<p><span class="pe">PE:</span>
Close Lower Bollinger Band से नीचे, RSI(14) &lt; 40,
और Close VWAP या Pivot S1 से नीचे।
</p>
<p class="hint">
Bollinger Bands: 20-period SMA ± 2 standard deviations.
Standard Pivot पिछले पूरे trading day के High, Low और Close से बनता है.
यह scanner केवल signals दिखाता है; orders place नहीं करता और profit की
गारंटी नहीं देता।
</p>
</div>
</main>
</body>
</html>
"""


class DhanAPIError(RuntimeError):
    pass


def dhan_post(path, token, payload):
    try:
        response = requests.post(
            DHAN_API_BASE + path,
            headers={
                "access-token": token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=18,
        )
        if response.status_code >= 400:
            raise DhanAPIError(
                f"HTTP {response.status_code}: {response.text[:250]}"
            )
        data = response.json()
        if not isinstance(data, dict):
            raise DhanAPIError("Unexpected Dhan response.")
        if data.get("status") == "failure" or data.get("errorCode"):
            raise DhanAPIError(str(data)[:300])
        return data
    except requests.RequestException as exc:
        raise DhanAPIError(f"Connection error: {exc}") from exc
    except ValueError as exc:
        raise DhanAPIError("Dhan API did not return valid JSON.") from exc


def candles_to_df(payload):
    keys = ["open", "high", "low", "close", "volume", "timestamp"]
    if any(k not in payload for k in keys):
        raise DhanAPIError("Candle response missing OHLCV/timestamp arrays.")
    if len({len(payload[k]) for k in keys}) != 1:
        raise DhanAPIError("Candle response arrays have different lengths.")

    df = pd.DataFrame({k: payload[k] for k in keys})
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], unit="s", utc=True)
        .dt.tz_convert(IST)
    )
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return (
        df.dropna()
        .sort_values("timestamp")
        .drop_duplicates("timestamp")
        .reset_index(drop=True)
    )


def fetch_intraday(token, security_id, interval):
    now = datetime.now(IST)
    start = now.replace(hour=9, minute=15, second=0, microsecond=0)

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": "NSE_EQ",
        "instrument": "EQUITY",
        "interval": interval,
        "oi": False,
        "fromDate": start.strftime("%Y-%m-%d %H:%M:%S"),
        "toDate": now.strftime("%Y-%m-%d %H:%M:%S"),
    }

    df = candles_to_df(dhan_post("/charts/intraday", token, payload))
    if df.empty:
        raise DhanAPIError("No intraday candles returned.")
    return df


def make_2m(df):
    if df.empty:
        return df

    x = df.copy().set_index("timestamp").sort_index()
    origin = x.index[0].normalize() + pd.Timedelta(hours=9, minutes=15)
    grouped = x.resample(
        "2min", origin=origin, label="left", closed="left"
    )

    bars = grouped.agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )

    counts = grouped["close"].count()
    now = pd.Timestamp.now(tz=IST)

    bars = bars[
        (counts == 2)
        & (bars.index + pd.Timedelta(minutes=2) <= now)
    ]
    return bars.dropna().reset_index()


def make_5m_closed(df):
    now = pd.Timestamp.now(tz=IST)
    return df[
        df["timestamp"] + pd.Timedelta(minutes=5) <= now
    ].copy().reset_index(drop=True)


def fetch_prev_hlc(token, security_id):
    today = datetime.now(IST).date()
    start = today - timedelta(days=20)

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": "NSE_EQ",
        "instrument": "EQUITY",
        "expiryCode": 0,
        "oi": False,
        "fromDate": start.strftime("%Y-%m-%d"),
        "toDate": today.strftime("%Y-%m-%d"),
    }

    data = dhan_post("/charts/historical", token, payload)
    keys = ["high", "low", "close", "timestamp"]

    if any(k not in data for k in keys):
        raise DhanAPIError("Daily candle response missing H/L/C/timestamp.")

    daily = pd.DataFrame({k: data[k] for k in keys})
    daily["date"] = (
        pd.to_datetime(daily["timestamp"], unit="s", utc=True)
        .dt.tz_convert(IST)
        .dt.date
    )

    daily = daily[daily["date"] < today].sort_values("date")
    if daily.empty:
        raise DhanAPIError("Previous completed trading day's H/L/C unavailable.")

    row = daily.iloc[-1]
    return float(row["high"]), float(row["low"]), float(row["close"])


def indicators(df, hlc):
    out = df.copy().sort_values("timestamp").reset_index(drop=True)

    # Bollinger Bands: 20-period SMA +/- 2 standard deviations
    out["bb_mid"] = out["close"].rolling(20, min_periods=20).mean()
    sd = out["close"].rolling(20, min_periods=20).std(ddof=0)
    out["upper"] = out["bb_mid"] + 2 * sd
    out["lower"] = out["bb_mid"] - 2 * sd

    # RSI(14)
    delta = out["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14, min_periods=14, adjust=False
    ).mean()
    avg_loss = loss.ewm(
        alpha=1 / 14, min_periods=14, adjust=False
    ).mean()

    rs = avg_gain / avg_loss.where(avg_loss != 0)
    out["rsi"] = 100 - (100 / (1 + rs))
    out.loc[(avg_loss == 0) & (avg_gain > 0), "rsi"] = 100
    out.loc[(avg_gain == 0) & (avg_loss > 0), "rsi"] = 0

    # Session VWAP
    typical = (out["high"] + out["low"] + out["close"]) / 3
    trading_day = out["timestamp"].dt.date
    volume_cum = (
        out["volume"].groupby(trading_day).cumsum()
        .replace(0, float("nan"))
    )
    price_volume_cum = (
        (typical * out["volume"]).groupby(trading_day).cumsum()
    )
    out["vwap"] = price_volume_cum / volume_cum

    # Standard Pivot levels based on previous completed trading day
    high, low, close = hlc
    pivot = (high + low + close) / 3
    out["r1"] = 2 * pivot - low
    out["s1"] = 2 * pivot - high

    out["ce_vwap"] = out["close"] > out["vwap"]
    out["ce_r1"] = out["close"] > out["r1"]
    out["pe_vwap"] = out["close"] < out["vwap"]
    out["pe_s1"] = out["close"] < out["s1"]

    # CE: Upper BB breakout + RSI > 60 + VWAP OR R1
    out["ce"] = (
        (out["close"] > out["upper"])
        & (out["rsi"] > 60)
        & (out["ce_vwap"] | out["ce_r1"])
    )

    # PE: Lower BB breakdown + RSI < 40 + VWAP OR S1
    out["pe"] = (
        (out["close"] < out["lower"])
        & (out["rsi"] < 40)
        & (out["pe_vwap"] | out["pe_s1"])
    )

    return out


def parse_security_ids(text):
    mapping = {}
    for item in (text or "").replace("\n", ",").split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        symbol, security_id = item.split(":", 1)
        mapping[symbol.strip().upper()] = security_id.strip()
    return mapping


def mapping_from_csv(file_storage):
    raw = pd.read_csv(file_storage, low_memory=False)
    lower = {str(c).strip().lower(): c for c in raw.columns}

    def find_col(*names):
        for name in names:
            if name.lower() in lower:
                return lower[name.lower()]
        return None

    symbol_col = find_col(
        "SEM_TRADING_SYMBOL", "TRADING_SYMBOL",
        "SYMBOL", "SEM_CUSTOM_SYMBOL"
    )
    id_col = find_col(
        "SEM_SMST_SECURITY_ID", "SECURITY_ID",
        "SECURITYID", "SEM_SECURITY_ID"
    )

    if not symbol_col or not id_col:
        raise ValueError(
            "CSV में symbol/security ID columns नहीं मिले। "
            "Dhan scrip-master CSV upload करें।"
        )

    return {
        str(symbol).strip().upper(): str(security_id).replace(".0", "").strip()
        for symbol, security_id in zip(raw[symbol_col], raw[id_col])
        if pd.notna(symbol) and pd.notna(security_id)
    }


def scan_one(token, symbol, security_id, timeframe):
    if timeframe == "2 minute":
        candles = make_2m(fetch_intraday(token, security_id, "1"))
    else:
        candles = make_5m_closed(fetch_intraday(token, security_id, "5"))

    if len(candles) < 25:
        raise DhanAPIError(
            f"Only {len(candles)} completed candles available; need at least 25."
        )

    previous_hlc = fetch_prev_hlc(token, security_id)
    data = indicators(candles, previous_hlc)
    row = data.iloc[-1]

    signal = (
        "CE" if bool(row["ce"])
        else "PE" if bool(row["pe"])
        else "—"
    )

    if signal == "CE":
        price_filter = "VWAP" if bool(row["ce_vwap"]) else "R1"
    elif signal == "PE":
        price_filter = "VWAP" if bool(row["pe_vwap"]) else "S1"
    else:
        price_filter = "—"

    def number(value):
        return "—" if pd.isna(value) else round(float(value), 2)

    return {
        "Stock": symbol,
        "Timeframe": timeframe,
        "Signal": signal,
        "Close": number(row["close"]),
        "RSI(14)": number(row["rsi"]),
        "Upper BB": number(row["upper"]),
        "Lower BB": number(row["lower"]),
        "VWAP": number(row["vwap"]),
        "R1": number(row["r1"]),
        "S1": number(row["s1"]),
        "Price filter": price_filter,
        "Confirmed candle (IST)": row["timestamp"].strftime("%H:%M:%S"),
    }


@app.route("/", methods=["GET", "POST"])
def index():
    client_id = os.getenv("DHAN_CLIENT_ID", "")
    token_env = os.getenv("DHAN_ACCESS_TOKEN", "")
    token_input = ""
    symbols_text = DEFAULT_SYMBOLS
    security_ids = ""
    timeframes = ["2 minute", "5 minute"]
    rows, errors = [], []
    message, message_class = "", "hint"

    if request.method == "POST":
        client_id = request.form.get("client_id", "").strip()
        submitted_token = request.form.get("access_token", "").strip()
        token = submitted_token or token_env
        symbols_text = request.form.get("symbols", DEFAULT_SYMBOLS)
        security_ids = request.form.get("security_ids", "")
        timeframes = request.form.getlist("timeframes") or [
            "2 minute", "5 minute"
        ]

        symbols = list(dict.fromkeys(
            symbol.strip().upper()
            for symbol in symbols_text.replace("\n", ",").replace(" ", ",").split(",")
            if symbol.strip()
        ))

        mapping = parse_security_ids(security_ids)
        upload = request.files.get("master_csv")

        if upload and upload.filename:
            try:
                mapping.update(mapping_from_csv(upload))
            except Exception as exc:
                message = f"Could not read instrument CSV: {exc}"
                message_class = "error"

        if not client_id or not token:
            message = "Dhan Client ID और Access Token भरें।"
            message_class = "error"
        elif not mapping:
            message = "Security IDs दें या Dhan scrip-master CSV upload करें।"
            message_class = "error"
        elif not message:
            for symbol in symbols:
                security_id = mapping.get(symbol)

                if not security_id:
                    for timeframe in timeframes:
                        errors.append({
                            "Stock": symbol,
                            "Timeframe": timeframe,
                            "Error": "Security ID mapping नहीं मिली।",
                        })
                    continue

                for timeframe in timeframes:
                    try:
                        rows.append(
                            scan_one(token, symbol, security_id, timeframe)
                        )
                    except Exception as exc:
                        errors.append({
                            "Stock": symbol,
                            "Timeframe": timeframe,
                            "Error": str(exc)[:350],
                        })

            message = (
                "Scan completed at "
                + datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
                + "."
            )
            message_class = "ok"

    columns = [
        "Stock", "Timeframe", "Signal", "Close", "RSI(14)",
        "Upper BB", "Lower BB", "VWAP", "R1", "S1",
        "Price filter", "Confirmed candle (IST)"
    ]

    return render_template_string(
        HTML,
        client_id=client_id,
        token_input=token_input,
        symbols_text=symbols_text,
        security_ids=security_ids,
        timeframes=timeframes,
        rows=rows,
        errors=errors,
        columns=columns,
        message=message,
        message_class=message_class,
        ce_count=sum(1 for row in rows if row["Signal"] == "CE"),
        pe_count=sum(1 for row in rows if row["Signal"] == "PE"),
        stocks_count=len(set(row["Stock"] for row in rows)),
    )


# PythonAnywhere WSGI loads this module.
if __name__ == "__main__":
    app.run(debug=True)
