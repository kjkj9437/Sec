import time
import yfinance as yf

def monitor_ticker(ticker_symbol):
    print(f"🚀 {ticker_symbol} 실시간 수급 모니터링 시작...")
    
    # 기본 종목 정보 (발행주식수 등) 최초 1회 로드
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info
    float_shares = info.get('floatShares', 1)  # 유통주식수
    avg_volume = info.get('averageVolume', 1)   # 평균 거래량
    
    prev_price = None

    while True:
        try:
            # 매초 가장 최신의 1분봉 데이터 가져오기
            data = ticker.history(period="1d", interval="1m")
            if data.empty:
                time.sleep(1)
                continue
                
            latest_bar = data.iloc[-1]
            current_price = latest_bar['Close']
            current_volume = latest_bar['Volume']
            high_price = latest_bar['High']
            low_price = latest_bar['Low']
            
            # 1. 급등 조건 감시 (예: 직전 가격 대비 2% 이상 순간 급등 시)
            if prev_price and (current_price >= prev_price * 1.02):
                
                # 지표 계산 데이터 가공
                rvol = current_volume / (avg_volume / 390) # 분당 평균 거래량 대비 현재 거래량 비율
                turnover = (current_volume / float_shares) * 100
                intraday_position = ((current_price - low_price) / (high_price - low_price + 1e-5)) * 100
                
                # 메시지 포맷팅 및 출력
                print(f"\n🔴 [급등 발견] ${ticker_symbol} | ${current_price:.2f}")
                print(f"📊 기회 신호:")
                print(f" ├─ RVOL: {rvol:.1f}x " + ("🔴 고점 과열" if rvol > 10 else "🟢 수급 진입"))
                print(f" ├─ 거래량: {current_volume/1000000:.1f}M주 | Turnover: {turnover:.2f}%")
                print(f" └─ Float: {float_shares/1000000:.1f}M")
                print(f"⚠️ 위험 체크:")
                print(f" ├─ 일중 위치: {intraday_position:.0f}% " + ("🔴 천장 근처" if intraday_position > 90 else "🟡 중간"))
                print(f" └─ 🚨 실시간 변동성 경보 (추격 주의)")
                print("-" * 30)
            
            prev_price = current_price
            time.sleep(1) # 1초마다 반복 감시
            
        except Exception as e:
            print(f"오류 발생: {e}")
            time.sleep(1)

# 테스트 실행 (예시: 치타넷 CTNT 감시)
# monitor_ticker("CTNT")
