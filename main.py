import os
import time
import imaplib
import email
from email.header import decode_header
import ccxt

# 환경변수 불러오기
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
BITGET_API_KEY = os.getenv("BITGET_API_KEY")
BITGET_SECRET = os.getenv("BITGET_SECRET")
BITGET_PASSPHRASE = os.getenv("BITGET_PASSPHRASE")

# 비트겟 API 연결
exchange = ccxt.bitget({
    'apiKey': BITGET_API_KEY,
    'secret': BITGET_SECRET,
    'password': BITGET_PASSPHRASE,
    'enableRateLimit': True,
    'options': {'defaultType': 'swap'}  # 선물 거래
})

def check_mail_and_trade():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        # 읽지 않은 메일 검색
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
                    amount = 0.01  # 주문할 이더리움 수량 (테스트 시 소액 설정)

                    # 롱 진입
                    if "[ETH 20x] Long 진입" in subject:
                        print("🚀 Long 포지션 주문 제출 중...")
                        # 20배 레버리지 설정
                        exchange.set_leverage(20, symbol)
                        # 시장가 매수
                        order = exchange.create_market_buy_order(symbol, amount)
                        print("Long 주문 완료:", order['id'])

                    # 숏 진입
                    elif "[ETH 20x] Short 진입" in subject:
                        print("📉 Short 포지션 주문 제출 중...")
                        exchange.set_leverage(20, symbol)
                        # 시장가 매도
                        order = exchange.create_market_sell_order(symbol, amount)
                        print("Short 주문 완료:", order['id'])

        mail.logout()
    except Exception as e:
        print(f"오류 발생: {e}")

print("🤖 ETH 자동매매 봇이 Render에서 구동을 시작합니다...")
while True:
    check_mail_and_trade()
    time.sleep(5)  # 5초 간격으로 지메일 체크
