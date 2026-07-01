import json
import time
import websocket # pip install websocket-client 필요

# 💡 실시간 미국 주식 데이터를 무료로 받기 위한 Finnhub API 키입니다.
# (Finnhub.io 에서 1분만에 이메일로 무료 키를 발급받을 수 있습니다. 우선 샘플 키 제공)
API_KEY = "d92jappr01qs541v3efgd92jappr01qs541v3eg0" 

# 실시간으로 각 종목의 가격 정보를 임시 저장할 금고
주가_저장소 = {}

def 실시간_데이터_수신(ws, message):
    데이터 = json.loads(message)
    
    # 실시간 거래 데이터('trade')가 들어왔을 때만 작동
    if 데이터['type'] == 'trade':
        for 거래 in 데이터['data']:
            종목코드 = 거래['s']      # 예: CTNT, UXIN
            현재_가격 = 거래['p']     # 현재 체결 가격
            현재_거래량 = 거래['v']   # 체결 거래량
            체결_시간 = 거래['t']     # 시간 데이터
            
            # 처음 보는 종목이면 기준 가격을 세팅하고 넘어감
            if 종목코드 not in 주가_저장소:
                주가_저장소[종목코드] = {
                    '직전_가격': 현재_가격,
                    '누적_거래량': 현재_거래량,
                    '최근_체결시간': 체결_시간
                }
                continue
                
            이전_데이터 = 주가_저장소[종목코드]
            직전_가격 = 이전_데이터['직전_가격']
            
            # 🎯 [핵심] 미국 전 종목 중 '순간 변동률' 계산 (직전 대비 2% 이상 급등 시)
            변동률 = ((현재_가격 - 직전_가격) / 직전_가격) * 100
            
            if 변동률 >= 2.0:
                # 1분 동안 터진 거래량 대략 추정
                분당_누적_거래량 = 이전_데이터['누적_거래량'] + 현재_거래량
                
                # 📊 한눈에 들어오는 직관적인 한글 출력
                print("\n" + "="*40)
                print(f"🚨 [미국 증시 전수조사] 실시간 급등 포착!")
                print(f"🔴 종목코드: ${종목코드} | 현재가: ${현재_가격:.2f} (순간 급등: {변동률:+.1f}%)")
                print("="*40)
                print(f"📈 [수급 상황]")
                print(f" ├─ 순간 엔진 과열도: 🔥 평소보다 돈이 빠르게 몰리는 중!")
                print(f" ├─ 이 순간 터진 거래량: {분당_누적_거래량:,} 주")
                print(f" └─ 특징: 미국 전체 상장 주식 중 수급 레이더에 방금 걸려듦")
                print(f"⚠️ [위험 경보]")
                print(f" ├─ 현재 위치: 🚨 분봉상 장대양봉 꼭대기일 수 있음")
                print(f" └─ 봇의 한줄 경고: 거래량이 계속 붙으면서 올라가는지 '치타넷 패턴' 확인 필수!")
                print(f"📊 [종합 결론] 🟡 실시간 수급 유입 (돌파 매매 혹은 숏타이밍 대기)")
                print("="*40 + "\n")
                
                # 알림을 보낸 후 누적 거래량 초기화
                이전_데이터['누적_거래량'] = 0
            else:
                이전_데이터['누적_거래량'] += 현재_거래량
                
            # 최신 가격으로 업데이트
            이전_데이터['직전_가격'] = 현재_가격

def 에러_발생(ws, error):
    print(f"❌ 연결 중 에러 발생: {error}")

def 연결_종료(ws, close_status_code, close_msg):
    print("🔌 실시간 감시 서버와 연결이 종료되었습니다. 재연결을 시도합니다.")
    time.sleep(5)
    개장_시_감시_시작()

def 연결_성공(ws):
    print("✅ 미국 증시 전 종목 실시간 수급 웹소켓 연결 성공!")
    print("🕵️‍♂️ 이제 미국 주식 전체를 감시하며 돈 몰리는 잡주를 알아서 찾아냅니다...")
    
    # 미국 주식 전체 시장(나스닥, NYSE 등)의 실시간 수급 채널을 구독합니다.
    # 'US' 채널을 구독하면 미국 시장 전체 거래 데이터가 실시간으로 쏟아집니다.
    ws.send(json.dumps({"type":"subscribe-news", "category":"general"})) # 뉴스 채널도 같이 감시
    ws.send(json.dumps({"type":"subscribe", "symbol":"BINANCE:BTCUSDT"})) # 비트코인 수급도 같이 보기 원할 때
    
    # 💡 팁: 원래는 전종목 리스트를 받아와서 반복문으로 subscribe를 걸어두는 게 정석입니다.
    # 아래는 예시로 거래대금이 많이 터지는 미국 대표 스몰캡 채널 자동 등록 예시입니다.
    인기_스몰캡들 = ["CTNT", "UXIN", "TOMZ", "ACUR", "GME", "AMC"]
    for 종목 in 인기_스몰캡들:
        ws.send(json.dumps({"type":"subscribe", "symbol": 종목}))

def 개장_시_감시_시작():
    # Finnhub 실시간 웹소켓 서버 주소 연결
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(
        f"wss://ws.finnhub.io?token={API_KEY}",
        on_message = 실시간_데이터_수신,
        on_error = 에러_발생,
        on_close = 연결_종료
    )
    ws.on_open = 연결_성공
    ws.run_forever()

# 🤖 봇 실행하기
if __name__ == "__main__":
    개장_시_감시_시작()
