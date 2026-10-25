import os
import time
import ccxt
import pandas as pd
from fastapi import FastAPI
from threading import Thread

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "5m Free Pure Python Bot is running!"}

def run_trading_bot():
    BITGET_API_KEY = os.getenv("BITGET_API_KEY")
    BITGET_SECRET = os.getenv("BITGET_SECRET")
    BITGET_PASSPHRASE = os.getenv("BITGET_PASSPHRASE")

    exchange = ccxt.bitget({
        'apiKey': BITGET_API_KEY,
        'secret': BITGET_SECRET,
        'password': BITGET_PASSPHRASE,
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })

    symbol = 'ETH/USDT:USDT'
    timeframe = '5m'  # 👈 1분봉에서 5분봉으로 변경
    amount = 0.01  # 테스트용 주문 수량

    print("🤖 5분봉 기준 100% 무료 자율 매매 봇이 가동을 시작한다...")

    last_checked_timestamp = 0

    while True:
        try:
            # 1. 비트겟에서 최근 5분봉 데이터 200개 조회
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=200)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            # 새로운 5분봉 마감 확인
            latest_timestamp = df['timestamp'].iloc[-1]
            if latest_timestamp == last_checked_timestamp:
                time.sleep(30)  # 5분봉이므로 체크 주기를 30초로 여유 있게 조절
                continue
            last_checked_timestamp = latest_timestamp

            # 2. 지표 연산 (100 EMA, VWAP, MACD)
            df['ema100'] = df['close'].ewm(span=100, adjust=False).mean()

            df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
            df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
            df['tp_vol'] = df['typical_price'] * df['volume']
            df['cum_tp_vol'] = df.groupby('date')['tp_vol'].cumsum()
            df['cum_vol'] = df.groupby('date')['volume'].cumsum()
            df['vwap'] = df['cum_tp_vol'] / df['cum_vol']

            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = exp1 - exp2
            df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()

            # 3. 중복 포지션 방지
            positions = exchange.fetch_positions([symbol])
            has_position = False
            for p in positions:
                if p['symbol'] == symbol and float(p['contracts']) > 0:
                    has_position = True
                    break

            if has_position:
                time.sleep(30)
                continue

            # 4. 크로스오버 신호 판정
            prev_macd = df['macd'].iloc[-2]
            prev_signal = df['signal'].iloc[-2]
            curr_macd = df['macd'].iloc[-1]
            curr_signal = df['signal'].iloc[-1]

            curr_close = df['close'].iloc[-1]
            curr_ema100 = df['ema100'].iloc[-1]
            curr_vwap = df['vwap'].iloc[-1]

            long_cond = (curr_close > curr_ema100) and (curr_close > curr_vwap) and (prev_macd <= prev_signal) and (curr_macd > curr_signal)
            short_cond = (curr_close < curr_ema100) and (curr_close < curr_vwap) and (prev_macd >= prev_signal) and (curr_macd < curr_signal)

            # 5. 주문 집행 (20배 레버리지 + TP + SL)
            exchange.set_leverage(20, symbol)

            if long_cond:
                print(f"[{pd.Timestamp.now()}] 🚀 5분봉 롱(Long) 진입 조건 충족!")
                exchange.create_market_buy_order(symbol, amount)
                
                tp_price = curr_close * (1 + 0.0035)
                sl_price = curr_close * (1 - 0.0020)
                exchange.create_order(symbol, 'limit', 'sell', amount, tp_price, {'reduceOnly': True})
                exchange.create_order(symbol, 'stop_market', 'sell', amount, params={'triggerPrice': sl_price, 'reduceOnly': True})

            elif short_cond:
                print(f"[{pd.Timestamp.now()}] 📉 5분봉 숏(Short) 진입 조건 충족!")
                exchange.create_market_sell_order(symbol, amount)
                
                tp_price = curr_close * (1 - 0.0035)
                sl_price = curr_close * (1 + 0.0020)
                exchange.create_order(symbol, 'limit', 'buy', amount, tp_price, {'reduceOnly': True})
                exchange.create_order(symbol, 'stop_market', 'buy', amount, params={'triggerPrice': sl_price, 'reduceOnly': True})

        except Exception as e:
            print(f"에러 발생: {e}")

        time.sleep(30)

@app.on_event("startup")
def startup_event():
    thread = Thread(target=run_trading_bot)
    thread.daemon = True
    thread.start()
