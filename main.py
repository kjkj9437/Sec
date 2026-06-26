import os
import requests
import time
from datetime import datetime
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
# 무료 구글 번역 라이브러리 추가
from googletrans import Translator

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SEC_EMAIL = os.environ.get("SEC_EMAIL", "your_default@email.com")

HEADERS = {'User-Agent': SEC_EMAIL}
seen_filings = set()
translator = Translator()

# 텔레그램 메시지 전송 함수
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except Exception as e: print(f"텔레그램 전송 실패: {e}")

# 번역 함수 (안전하게 에러 예외 처리)
def translate_to_korean(text):
    try:
        translated = translator.translate(text, src='en', dest='ko')
        return translated.text
    except Exception:
        return text # 번역 에러 시 원문 그대로 반환

# SEC 모니터링 메인 로직
def check_sec_filings():
    url = "https://data.sec.gov/submissions/latest-filings.json"
    try:
        response = requests.get(url, headers=HEADERS)
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
                
                # 중대 호재 공시인 8-K만 필터링
                if form_type == '8-K':
                    cik = filing.get('cik')
                    doc_link = f"https://www.sec.gov/edgar/browse/?CIK={cik}"
                    
                    # 💡 [업그레이드] 8-K 공시의 세부 주제(항목들)를 가져옵니다.
                    # 예: "Item 1.01 Entry into a Material Definitive Agreement"
                    items = filing.get('items', '')
                    if items:
                        items_list = [i.strip() for i in items.split(',')]
                        items_text = ", ".join(items_list)
                    else:
                        items_text = "세부 항목 없음"
                    
                    # 회사명과 세부 공시 주제를 한글로 번역
                    ko_company_name = translate_to_korean(company_name)
                    ko_items_text = translate_to_korean(items_text)
                    
                    # 메시지 구성
                    message = (
                        f"🚨 *[실시간 8-K 호재 포착]*\n\n"
                        f"🎫 *종목 티커:* {ticker}\n"
                        f"🏢 *회 사 명:* {ko_company_name}\n"
                        f"📝 *공시 내용:* {ko_items_text}\n"
                        f"🇺🇸 *원문 영문:* {items_text}\n"
                        f"🔗 *공시 링크:* [SEC 원문보기]({doc_link})"
                    )
                    send_telegram_message(message)
    except Exception as e:
        print(f"에러: {e}")

def monitor_loop():
    print("SEC 실시간 한글화 모니터링 루프 시작...")
    check_sec_filings()
    while True:
        check_sec_filings()
        time.sleep(3) # 3초마다 체크

# Render 무료 서버 유지용 더미 웹서버
class WebServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

if __name__ == "__main__":
    Thread(target=monitor_loop, daemon=True).start()
    server = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), WebServerHandler)
    server.serve_forever()
