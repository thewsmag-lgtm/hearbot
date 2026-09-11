import os
import sys
import time
import json
import requests
from datetime import datetime

# --- AYARLAR ---
HIVE_USERNAME = os.getenv("HIVE_USERNAME", "test_user")
POSTING_KEY = os.getenv("HIVE_POSTING_KEY", "test_key")
TOKEN = os.getenv("TOKEN", "DEC")
TRADE_AMOUNT_HIVE = float(os.getenv("TRADE_AMOUNT", "1"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))
TICK_SIZE = float(os.getenv("TICK_SIZE", "0.00000001"))

# Hive Engine API
HE_API = "https://api.hive-engine.com/rpc/contracts"

def log(message, level="INFO"):
    """Anlık log mesajı"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")
    sys.stdout.flush()

def safe_parse(value):
    """Güvenli float dönüşümü"""
    if value is None or value == '':
        return None
    try:
        return float(str(value).replace(',', '.'))
    except:
        return None

def get_order_book(token):
    """Hive Engine order book'u çek"""
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
        
        sell_orders = sell_response.get("result", [])
        buy_orders = buy_response.get("result", [])
        
        if not sell_orders or not buy_orders:
            return None, None
        
        best_ask = min([safe_parse(o["price"]) for o in sell_orders if safe_parse(o["price"])])
        best_bid = max([safe_parse(o["price"]) for o in buy_orders if safe_parse(o["price"])])
        
        return best_ask, best_bid
    except Exception as e:
        log(f"Order book hatası: {e}", "ERROR")
        return None, None

def get_my_open_orders(token):
    """Kullanıcının açık emirlerini çek"""
    try:
        # Açık alım emirleri
        open_buys = requests.post(HE_API, json={
            "jsonrpc": "2.0",
            "id": 10,
            "method": "find",
            "params": {
                "contract": "market",
                "table": "openBuyBook",
                "query": {"account": HIVE_USERNAME, "symbol": token},
                "limit": 1000
            }
        }, timeout=10).json().get("result", [])
        
        # Açık satım emirleri
        open_sells = requests.post(HE_API, json={
            "jsonrpc": "2.0",
            "id": 11,
            "method": "find",
            "params": {
                "contract": "market",
                "table": "openSellBook",
                "query": {"account": HIVE_USERNAME, "symbol": token},
                "limit": 1000
            }
        }, timeout=10).json().get("result", [])
        
        return open_buys + open_sells
    except Exception as e:
        log(f"Açık emirler çekilemedi: {e}", "ERROR")
        return []

def cancel_order(order_id):
    """Emir iptal et (SİMÜLASYON)"""
    log(f"   🗑️ Emir iptal ediliyor: {order_id}", "INFO")
    # Gerçek işlem için:
    # payload = {
    #     "contractName": "market",
    #     "contractAction": "cancel",
    #     "contractPayload": {"id": str(order_id)}
    # }
    # send_custom_json(payload)
    return True

def cancel_all_my_orders(token):
    """Tüm açık emirlerimi iptal et"""
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
    
    log(f"   ✅ {cancelled} emir iptal edildi", "SUCCESS")
    return cancelled

def place_buy_order(token, price, quantity):
    """Alım emri koy (SİMÜLASYON)"""
    log(f"📈 ALIM EMRİ: {quantity:.4f} {token} @ {price:.8f}", "SUCCESS")
    # Gerçek işlem için:
    # payload = {
    #     "contractName": "market",
    #     "contractAction": "buy",
    #     "contractPayload": {
    #         "symbol": token,
    #         "quantity": f"{quantity:.8f}",
    #         "price": f"{price:.8f}"
    #     }
    # }
    # send_custom_json(payload)
    return True

def place_sell_order(token, price, quantity):
    """Satım emri koy (SİMÜLASYON)"""
    log(f"📉 SATIM EMRİ: {quantity:.4f} {token} @ {price:.8f}", "SUCCESS")
    # Gerçek işlem için:
    # payload = {
    #     "contractName": "market",
    #     "contractAction": "sell",
    #     "contractPayload": {
    #         "symbol": token,
    #         "quantity": f"{quantity:.8f}",
    #         "price": f"{price:.8f}"
    #     }
    # }
    # send_custom_json(payload)
    return True

def run_bot():
    """Ana bot döngüsü"""
    log("=" * 60, "INFO")
    log("🤖 Hive Engine Top-of-Book Botu (Emir İptalli)", "INFO")
    log(f"Kullanıcı: {HIVE_USERNAME}", "INFO")
    log(f"Token: {TOKEN}", "INFO")
    log(f"İşlem miktarı: {TRADE_AMOUNT_HIVE} HIVE", "INFO")
    log(f"Fiyat adımı (tick): {TICK_SIZE}", "INFO")
    log(f"Kontrol aralığı: {CHECK_INTERVAL} saniye", "INFO")
    log("=" * 60, "INFO")
    log("️  SİMÜLASYON MODU - Gerçek emir koyulmuyor!", "WARNING")
    log("=" * 60, "INFO")
    
    cycle = 0
    orders_placed = 0
    orders_cancelled = 0
    
    while True:
        try:
            cycle += 1
            log(f"\n🔄 Döngü #{cycle}", "INFO")
            
            # 1. Önce eski emirleri iptal et
            log("🧹 Eski emirler temizleniyor...", "INFO")
            cancelled = cancel_all_my_orders(TOKEN)
            orders_cancelled += cancelled
            
            # 2. Order book çek
            best_ask, best_bid = get_order_book(TOKEN)
            
            if not best_ask or not best_bid:
                log("️  Order book boş, bekleniyor...", "WARNING")
                time.sleep(CHECK_INTERVAL)
                continue
            
            log(f"📊 Mevcut Order Book:", "INFO")
            log(f"   Best ASK: {best_ask:.8f}", "INFO")
            log(f"   Best BID: {best_bid:.8f}", "INFO")
            log(f"   Spread: %{((best_ask - best_bid) / best_bid * 100):.2f}", "INFO")
            
            # 3. DEC miktarını hesapla
            dec_quantity = TRADE_AMOUNT_HIVE / best_ask
            
            # 4. ALIŞ EMRİ: Best BID'in üzerine koy
            buy_price = best_bid + TICK_SIZE
            log(f"\n📈 Alım emri: {buy_price:.8f} (BID + {TICK_SIZE})", "INFO")
            place_buy_order(TOKEN, buy_price, dec_quantity)
            
            # 5. SATIŞ EMRİ: Best ASK'ın altına koy
            sell_price = best_ask - TICK_SIZE
            log(f" Satım emri: {sell_price:.8f} (ASK - {TICK_SIZE})", "INFO")
            place_sell_order(TOKEN, sell_price, dec_quantity)
            
            orders_placed += 2
            
            # 6. Beklenen kâr
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
