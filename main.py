import os
import requests
import time
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SEC_EMAIL = os.environ.get("SEC_EMAIL", "your_default@email.com")

HEADERS = {'User-Agent': SEC_EMAIL}
seen_filings = set()

# 🔥 주가 상승에 막대한 영향을 미치는 초특급 호재 키워드 세트
GOOD_NEWS_KEYWORDS = {
    "merger": "기업 합병 (Merger)",
    "acquisition": "지분 및 자산 인수 (Acquisition)",
    "definitive agreement": "구속력 있는 주요 계약 체결 (Definitive Agreement)",
    "purchase": "대규모 자산/주식 매입 (Purchase)",
    "joint venture": "합작 투자 회사 설립 (Joint Venture)",
    "patent": "핵심 특허 취득 (Patent)",
    "fda": "FDA 승인 관련 (FDA Approval)",
    "spacex": "스페이스X 관련 호재 (SpaceX Related)"
}

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: 
        requests.post(url, json=payload)
    except Exception as e: 
        print(f"텔레그램 전송 실패: {e}")

def extract_positive_factors(text):
    detected_factors = []
    text_lower = text.lower()
    for keyword, korean_meaning in GOOD_NEWS_KEYWORDS.items():
        if keyword in text_lower:
            detected_factors.append(korean_meaning)
    return detected_factors

def check_sec_filings():
    url = "https://data.sec.gov/submissions/latest-filings.json"
    try:
        response = requests.get(url, headers=HEADERS)
        print(f"⏰ SEC 체크 중... 상태코드: {response.status_code}") # 3초마다 찍히는지 확인용 로그
        
        if response.status_code != 200: return
        
        data = response.json()
        filings = data.get('actions', [])
        
        for filing in filings[:15]:
            accession_num = filing.get('accessionNumber')
            form_type = filing.get('form')
            ticker = filing.get('ticker', 'N/A')
            company_name = filing.get('name')
            
            if accession_num not in seen_filings:
                seen_filings.add(accession_num)
                
                # 테스트 모드: 우선 모든 공시가 다 텔레그램으로 꽂히도록 설정
                if form_type:
                    cik = filing.get('cik')
                    doc_link = f"https://www.sec.gov/edgar/browse/?CIK={cik}"
                    
                    items = filing.get('items', '')
                    items_text = ", ".join([i.strip() for i in items.split(',')]) if items else "No Items"
                    
                    positive_factors = extract_positive_factors(items_text)
                    
                    if positive_factors:
                        factors_str = ", ".join(positive_factors)
                        title = f"🔥 *[초특급 호재 의심 종목 포착]* 🔥\n⚠️ *핵심 호재 요인:* {factors_str}\n"
                    else:
                        title = f"🚨 *[실시간 SEC 공시 알림]* ({form_type})\n"
                    
                    message = (
                        f"{title}\n"
                        f"🎫 *Ticker:* {ticker}\n"
                        f"🏢 *Company:* {company_name}\n"
                        f"📝 *Content:* {items_text}\n"
                        f"🔗 *Link:* [SEC 원문보기]({doc_link})"
                    )
                    send_telegram_message(message)
    except Exception as e:
        print(f"에러 발생: {e}")

# 3초마다 SEC를 감시하는 전용 독립 루프 함수
def monitor_loop():
    print("🚀 SEC 호재 추출 모니터링 루프 시작...")
    while True:
        check_sec_filings()
        time.sleep(3)

class WebServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

# Render가 프로그램을 실행할 때 실행되는 메인 시작 지점
if __name__ == "__main__":
    # 1. 텔레그램 모니터링 루프를 백그라운드(독립 스레드)에서 먼저 무조건 시작시킵니다.
    monitor_thread = Thread(target=monitor_loop)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # 2. 메인 스레드에서는 Render 서버용 웹서버를 실행하여 봇을 영원히 유지시킵니다.
    print("🌐 Render 웹서버 가동...")
    server = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), WebServerHandler)
    server.serve_forever()
