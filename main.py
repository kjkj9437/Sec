import json
import time
import websocket
import threading
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

# ⚙️ [변경] 렌더 인바이런먼트(Environment)에 입력한 값을 자동으로 가져옵니다.
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = "d92jp11r01qs541v6570d92jp11r01qs541v657g"  

주가_저장소 = {}

# 1. 텔레그램 메시지 전송 함수
def 텔레그램_알림_전송(메시지):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 렌더 Environment에 TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID가 설정되지 않았습니다.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": 메시지
    }
    
    try:
        데이터 = json.dumps(payload).encode('utf-8')
        요청 = urllib.request.Request(
            url, 
            data=데이터, 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(요청, timeout=5) as 응답:
            pass
    except Exception as 에러:
        print(f"❌ 텔레그램 발송 중 에러 발생: {에러}")

# 2. 렌더 우회용 가짜 웹 서버
class 가짜웹서버(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("BOT_RUNNING", "utf-8"))

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

# 3. 주식 수급 감시 로직
def 실시간_데이터_수신(ws, message):
    데이터 = json.loads(message)
    if 데이터['type'] == 'trade':
        for 거래 in 데이터['data']:
            종목코드 = 거래['s']
            현재_가격 = 거래['p']
            현재_거래량 = 거래['v']
            
            if 종목코드 not in 주가_저장소:
                주가_저장소[종목코드] = {'직전_가격': 현재_가격, '누적_거래량': 현재_거래량}
                continue
                
            이전_데이터 = 주가_저장소[종목코드]
            변동률 = ((현재_가격 - 이전_데이터['직전_가격']) / 이전_데이터['직전_가격']) * 100
            
            if 변동률 >= 2.0:
                알림내용 = (
                    f"🚨 [미국 증시] 실시간 급등 포착!\n"
                    f"🔴 종목코드: ${종목코드}\n"
                    f"💰 현재가격: ${현재_가격:.2f} ({변동률:+.1f}%)\n"
                    f"🔥 특징: 평소보다 돈이 빠르게 몰리는 중!"
                )
                print(f"\n{알림내용}")
                텔레그램_알림_전송(알림내용)
                이전_데이터['누적_거래량'] = 0
            else:
                이전_데이터['누적_거래량'] += 현재_거래량
            이전_데이터['직전_가격'] = 현재_가격

def 연결_성공(ws):
    print("✅ 미국 증시 실시간 수급 감시 시작...")
    인기_스몰캡들 = ["CTNT", "UXIN", "TOMZ", "ACUR", "GME"]
    for 종목 in 인기_스몰캡들:
        ws.send(json.dumps({"type":"subscribe", "symbol": 종목}))

def 주식_감시_백그라운드_루프():
    while True:
        try:
            print("🔄 실시간 주식 서버(Websocket) 연결 시도 중...")
            ws = websocket.WebSocketApp(
                f"wss://ws.finnhub.io?token={API_KEY}",
                on_message = 실시간_데이터_수신,
                on_open = 연결_성공
            )
            ws.run_forever()
        except Exception as 에러:
            print(f"❌ 감시 중 에러 발생: {에러}")
        
        time.sleep(5)

if __name__ == "__main__":
    감시스레드 = threading.Thread(target=주식_감시_백그라운드_루프, daemon=True)
    감시스레드.start()

    포트 = int(os.environ.get('PORT', 10000))
    서버 = HTTPServer(('0.0.0.0', 포트), 가짜웹서버)  # 오타 수정 완료
    print(f"🌐 [안정] 렌더 우회용 가짜 웹 서버가 메인으로 가동되었습니다. (포트: {포트})")
    서버.serve_forever()
