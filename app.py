# app.py
import os
import threading
import time
import requests
from datetime import datetime, timezone
from flask import Flask, jsonify, send_from_directory
from fetch_bist import fetch_bist_data
from utils import to_tr_timezone
from self_ping import start_self_ping

app = Flask(__name__)

# ================= STATE =================
LATEST_DATA = []
LAST_SCAN_TS = 0
SYSTEM_STARTED = False
data_lock = threading.Lock()

# ================= ENV =================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_IDS = [int(x) for x in os.getenv("CHAT_IDS", "").split(",") if x]

# ================= TELEGRAM =================
def telegram_send(text):
    if not TELEGRAM_TOKEN or not CHAT_IDS:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for cid in CHAT_IDS:
        try:
            requests.post(url, json={"chat_id": cid, "text": text}, timeout=5)
        except:
            pass

# ================= MARKET =================
def market_open_status():
    now = to_tr_timezone(datetime.now(timezone.utc))
    if now.weekday() >= 5:
        return 0
    return 1 if (now.hour > 9 or (now.hour == 9 and now.minute >= 55)) and now.hour < 18 else 0

# ================= BACKGROUND =================
def background_loop():
    global LATEST_DATA, LAST_SCAN_TS, SYSTEM_STARTED

    SYSTEM_STARTED = True
    telegram_send("🤖 Sistem başlatıldı – tarama başladı")

    while True:
        try:
            data = fetch_bist_data()

            with data_lock:
                LATEST_DATA = data
                LAST_SCAN_TS = int(time.time())

            # 🔔 Telegram sinyal
            for s in data:
                if s.get("last_signal") in ("AL", "SAT"):
                    telegram_send(
                        f"📊 {s['symbol']}\n"
                        f"Fiyat: {s['current_price']}\n"
                        f"Sinyal: {s['last_signal']}\n"
                        f"RSI: {round(s.get('rsi_15', 0),2)}"
                    )

        except Exception as e:
            print("SCAN ERROR:", e)

        time.sleep(60)

# ================= AUTO START =================
threading.Thread(target=background_loop, daemon=True).start()
start_self_ping()

# ================= API =================
@app.route("/api")
def api():
    with data_lock:
        return jsonify({
            "system_active": int(SYSTEM_STARTED),
            "market_open": int(market_open_status()),
            "last_scan": int(LAST_SCAN_TS),
            "data": LATEST_DATA
        })

# ================= DASHBOARD =================
@app.route("/")
def dashboard():
    return send_from_directory("static", "dashboard.html")
