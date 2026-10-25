import os
import time
import imaplib
import email
from email.header import decode_header
import ccxt
from threading import Thread
from fastapi import FastAPI

# FastAPI 앱 생성 (Render 웹 서비스 포트 검증용)
app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "Bot is running!"}

# 지메일 및 비트겟 자동매매 로직
def run_bot():
    GMAIL_USER = os.getenv("GMAIL_USER")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
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

    print("🤖 ETH 자동매매 봇 백그라운드 루프 시작...")
    while True:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            mail.select("inbox")

            status, messages = mail.search(None, '(UNSEEN)')
            
            for num in messages[0].split():
                res, msg_data = mail.fetch(num, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 신규 메일 감지: {subject}")

                        symbol = "ETH/USDT:USDT"
                        amount = 0.01  # 주문 수량

                        if "[ETH 20x] Long 진입" in subject:
                            print("🚀 Long 포지션 주문 제출 중...")
                            exchange.set_leverage(20, symbol)
                            order = exchange.create_market_buy_order(symbol, amount)
                            print("Long 주문 완료:", order['id'])

                        elif "[ETH 20x] Short 진입" in subject:
                            print("📉 Short 포지션 주문 제출 중...")
                            exchange.set_leverage(20, symbol)
                            order = exchange.create_market_sell_order(symbol, amount)
                            print("Short 주문 완료:", order['id'])

            mail.logout()
        except Exception as e:
            print(f"오류 발생: {e}")
        
        time.sleep(5)

# 서버가 켜질 때 백그라운드에서 매매 봇 스레드 실행
@app.on_event("startup")
def startup_event():
    thread = Thread(target=run_bot)
    thread.daemon = True
    thread.start()
