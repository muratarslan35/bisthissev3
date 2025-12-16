from datetime import datetime, timezone
from utils import to_tr_timezone

# ==================================================
# SUCCESS TRACKING (IN-MEMORY - DAILY)
# ==================================================
success_tracker = {}

# ==================================================
# HELPERS
# ==================================================
def ma_text(v):
    if v == "above":
        return "🔼 yukarı kırdı"
    if v == "below":
        return "🔻 aşağı kırdı"
    if v == "golden_cross":
        return "⚔️ Golden Cross"
    if v == "death_cross":
        return "☠️ Death Cross"
    return "➡️ yatay"

def fmt_support_resistance(sr):
    if not sr:
        return "Destek/Direnç verisi yok"
    return (
        f"• 15m → D: {sr['15m']['support']} | R: {sr['15m']['resistance']}\n"
        f"• 1h → D: {sr['1h']['support']} | R: {sr['1h']['resistance']}\n"
        f"• 4h → D: {sr['4h']['support']} | R: {sr['4h']['resistance']}\n"
        f"• 1D → D: {sr['1D']['support']} | R: {sr['1D']['resistance']}"
    )

# ==================================================
# SUCCESS LOGIC
# ==================================================
def check_success(symbol, price):
    today = to_tr_timezone(datetime.now(timezone.utc)).date()
    if symbol not in success_tracker:
        return None
    day_data = success_tracker[symbol].get(today)
    if not day_data:
        return None
    if not day_data["hit"] and price >= day_data["target"]:
        day_data["hit"] = True
    return "BAŞARILI ✅" if day_data["hit"] else "BAŞARISIZ ❌"

def register_signal(symbol, price):
    today = to_tr_timezone(datetime.now(timezone.utc)).date()
    success_tracker.setdefault(symbol, {})
    if today not in success_tracker[symbol]:
        success_tracker[symbol][today] = {
            "entry": price,
            "target": price * 1.02,
            "hit": False
        }

# ==================================================
# MAIN ENGINE
# ==================================================
def process_signals(item):
    out = []

    symbol = item["symbol"]
    price = float(item["current_price"])
    rsi = round(item["RSI"], 2)
    trend = item["trend"]
    volume = item.get("volume")
    change = item.get("daily_change")

    ma = item.get("ma_breaks", {})
    sr = item.get("support_resistance")
    score = item.get("super_score")

    ts = to_tr_timezone(datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M:%S")

    success_status = check_success(symbol, price)

    ma_block = (
        f"MA Durumları:\n"
        f"{ma_text(ma.get('MA20'))} MA20\n"
        f"{ma_text(ma.get('MA50'))} MA50\n"
        f"{ma_text(ma.get('MA100'))} MA100\n"
        f"{ma_text(ma.get('MA200'))} MA200"
    )

    # ---------------- SUPER KOMBİNE ----------------
    if score and score >= 80:
        register_signal(symbol, price)
        msg = (
            f"Hisse Takip: {symbol}\n"
            f"💎🚀 SÜPER KOMBİNE SİNYAL\n"
            f"Puan: {score}/100\n"
            f"{'🎯 ' + success_status if success_status else ''}\n\n"
            f"Fiyat: {price} TL | RSI: {rsi}\n"
            f"Günlük Değişim: {change} | Hacim: {volume}\n\n"
            f"{ma_block}\n\n"
            f"📉 Destek – Direnç:\n{fmt_support_resistance(sr)}\n\n"
            f"Sinyal zamanı (TR): {ts}"
        )
        out.append((
            f"SUPER-{symbol}",
            msg,
            {
                "type": "super",
                "score": score,
                "success": success_status,
                "ma": ma,
                "support_resistance": sr,
                "price": price,
                "rsi": rsi,
                "volume": volume,
                "change": change
            }
        ))

    # ---------------- KOMBİNE ----------------
    if item.get("composite_signal") == "A":
        register_signal(symbol, price)
        out.append((
            f"COMBO-{symbol}",
            f"🚀 Kombine Sinyal - {symbol}",
            {
                "type": "combo",
                "success": success_status,
                "ma": ma,
                "support_resistance": sr,
                "price": price,
                "rsi": rsi,
                "volume": volume,
                "change": change
            }
        ))

    # ---------------- 3 TEPE ----------------
    if item.get("three_peak_break"):
        register_signal(symbol, price)
        out.append((
            f"3PEAK-{symbol}",
            f"🔥 3'lü Tepe Kırılımı - {symbol}",
            {
                "type": "3peak",
                "success": success_status,
                "ma": ma,
                "support_resistance": sr,
                "price": price,
                "rsi": rsi,
                "volume": volume,
                "change": change
            }
        ))

    return out

# ================== LOOP TARAMA ÖNCESİ ==================
def safe_process_bist_data(data_list):
    results = []
    if not data_list:
        return results
    for item in data_list:
        try:
            sigs = process_signals(item)
            if sigs:
                results.extend(sigs)
        except Exception:
            continue
    return results

# ================== DASHBOARD MAPPING ==================
def map_signals_for_dashboard(signal_list):
    """
    process_signals() çıktısını frontend dashboard'un DATA array formatına çevirir.
    Mevcut tüm özellikler korunur.
    """
    dashboard_data = []

    for sig in signal_list:
        for _, msg, info in [sig]:
            item = {}
            item["symbol"] = _.split("-")[-1]  # SUPER-XYZ -> XYZ
            item["current_price"] = info.get("price") or 0
            item["RSI"] = info.get("rsi")
            item["volume"] = info.get("volume")
            item["daily_change"] = info.get("change")
            item["composite_signal"] = True if info.get("type") == "combo" else False
            item["three_peak_break"] = True if info.get("type") == "3peak" else False
            item["super_score"] = info.get("score") if info.get("type") == "super" else None
            item["success_label"] = info.get("success")
            item["ma_breaks"] = info.get("ma") or {}
            item["support_resistance"] = info.get("support_resistance") or {}
            dashboard_data.append(item)

    return dashboard_data
