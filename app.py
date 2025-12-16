from flask import Flask, jsonify, send_from_directory
import threading, time, requests
from datetime import datetime, timezone
from fetch_bist import fetch_bist_data
from utils import to_tr_timezone
from self_ping import start_self_ping
from signal_engine import safe_process_bist_data  # yeni ekleme

app = Flask(__name__)

# ================== GLOBALS ==================
LATEST_DATA = {"status": "init", "data": None, "timestamp": None}
data_lock = threading.Lock()

TELEGRAM_TOKEN = "8588829956:AAEK2-wa75CoHQPjPFEAUU_LElRBduC-_TU"
CHAT_IDS = [661794787]

sent_signals = {}        # { symbol: set(signal_keys) }
last_reset_date = None  # date object (TR)

# ================== TELEGRAM ==================
def telegram_send(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for cid in CHAT_IDS:
        try:
            payload = {
                "chat_id": cid,
                "text": text,
                "parse_mode": "HTML"
            }
            requests.post(url, json=payload, timeout=8)
        except Exception as e:
            app.logger.error(f"[TELEGRAM ERROR] {e}")

# ================== LOOP ==================
def update_loop():
    telegram_send("🤖 Sistem aktif – tarama başladı")

    while True:
        try:
            data = fetch_bist_data()
            # --- safe_process_bist_data ile tarama ---
            signals = safe_process_bist_data(data)

            # --- LATEST_DATA güncelle ---
            with data_lock:
                LATEST_DATA.update({
                    "status": "ok",
                    "timestamp": int(time.time()),
                    "data": data
                })

            # --- sinyalleri Telegram'a gönder ---
            for _, msg, _ in signals:
                telegram_send(msg)

        except Exception as e:
            app.logger.error(f"[LOOP ERROR] {e}")
        time.sleep(60)

# ================== START ==================
_started = False
@app.before_request
def start_bg():
    global _started
    if not _started:
        _started = True
        threading.Thread(target=update_loop, daemon=True).start()
        start_self_ping()

@app.route("/")
def dashboard():
    return send_from_directory("static", "dashboard.html")

@app.route("/api")
def api():
    with data_lock:
        return jsonify(LATEST_DATA)
