import os
import sys
import time
import json
import requests
from datetime import datetime
from beem import Hive

# --- AYARLAR ---
HIVE_USERNAME = os.getenv("HIVE_USERNAME", "test_user")
POSTING_KEY = os.getenv("HIVE_POSTING_KEY", "test_key")
TOKEN = os.getenv("TOKEN", "DEC")
TRADE_AMOUNT_HIVE = float(os.getenv("TRADE_AMOUNT", "0.1"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))
TICK_SIZE = float(os.getenv("TICK_SIZE", "0.00000001"))

# Hive Engine API
HE_API = "https://api.hive-engine.com/rpc/contracts"
HIVE_NODE = "https://api.hive.blog"

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")
    sys.stdout.flush()

def safe_parse(value):
    if value is None or value == '':
        return None
    try:
        return float(str(value).replace(',', '.'))
    except:
        return None

def get_order_book(token):
    try:
        sell_response = requests.post(HE_API, json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "find",
            "params": {
                "contract": "market",
                "table": "sellBook",
                "query": {"symbol": token},
                "limit": 1000
            }
        }, timeout=10).json()
        
        buy_response = requests.post(HE_API, json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "find",
            "params": {
                "contract": "market",
                "table": "buyBook",
                "query": {"symbol": token},
                "limit": 1000
            }
        }, timeout=10).json()
        
        sell_orders = sell_response.get("result") or []
        buy_orders = buy_response.get("result") or []
        
        if not sell_orders or not buy_orders:
            return None, None
        
        best_ask = min([safe_parse(o["price"]) for o in sell_orders if safe_parse(o["price"])])
        best_bid = max([safe_parse(o["price"]) for o in buy_orders if safe_parse(o["price"])])
        
        return best_ask, best_bid
    except Exception as e:
        log(f"Order book hatası: {e}", "ERROR")
        return None, None

def get_my_open_orders(token):
    try:
        buy_response = requests.post(HE_API, json={
            "jsonrpc": "2.0",
            "id": 10,
            "method": "find",
            "params": {
                "contract": "market",
                "table": "openBuyBook",
                "query": {"account": HIVE_USERNAME, "symbol": token},
                "limit": 1000
            }
        }, timeout=10).json()
        
        open_buys = buy_response.get("result") or []
        
        sell_response = requests.post(HE_API, json={
            "jsonrpc": "2.0",
            "id": 11,
            "method": "find",
            "params": {
                "contract": "market",
                "table": "openSellBook",
                "query": {"account": HIVE_USERNAME, "symbol": token},
                "limit": 1000
            }
        }, timeout=10).json()
        
        open_sells = sell_response.get("result") or []
        
        return open_buys + open_sells
    except Exception as e:
        log(f"Açık emirler çekilemedi: {e}", "ERROR")
        return []

def send_custom_json(payload):
    """Hive Engine'e Custom JSON gönder - DOĞRU YÖNTEM"""
    try:
        hive = Hive(node=HIVE_NODE, keys=[POSTING_KEY])
        result = hive.custom_json(
            id="ssc-mainnet1",
            json_data=json.dumps(payload),
            required_posting_auths=[HIVE_USERNAME]
        )
        return result
    except Exception as e:
        log(f"İşlem gönderilemedi: {e}", "ERROR")
        return None

def cancel_order(order_id):
    log(f"   ️ Emir iptal ediliyor: {order_id}", "INFO")
    
    payload = {
        "contractName": "market",
        "contractAction": "cancel",
        "contractPayload": {"id": str(order_id)}
    }
    
    result = send_custom_json(payload)
    
    if result:
        log(f"   ✅ Emir iptal edildi", "SUCCESS")
    else:
        log(f"   ❌ Emir iptal edilemedi", "ERROR")
    
    return result

def cancel_all_my_orders(token):
    open_orders = get_my_open_orders(token)
    
    if not open_orders:
        log("   İptal edilecek açık emir yok", "INFO")
        return 0
    
    log(f"   🧹 {len(open_orders)} açık emir bulundu, iptal ediliyor...", "INFO")
    
    cancelled = 0
    for order in open_orders:
        order_id = order.get("_id")
        if order_id:
            cancel_order(order_id)
            cancelled += 1
            time.sleep(1)
    
    log(f"   ✅ {cancelled} emir iptal edildi", "SUCCESS")
    return cancelled

def place_buy_order(token, price, quantity):
    log(f"📈 ALIM EMRİ: {quantity:.4f} {token} @ {price:.8f}", "SUCCESS")
    
    payload = {
        "contractName": "market",
        "contractAction": "buy",
        "contractPayload": {
            "symbol": token,
            "quantity": f"{quantity:.8f}",
            "price": f"{price:.8f}"
        }
    }
    
    result = send_custom_json(payload)
    
    if result:
        log(f"   ✅ Alım emri gönderildi", "SUCCESS")
    else:
        log(f"   ❌ Alım emri gönderilemedi", "ERROR")
    
    return result

def place_sell_order(token, price, quantity):
    log(f" SATIM EMRİ: {quantity:.4f} {token} @ {price:.8f}", "SUCCESS")
    
    payload = {
        "contractName": "market",
        "contractAction": "sell",
        "contractPayload": {
            "symbol": token,
            "quantity": f"{quantity:.8f}",
            "price": f"{price:.8f}"
        }
    }
    
    result = send_custom_json(payload)
    
    if result:
        log(f"   ✅ Satım emri gönderildi", "SUCCESS")
    else:
        log(f"   ❌ Satım emri gönderilemedi", "ERROR")
    
    return result

def run_bot():
    log("=" * 60, "INFO")
    log("🤖 Hive Engine Top-of-Book Botu (GERÇEK İŞLEM)", "INFO")
    log(f"Kullanıcı: {HIVE_USERNAME}", "INFO")
    log(f"Token: {TOKEN}", "INFO")
    log(f"İşlem miktarı: {TRADE_AMOUNT_HIVE} HIVE", "INFO")
    log(f"Fiyat adımı (tick): {TICK_SIZE}", "INFO")
    log(f"Kontrol aralığı: {CHECK_INTERVAL} saniye", "INFO")
    log("=" * 60, "INFO")
    log("️  GERÇEK İŞLEM MODU - Gerçek emirler koyulacak!", "WARNING")
    log("=" * 60, "INFO")
    
    cycle = 0
    orders_placed = 0
    orders_cancelled = 0
    
    while True:
        try:
            cycle += 1
            log(f"\n🔄 Döngü #{cycle}", "INFO")
            
            log("🧹 Eski emirler temizleniyor...", "INFO")
            cancelled = cancel_all_my_orders(TOKEN)
            orders_cancelled += cancelled
            
            best_ask, best_bid = get_order_book(TOKEN)
            
            if not best_ask or not best_bid:
                log("⚠️  Order book boş, bekleniyor...", "WARNING")
                time.sleep(CHECK_INTERVAL)
                continue
            
            log(f"📊 Mevcut Order Book:", "INFO")
            log(f"   Best ASK: {best_ask:.8f}", "INFO")
            log(f"   Best BID: {best_bid:.8f}", "INFO")
            log(f"   Spread: %{((best_ask - best_bid) / best_bid * 100):.2f}", "INFO")
            
            dec_quantity = TRADE_AMOUNT_HIVE / best_ask
            
            buy_price = best_bid + TICK_SIZE
            log(f"\n📈 Alım emri: {buy_price:.8f} (BID + {TICK_SIZE})", "INFO")
            place_buy_order(TOKEN, buy_price, dec_quantity)
            
            sell_price = best_ask - TICK_SIZE
            log(f"📉 Satım emri: {sell_price:.8f} (ASK - {TICK_SIZE})", "INFO")
            place_sell_order(TOKEN, sell_price, dec_quantity)
            
            orders_placed += 2
            
            profit = (sell_price - buy_price) * dec_quantity
            log(f"   Beklenen kâr: {profit:.6f} HIVE", "INFO")
            log(f"   Toplam koyulan emir: {orders_placed}", "INFO")
            log(f"   Toplam iptal edilen emir: {orders_cancelled}", "INFO")
            
            log(f"\n⏳ {CHECK_INTERVAL} saniye bekleniyor...", "INFO")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log(f"\n🛑 Bot durduruldu.", "INFO")
            log(f"   Toplam koyulan emir: {orders_placed}", "INFO")
            log(f"   Toplam iptal edilen emir: {orders_cancelled}", "INFO")
            break
        except Exception as e:
            log(f"\n❌ HATA: {e}", "ERROR")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_bot()
