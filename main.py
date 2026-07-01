import json
import time
import websocket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# 💡 [무료 꼼수] 렌더(Render)가 포트 안 열렸다고 화내지 못하게 가짜 웹페이지를 여는 함수
class 가짜웹서버(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("BOT_RUNNING", "utf-8"))

def 가짜_포트_개방():
    # 렌더는 10000번 포트나 환경변수로 지정된 포트를 감시합니다.
    서버 = HTTPServer(('0.0.0.0', 10000), 가짜웹서버)
    print("🌐 렌더 우회용 가짜 웹 서버 가동 완료 (포트: 10000)")
    서버.serve_forever()

# --- 여기부터는 아까 드린 주식 스캐너 로직 그대로 ---
API_KEY = "d92jappr01qs541v3efgd92jappr01qs541v3eg0" # 내 무료 핀허브 키로 교체 필수
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
                print(f"💡 '치타넷 패턴' 수급 유입 중! 분할 매수 타점 확인하세요.")
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
    # 🎯 [핵심] 주식 감시와 가짜 웹페이지 개방을 '동시에' 실행합니다.
    우회스레드 = threading.Thread(target=가짜_포트_개방, daemon=True)
    우회스레드.start()

    ws = websocket.WebSocketApp(
        f"wss://ws.finnhub.io?token={API_KEY}",
        on_message = 실시간_데이터_수신,
        on_open = 연결_성공
    )
    ws.run_forever()

if __name__ == "__main__":
    개장_시_감시_시작()
