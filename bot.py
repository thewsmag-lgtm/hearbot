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
MIN_SPREAD = float(os.getenv("MIN_SPREAD", "1.0"))

# Hive Engine API
HE_API = "https://api.hive-engine.com/rpc/contracts"

def log(message, level="INFO"):
    """Anlık log mesajı"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")
    sys.stdout.flush()

def safe_parse(value):
    """Güvenli float dönüşümü (virgül/nokta)"""
    if value is None or value == '':
        return None
    try:
        return float(str(value).replace(',', '.'))
    except:
        return None

def get_he_order_book(token):
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
        
        # En düşük satış fiyatı (ASK)
        best_ask = min([safe_parse(o["price"]) for o in sell_orders if safe_parse(o["price"])])
        # En yüksek alış fiyatı (BID)
        best_bid = max([safe_parse(o["price"]) for o in buy_orders if safe_parse(o["price"])])
        
        return best_ask, best_bid
    except Exception as e:
        log(f"HE order book hatası: {e}", "ERROR")
        return None, None

def get_td_price(token, trade_amount):
    """
    TribalDex havuzundan gerçek fiyat hesapla (AMM slippage dahil)
    x * y = k formülü ile
    """
    try:
        response = requests.post(HE_API, json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "find",
            "params": {
                "contract": "marketpools",
                "table": "pools",
                "query": {"tokenPair": f"SWAP.HIVE:{token}"},
                "limit": 1
            }
        }, timeout=10).json()
        
        pools = response.get("result", [])
        if not pools:
            return None, None, None
        
        pool = pools[0]
        base_qty = safe_parse(pool["baseQuantity"])  # SWAP.HIVE miktarı
        quote_qty = safe_parse(pool["quoteQuantity"])  # Token miktarı
        
        if not base_qty or not quote_qty or base_qty <= 0 or quote_qty <= 0:
            return None, None, None
        
        # AMM formülü: x * y = k
        k = base_qty * quote_qty
        
        # TD BUY: SWAP.HIVE ver, token al
        new_base = base_qty + trade_amount
        new_quote = k / new_base
        tokens_received = quote_qty - new_quote
        
        if tokens_received <= 0:
            return None, None, None
        
        td_buy_price = trade_amount / tokens_received  # 1 token için ödenen HIVE
        
        # TD SELL: Token ver, SWAP.HIVE al
        new_quote_sell = quote_qty + tokens_received
        new_base_sell = k / new_quote_sell
        hive_received = base_qty - new_base_sell
        
        td_sell_price = hive_received / tokens_received  # 1 token için alınan HIVE
        
        return td_buy_price, td_sell_price, pool
        
    except Exception as e:
        log(f"TD fiyat hatası: {e}", "ERROR")
        return None, None, None

def simulate_trade(action, token, price, quantity):
    """İşlem simülasyonu"""
    log(f"   {action}: {quantity:.4f} {token} @ {price:.8f}", "INFO")
    # Gerçek işlem için burayı aç:
    # payload = {
    #     "contractName": "market",
    #     "contractAction": action.lower(),
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
    log("🤖 DEC Arbitraj Botu Başlatıldı", "INFO")
    log(f"Kullanıcı: {HIVE_USERNAME}", "INFO")
    log(f"Token: {TOKEN}", "INFO")
    log(f"İşlem miktarı: {TRADE_AMOUNT_HIVE} HIVE", "INFO")
    log(f"Minimum kâr: %{MIN_SPREAD}", "INFO")
    log(f"Kontrol aralığı: {CHECK_INTERVAL} saniye", "INFO")
    log("=" * 60, "INFO")
    log("⚠️  SİMÜLASYON MODU - Gerçek işlem yapılmıyor!", "WARNING")
    log("=" * 60, "INFO")
    
    cycle = 0
    opportunities_found = 0
    
    while True:
        try:
            cycle += 1
            log(f"\n🔄 Döngü #{cycle}", "INFO")
            
            # 1. HE fiyatlarını çek
            he_ask, he_bid = get_he_order_book(TOKEN)
            
            if not he_ask or not he_bid:
                log("⚠️  HE order book boş", "WARNING")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # 2. TD fiyatlarını çek (slippage dahil)
            td_buy, td_sell, pool_data = get_td_price(TOKEN, TRADE_AMOUNT_HIVE)
            
            if not td_buy or not td_sell:
                log("⚠️  TD havuzu yok veya likidite yetersiz", "WARNING")
                time.sleep(CHECK_INTERVAL)
                continue
            
            log(f"📊 Fiyatlar:", "INFO")
            log(f"   HE ASK: {he_ask:.8f}", "INFO")
            log(f"   HE BID: {he_bid:.8f}", "INFO")
            log(f"   TD BUY: {td_buy:.8f}", "INFO")
            log(f"   TD SELL: {td_sell:.8f}", "INFO")
            
            # 3. Arbitraj hesapla
            # Senaryo 1: HE'den al, TD'de sat
            profit_he_to_td = ((td_sell - he_ask) / he_ask) * 100
            
            # Senaryo 2: TD'den al, HE'de sat
            profit_td_to_he = ((he_bid - td_buy) / td_buy) * 100
            
            log(f"📈 HE→TD kâr: %{profit_he_to_td:.2f}", "INFO")
            log(f"📉 TD→HE kâr: %{profit_td_to_he:.2f}", "INFO")
            
            # 4. Fırsat kontrolü
            if profit_he_to_td >= MIN_SPREAD:
                opportunities_found += 1
                log(f"\n💰 FIRSAT #{opportunities_found}: HE→TD (%{profit_he_to_td:.2f})", "SUCCESS")
                
                dec_quantity = TRADE_AMOUNT_HIVE / he_ask
                simulate_trade("BUY", TOKEN, he_ask, dec_quantity)
                simulate_trade("SELL", TOKEN, td_sell, dec_quantity)
                
                kar_hive = (td_sell - he_ask) * dec_quantity
                log(f"   Beklenen kâr: {kar_hive:.6f} HIVE", "INFO")
                
            elif profit_td_to_he >= MIN_SPREAD:
                opportunities_found += 1
                log(f"\n💰 FIRSAT #{opportunities_found}: TD→HE (%{profit_td_to_he:.2f})", "SUCCESS")
                
                dec_quantity = TRADE_AMOUNT_HIVE / td_buy
                simulate_trade("BUY_TD", TOKEN, td_buy, dec_quantity)
                simulate_trade("SELL_HE", TOKEN, he_bid, dec_quantity)
                
                kar_hive = (he_bid - td_buy) * dec_quantity
                log(f"   Beklenen kâr: {kar_hive:.6f} HIVE", "INFO")
                
            else:
                log("️  Arbitraj fırsatı yok", "INFO")
            
            log(f"\n {CHECK_INTERVAL} saniye bekleniyor...", "INFO")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log(f"\n Bot durduruldu. Toplam {opportunities_found} fırsat bulundu.", "INFO")
            break
        except Exception as e:
            log(f"\n❌ HATA: {e}", "ERROR")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_bot()
