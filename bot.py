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
MIN_SPREAD = float(os.getenv("MIN_SPREAD", "3.0"))

# Hive Engine API
HE_API = "https://api.hive-engine.com/rpc/contracts"

def log(message, level="INFO"):
    """Anlık log mesajı"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")
    sys.stdout.flush()  # Anlık gösterim için

def get_order_book(token):
    """Order book'u çek"""
    try:
        # Sell book (satış emirleri)
        sell_response = requests.post(HE_API, json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "find",
            "params": {
                "contract": "market",
                "table": "sellBook",
                "query": {"symbol": token},
                "limit": 10
            }
        }, timeout=10).json()
        
        # Buy book (alış emirleri)
        buy_response = requests.post(HE_API, json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "find",
            "params": {
                "contract": "market",
                "table": "buyBook",
                "query": {"symbol": token},
                "limit": 10
            }
        }, timeout=10).json()
        
        sell_orders = sell_response.get("result", [])
        buy_orders = buy_response.get("result", [])
        
        if not sell_orders or not buy_orders:
            return None, None, [], []
        
        best_ask = min([float(o["price"]) for o in sell_orders])
        best_bid = max([float(o["price"]) for o in buy_orders])
        
        return best_ask, best_bid, sell_orders, buy_orders
    except Exception as e:
        log(f"Order book çekilemedi: {e}", "ERROR")
        return None, None, [], []

def send_custom_json(payload):
    """Hive Engine'e Custom JSON gönder (SİMÜLASYON)"""
    log(f" İşlem gönderilecek:", "INFO")
    log(f"   {json.dumps(payload, indent=2)}", "INFO")
    
    # ⚠️ GERÇEK İŞLEM İÇİN BU KISMI AÇ:
    # from beem import Hive
    # from beembase.operations import CustomJson
    # from beem.transactionbuilder import TransactionBuilder
    # 
    # hive = Hive(node="https://api.hive.blog", keys=[POSTING_KEY])
    # tx = TransactionBuilder(blockchain_instance=hive)
    # tx.appendOp(CustomJson(
    #     required_auths=[],
    #     required_posting_auths=[HIVE_USERNAME],
    #     id="ssc-mainnet1",
    #     json=json.dumps(payload)
    # ))
    # tx.appendWif(POSTING_KEY)
    # tx.sign()
    # result = tx.broadcast()
    # log(f"✅ İşlem gönderildi: {result}", "SUCCESS")
    # return result
    
    log("️  SİMÜLASYON: Gerçek işlem yapılmadı", "WARNING")
    return {"simulated": True}

def place_buy_order(token, price, quantity):
    """Alım emri"""
    payload = {
        "contractName": "market",
        "contractAction": "buy",
        "contractPayload": {
            "symbol": token,
            "quantity": f"{quantity:.8f}",
            "price": f"{price:.8f}"
        }
    }
    return send_custom_json(payload)

def place_sell_order(token, price, quantity):
    """Satım emri"""
    payload = {
        "contractName": "market",
        "contractAction": "sell",
        "contractPayload": {
            "symbol": token,
            "quantity": f"{quantity:.8f}",
            "price": f"{price:.8f}"
        }
    }
    return send_custom_json(payload)

def run_bot():
    """Ana bot döngüsü"""
    log("=" * 60, "INFO")
    log("DEC Arbitraj Botu Başlatıldı", "INFO")
    log(f"Kullanıcı: {HIVE_USERNAME}", "INFO")
    log(f"Token: {TOKEN}", "INFO")
    log(f"İşlem miktarı: {TRADE_AMOUNT_HIVE} HIVE", "INFO")
    log(f"Minimum spread: %{MIN_SPREAD}", "INFO")
    log(f"Kontrol aralığı: {CHECK_INTERVAL} saniye", "INFO")
    log("=" * 60, "INFO")
    log("⚠️  SİMÜLASYON MODU - Gerçek işlem yapılmıyor!", "WARNING")
    log("Gerçek işlem için bot.py'de yorum satırlarını kaldır", "WARNING")
    log("=" * 60, "INFO")
    
    cycle = 0
    while True:
        try:
            cycle += 1
            log(f"\n🔄 Döngü #{cycle} başlıyor...", "INFO")
            
            # Order book çek
            best_ask, best_bid, sell_orders, buy_orders = get_order_book(TOKEN)
            
            if not best_ask or not best_bid:
                log("⚠️  Order book boş, bekleniyor...", "WARNING")
                time.sleep(CHECK_INTERVAL)
                continue
            
            spread = ((best_ask - best_bid) / best_bid) * 100
            
            log(f"📊 Order Book:", "INFO")
            log(f"   Best ASK (en düşük satış): {best_ask:.8f}", "INFO")
            log(f"   Best BID (en yüksek alış): {best_bid:.8f}", "INFO")
            log(f"   Spread: %{spread:.2f}", "INFO")
            
            # Spread kontrolü
            if spread >= MIN_SPREAD:
                log(f"\n💰 ARBITRAJ FIRSATI! Spread: %{spread:.2f}", "SUCCESS")
                
                # DEC miktarı hesapla
                dec_quantity = TRADE_AMOUNT_HIVE / best_ask
                
                # Alım emri (best ask'in %0.5 üstü - hızlı dolması için)
                buy_price = best_ask * 1.005
                log(f"📈 Alım emri: {dec_quantity:.4f} {TOKEN} @ {buy_price:.8f}", "INFO")
                place_buy_order(TOKEN, buy_price, dec_quantity)
                
                # Satım emri (best bid'in %0.5 altı - hızlı dolması için)
                sell_price = best_bid * 0.995
                log(f"📉 Satım emri: {dec_quantity:.4f} {TOKEN} @ {sell_price:.8f}", "INFO")
                place_sell_order(TOKEN, sell_price, dec_quantity)
                
                beklenen_kar = (sell_price - buy_price) * dec_quantity
                log(f" Beklenen kâr: {beklenen_kar:.6f} HIVE", "INFO")
            else:
                log(f"️  Spread yetersiz (%{spread:.2f} < %{MIN_SPREAD})", "INFO")
            
            log(f"\n⏳ {CHECK_INTERVAL} saniye bekleniyor...", "INFO")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("\n🛑 Bot durduruldu", "INFO")
            break
        except Exception as e:
            log(f"\n❌ HATA: {e}", "ERROR")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_bot()
