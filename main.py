import json
import time
import websocket
import threading
import os  # 🎯 렌더의 동적 포트를 가져오기 위해 추가
from http.server import BaseHTTPRequestHandler, HTTPServer

# 1. 렌더 우회용 가짜 웹 서버 설정
class 가짜웹서버(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("BOT_RUNNING", "utf-8"))

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def 가짜_포트_개방():
    # 🎯 렌더가 주는 환경변수 포트를 자동으로 찾고, 없으면 10000번을 씁니다.
    포트 = int(os.environ.get('PORT', 10000))
    서버 = HTTPServer(('0.0.0.0', 포트), 가짜웹서버)
    print(f"🌐 렌더 우회용 가짜 웹 서버 가동 완료 (포트: {포트})")
    서버.serve_forever()

# 2. 주식 수급 감시 로직
# ⚠️ 중요: 계속 튕긴다면 Finnhub.io에서 무료 가입 후 개인 키를 발급받아 교체하세요!
API_KEY = "d92jappr01qs541v3efgd92jappr01qs541v3eg0" 
주가_저장소 = {}

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
                print(f"\n🚨 [급등 포착] ${종목코드} | 현재가: ${현재_가격:.2f} ({변동률:+.1f}%)")
                이전_데이터['누적_거래량'] = 0
            else:
                이전_데이터['누적_거래량'] += 현재_거래량
            이전_데이터['직전_가격'] = 현재_가격

def 연결_성공(ws):
    print("✅ 미국 증시 실시간 수급 감시 시작...")
    인기_스몰캡들 = ["CTNT", "UXIN", "TOMZ", "ACUR", "GME"]
    for 종목 in 인기_스몰캡들:
        ws.send(json.dumps({"type":"subscribe", "symbol": 종목}))

def 개장_시_감시_시작():
    # 가짜 웹 서버를 백그라운드에서 실행
    우회스레드 = threading.Thread(target=가짜_포트_개방, daemon=True)
    우회스레드.start()

    # 🎯 [핵심 수정] 웹소켓이 끊어져도 프로그램이 완전히 끝나지 않도록 무한 루프로 감쌉니다.
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
        
        # 연결이 끊기거나 실패하면 5초 쉬고 프로그램 종료 없이 다시 접속 시도
        print("⏳ 서버 연결이 일시적으로 끊겼습니다. 5초 후 자동으로 재연결합니다...")
        time.sleep(5)

if __name__ == "__main__":
    개장_시_감시_시작()
