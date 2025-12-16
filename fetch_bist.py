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
    """
    Yahoo Finance'ten veri çekmeye çalışır.
    Veri yoksa None döner, hata atmaz.
    """
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
    except Exception:
        return None

# ================= SYMBOL LIST =================
def get_bist_symbols():
    """
    BIST sembollerini API'den çeker.
    API başarısızsa FALLBACK_SYMBOLS listesi döner.
    """
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
    except Exception:
        print("[fetch_bist] API fail → FALLBACK")
        return FALLBACK_SYMBOLS.copy()

# ================= SINGLE SYMBOL =================
def fetch_one_symbol(sym):
    """
    Tek bir sembolün verilerini çeker:
    - 15m / 7d veya fallback 1d / 60d
    - RSI ve 3 tepe kontrolü
    """
    df_15 = yf_download_safe(sym, "7d", "15m")

    # 🔥 fallback 1d kullan
    if df_15 is None:
        df_15 = yf_download_safe(sym, "60d", "1d")
        if df_15 is None:
            # artık log spamlamadan sessiz skip
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
    """
    Bütün BIST sembollerini dolaşır, fetch_one_symbol çağırır.
    Delist edilmiş semboller sessiz atlanır.
    """
    results = []
    for s in get_bist_symbols():
        try:
            rec = fetch_one_symbol(s)
            if rec:
                results.append(rec)
        except Exception as e:
            # loglama minimal, delist vs hataları sessiz
            print(f"[fetch_bist] {s} fetch error (ignored)")
        time.sleep(0.1)

    return results
