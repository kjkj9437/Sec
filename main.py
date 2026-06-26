import os
import requests
import time
import sys
import xml.etree.ElementTree as ET  # RSS(XML) 파싱용
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SEC_EMAIL = os.environ.get("SEC_EMAIL", "your_default@email.com")

# SEC는 RSS를 긁어갈 때도 무조건 User-Agent에 이메일을 요구합니다.
HEADERS = {'User-Agent': SEC_EMAIL}
seen_links = set()

# 🔥 초특급 호재 키워드 세트
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

def log_print(message):
    print(message)
    sys.stdout.flush()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: 
        res = requests.post(url, json=payload)
        log_print(f"📡 텔레그램 전송 결과: {res.status_code}")
    except Exception as e: 
        log_print(f"❌ 텔레그램 전송 실패: {e}")

def extract_positive_factors(text):
    detected_factors = []
    text_lower = text.lower()
    for keyword, korean_meaning in GOOD_NEWS_KEYWORDS.items():
        if keyword in text_lower:
            detected_factors.append(korean_meaning)
    return detected_factors

def check_sec_filings():
    # 💡 [주소 전면 교체] 절대 404가 나지 않는 SEC 공식 실시간 공시 RSS 주소입니다.
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=include&start=0&count=40&output=atom"
    try:
        response = requests.get(url, headers=HEADERS)
        log_print(f"⏰ SEC 서버 응답 상태코드: {response.status_code}")
        
        if response.status_code != 200: 
            log_print(f"⚠️ 에러 응답 내용: {response.text[:100]}")
            return
        
        # XML(Atom 피드) 구조 파싱
        root = ET.fromstring(response.content)
        
        # XML 네임스페이스 정의 (SEC 데이터 추출용)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)
        
        log_print(f"📊 현재 SEC에서 가져온 실시간 공시 수: {len(entries)}개")

        for entry in entries[:15]:
            try:
                title_text = entry.find('atom:title', ns).text  # 예: "8-K - Apple Inc. (0000320193)"
                link_url = entry.find('atom:link', ns).attrib['href']
                summary_node = entry.find('atom:summary', ns)
                summary_text = summary_node.text if summary_node is not None else ""

                if link_url not in seen_links:
                    seen_links.add(link_url)
                    
                    # 제목에서 공시 종류(Form)와 회사명 추출
                    # 대략 "8-K - 회사명" 구조로 옵니다.
                    form_type = title_text.split('-')[0].strip() if '-' in title_text else "Unknown"
                    
                    # 💡 테스트 모드: 모든 공시 통과 (8-K만 보려면 나중에 if form_type == '8-K': 로 변경)
                    if form_type:
                        positive_factors = extract_positive_factors(title_text + " " + summary_text)
                        
                        if positive_factors:
                            factors_str = ", ".join(positive_factors)
                            title_tag = f"🔥 *[초특급 호재 의심 종목 포착]* 🔥\n⚠️ *핵심 호재 요인:* {factors_str}\n"
                        else:
                            title_tag = f"🚨 *[실시간 SEC 공시 알림]* ({form_type})\n"
                        
                        message = (
                            f"{title_tag}\n"
                            f"📝 *공시 제목:* {title_text}\n"
                            f"📄 *요약 내용:* {summary_text[:300]}\n"
                            f"🔗 *Link:* [SEC 원문보기]({link_url})"
                        )
                        log_print(f"📤 텔레그램 발송 시도: {title_text[:30]}")
                        send_telegram_message(message)
            except Exception as inner_e:
                continue
                
    except Exception as e:
        log_print(f"❌ 전체 에러 발생: {e}")

def monitor_loop():
    log_print("🚀 SEC 호재 추출 모니터링 루프 시작...")
    while True:
        check_sec_filings()
        time.sleep(10)  # RSS 피드는 10초 주기가 가장 안전합니다.

class WebServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

if __name__ == "__main__":
    log_print("🌐 백그라운드 스레드 및 웹서버 가동 시작...")
    monitor_thread = Thread(target=monitor_loop)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    server = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), WebServerHandler)
    server.serve_forever()
