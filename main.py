import os
import requests
import time
import sys  # 🔥 실시간 로그 강제 출력을 위해 추가
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

# 💡 로그를 즉시 화면에 밀어내는 전용 함수
def log_print(message):
    print(message)
    sys.stdout.flush()  # 🔥 메모리에 머물지 않고 Render 로그창에 즉시 즉시 출력하도록 강제 설정

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: 
        res = requests.post(url, json=payload)
        log_print(f"📡 텔레그램 서버 응답: {res.status_code} -> {res.text}")
    except Exception as e: 
        log_print(f"❌ 텔레그램 전송 중 예외 발생: {e}")

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
        log_print(f"⏰ SEC 데이터 요청 상태코드: {response.status_code}")
        
        if response.status_code != 200: 
            log_print(f"⚠️ SEC 서버 연결이 원활하지 않습니다. 응답내용: {response.text[:100]}")
            return
        
        data = response.json()
        # 구조가 바뀌었을 경우를 대비해 안전하게 딕셔너리 내부 확인
        filings = data.get('actions', [])
        if not filings and 'filings' in data:
            filings = data.get('filings', {}).get('recent', [])
        
        # 가져온 데이터가 리스트 형태가 아닐 경우 처리
        if not isinstance(filings, list):
            log_print("⚠️ SEC 공시 데이터 구조가 예상과 다릅니다.")
            return

        for filing in filings[:15]:
            if not isinstance(filing, dict): continue
            
            accession_num = filing.get('accessionNumber')
            form_type = filing.get('form')
            ticker = filing.get('ticker', 'N/A')
            company_name = filing.get('name', 'Unknown')
            
            if accession_num and accession_num not in seen_filings:
                seen_filings.add(accession_num)
                
                # 테스트 모드: 모든 공시 통과
                if form_type:
                    cik = filing.get('cik', '')
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
                    log_print(f"📤 텔레그램 발송 시도 종목: {ticker} ({form_type})")
                    send_telegram_message(message)
    except Exception as e:
        log_print(f"❌ 에러 발생: {e}")

def monitor_loop():
    log_print("🚀 SEC 호재 추출 모니터링 루프 시작...")
    while True:
        check_sec_filings()
        time.sleep(3)

class WebServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

if __name__ == "__main__":
    log_print("🌐 Render 전용 백그라운드 스레드 및 웹서버 가동 준비...")
    monitor_thread = Thread(target=monitor_loop)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    server = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), WebServerHandler)
    server.serve_forever()
