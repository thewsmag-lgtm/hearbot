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
TICK_SIZE = float(os.getenv("TICK_SIZE", "0.00000001"))  # Fiyat adımı

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

def place_buy_order(token, price, quantity):
    """Alım emri koy (SİMÜLASYON)"""
    log(f"📈 ALIM EMRİ: {quantity:.4f} {token} @ {price:.8f}", "SUCCESS")
    # Gerçek işlem için bu kısmı aç:
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
    # Gerçek işlem için bu kısmı aç:
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
    log("🤖 Hive Engine Top-of-Book Botu", "INFO")
    log(f"Kullanıcı: {HIVE_USERNAME}", "INFO")
    log(f"Token: {TOKEN}", "INFO")
    log(f"İşlem miktarı: {TRADE_AMOUNT_HIVE} HIVE", "INFO")
    log(f"Fiyat adımı (tick): {TICK_SIZE}", "INFO")
    log(f"Kontrol aralığı: {CHECK_INTERVAL} saniye", "INFO")
    log("=" * 60, "INFO")
    log("⚠️  SİMÜLASYON MODU - Gerçek emir koyulmuyor!", "WARNING")
    log("=" * 60, "INFO")
    
    cycle = 0
    orders_placed = 0
    
    while True:
        try:
            cycle += 1
            log(f"\n🔄 Döngü #{cycle}", "INFO")
            
            # Order book çek
            best_ask, best_bid = get_order_book(TOKEN)
            
            if not best_ask or not best_bid:
                log("⚠️  Order book boş, bekleniyor...", "WARNING")
                time.sleep(CHECK_INTERVAL)
                continue
            
            log(f"📊 Mevcut Order Book:", "INFO")
            log(f"   Best ASK: {best_ask:.8f}", "INFO")
            log(f"   Best BID: {best_bid:.8f}", "INFO")
            log(f"   Spread: %{((best_ask - best_bid) / best_bid * 100):.2f}", "INFO")
            
            # DEC miktarını hesapla
            dec_quantity = TRADE_AMOUNT_HIVE / best_ask
            
            # ALIŞ EMRİ: Best BID'in üzerine koy (bir tick yukarı)
            # Böylece en üstte durur, ilk eşleşen olur
            buy_price = best_bid + TICK_SIZE
            log(f"\n📈 Alım emri koyulacak: {buy_price:.8f} (BID + {TICK_SIZE})", "INFO")
            place_buy_order(TOKEN, buy_price, dec_quantity)
            
            # SATIŞ EMRİ: Best ASK'ın altına koy (bir tick aşağı)
            # Böylece en üstte durur, ilk eşleşen olur
            sell_price = best_ask - TICK_SIZE
            log(f"📉 Satım emri koyulacak: {sell_price:.8f} (ASK - {TICK_SIZE})", "INFO")
            place_sell_order(TOKEN, sell_price, dec_quantity)
            
            orders_placed += 2
            log(f"   Toplam emir sayısı: {orders_placed}", "INFO")
            
            # Beklenen kâr (eğer her iki emir de dolarsa)
            profit = (sell_price - buy_price) * dec_quantity
            log(f"   Beklenen kâr (her iki emir dolarsa): {profit:.6f} HIVE", "INFO")
            
            log(f"\n {CHECK_INTERVAL} saniye bekleniyor...", "INFO")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log(f"\n Bot durduruldu. Toplam {orders_placed} emir koyuldu.", "INFO")
            break
        except Exception as e:
            log(f"\n❌ HATA: {e}", "ERROR")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_bot()
