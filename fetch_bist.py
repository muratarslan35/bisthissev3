# fetch_bist.py
import time
import requests
import pandas as pd
import yfinance as yf
from utils import (
    FALLBACK_SYMBOLS,
    calculate_rsi,
    detect_three_peaks
)

# ================= SAFE DOWNLOAD =================
def yf_download_safe(ticker, period, interval):
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False
        )
        if df is None or df.empty or "Close" not in df.columns:
            return None
        return df.dropna()
    except:
        return None

# ================= SYMBOL LIST =================
def get_bist_symbols():
    try:
        url = "https://api.isyatirim.com.tr/index/indexsectorperformance"
        r = requests.get(url, timeout=5)
        js = r.json()
        syms = []
        for item in js:
            for c in item.get("components", []):
                s = c.get("symbol")
                if s:
                    syms.append(s + ".IS")
        return list(dict.fromkeys(syms))
    except:
        print("[fetch_bist] API fail → FALLBACK")
        return FALLBACK_SYMBOLS.copy()

# ================= SINGLE SYMBOL =================
def fetch_one_symbol(sym):
    df_15 = yf_download_safe(sym, "7d", "15m")

    # 🔥 KRİTİK: 15m yoksa fallback olarak 1d kullan
    if df_15 is None:
        df_15 = yf_download_safe(sym, "60d", "1d")
        if df_15 is None:
            return None

    close = df_15["Close"]
    current_price = float(close.iloc[-1].item())  # FutureWarning giderildi

    try:
        rsi_series = calculate_rsi(close)
        rsi = float(rsi_series.iloc[-1].item())     # FutureWarning giderildi
    except:
        rsi = None

    last_signal = None
    if rsi is not None:
        if rsi < 30:
            last_signal = "AL"
        elif rsi > 70:
            last_signal = "SAT"

    return {
        "symbol": sym.replace(".IS", ""),
        "current_price": current_price,
        "RSI": rsi,  # app.py ile uyumlu
        "last_signal": last_signal,
        "three_peak_break": detect_three_peaks(close),
    }

# ================= MAIN FETCH =================
def fetch_bist_data():
    results = []
    for s in get_bist_symbols():
        try:
            rec = fetch_one_symbol(s)
            if rec:
                results.append(rec)
        except Exception as e:
            print("[fetch_bist]", s, e)
        time.sleep(0.1)

    return results
