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
MIN_SPREAD_PERCENT = float(os.getenv("MIN_SPREAD", "5.0"))  # Minimum %5 spread

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
        # Satış emirleri (ASK)
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
        
        # Alış emirleri (BID)
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
            return None, None, [], []
        
        # En düşük satış fiyatı (best ASK)
        best_ask = min([safe_parse(o["price"]) for o in sell_orders if safe_parse(o["price"])])
        # En yüksek alış fiyatı (best BID)
        best_bid = max([safe_parse(o["price"]) for o in buy_orders if safe_parse(o["price"])])
        
        return best_ask, best_bid, sell_orders, buy_orders
    except Exception as e:
        log(f"Order book hatası: {e}", "ERROR")
        return None, None, [], []

def place_buy_order(token, price, quantity):
    """Alım emri koy"""
    log(f" ALIM EMRİ: {quantity:.4f} {token} @ {price:.8f}", "SUCCESS")
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
    """Satım emri koy"""
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
    log("🤖 Hive Engine Market Making Botu", "INFO")
    log(f"Kullanıcı: {HIVE_USERNAME}", "INFO")
    log(f"Token: {TOKEN}", "INFO")
    log(f"İşlem miktarı: {TRADE_AMOUNT_HIVE} HIVE", "INFO")
    log(f"Minimum spread: %{MIN_SPREAD_PERCENT}", "INFO")
    log(f"Kontrol aralığı: {CHECK_INTERVAL} saniye", "INFO")
    log("=" * 60, "INFO")
    log("⚠️  SİMÜLASYON MODU", "WARNING")
    log("=" * 60, "INFO")
    
    cycle = 0
    orders_placed = 0
    
    while True:
        try:
            cycle += 1
            log(f"\n🔄 Döngü #{cycle}", "INFO")
            
            # Order book çek
            best_ask, best_bid, sell_orders, buy_orders = get_order_book(TOKEN)
            
            if not best_ask or not best_bid:
                log("⚠️  Order book boş", "WARNING")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # Spread hesapla
            spread = ((best_ask - best_bid) / best_bid) * 100
            
            log(f"📊 Order Book:", "INFO")
            log(f"   Best ASK: {best_ask:.8f}", "INFO")
            log(f"   Best BID: {best_bid:.8f}", "INFO")
            log(f"   Spread: %{spread:.2f}", "INFO")
            
            # Spread yeterince büyükse emir koy
            if spread >= MIN_SPREAD_PERCENT:
                orders_placed += 1
                log(f"\n💰 Spread yeterli! (%{spread:.2f} >= %{MIN_SPREAD_PERCENT})", "SUCCESS")
                
                # DEC miktarını hesapla
                dec_quantity = TRADE_AMOUNT_HIVE / best_ask
                
                # Alım emri: Best BID'in %1 üstüne koy (daha rekabetçi)
                buy_price = best_bid * 1.01
                log(f"   Alım fiyatı: {buy_price:.8f} (BID + %1)", "INFO")
                place_buy_order(TOKEN, buy_price, dec_quantity)
                
                # Satım emri: Best ASK'ın %1 altına koy (daha rekabetçi)
                sell_price = best_ask * 0.99
                log(f"   Satım fiyatı: {sell_price:.8f} (ASK - %1)", "INFO")
                place_sell_order(TOKEN, sell_price, dec_quantity)
                
                # Beklenen kâr
                profit = (sell_price - buy_price) * dec_quantity
                log(f"   Beklenen kâr: {profit:.6f} HIVE", "INFO")
                log(f"   Toplam emir: {orders_placed}", "INFO")
            else:
                log(f"️  Spread yetersiz (%{spread:.2f} < %{MIN_SPREAD_PERCENT})", "INFO")
            
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
