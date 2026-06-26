import os
import requests
import time
import sys
import xml.etree.ElementTree as ET
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
import translators as ts  # 🔥 차단 없는 초고속 번역 라이브러리

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SEC_EMAIL = os.environ.get("SEC_EMAIL", "your_default@email.com")

HEADERS = {'User-Agent': SEC_EMAIL}
seen_links = set()

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

def log_print(message):
    print(message)
    sys.stdout.flush()

# 💡 멈추지 않는 안전한 한글 번역 함수
def translate_to_korean(text):
    if not text or text == "No Items": return text
    try:
        # 카카오 번역 엔진을 사용하여 안정적으로 영어->한국어 번역 진행
        return ts.translate_text(text, from_language='en', to_language='ko', translator='kakao')
    except Exception:
        try:
            # 카카오가 일시적 응답이 없으면 구글 엔진으로 우회
            return ts.translate_text(text, from_language='en', to_language='ko', translator='google')
        except Exception:
            return text # 번역 실패 시 원문 유지

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
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=include&start=0&count=40&output=atom"
    try:
        response = requests.get(url, headers=HEADERS)
        log_print(f"⏰ SEC 서버 감시 중... 상태코드: {response.status_code}")
        
        if response.status_code != 200: return
        
        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)

        for entry in entries[:15]:
            try:
                title_text = entry.find('atom:title', ns).text  
                link_url = entry.find('atom:link', ns).attrib['href']
                summary_node = entry.find('atom:summary', ns)
                summary_text = summary_node.text if summary_node is not None else ""

                if link_url not in seen_links:
                    seen_links.add(link_url)
                    
                    # 제목에서 공시 종류(Form) 추출 (예: "8-K", "4", "10-Q")
                    form_type = title_text.split('-')[0].strip() if '-' in title_text else "Unknown"
                    
                    # 🎯 [핵심 필터링] 잡다한 공시는 무시하고 오직 수시공시(8-K)만 골라냅니다!
                    if form_type == '8-K':
                        full_content = title_text + " " + summary_text
                        positive_factors = extract_positive_factors(full_content)
                        
                        # 텍스트 번역 진행
                        ko_title_text = translate_to_korean(title_text)
                        ko_summary_text = translate_to_korean(summary_text)
                        
                        if positive_factors:
                            factors_str = ", ".join(positive_factors)
                            title_tag = f"🔥 *[초특급 호재 의심 8-K 포착]* 🔥\n⚠️ *핵심 호재 요인:* {factors_str}\n"
                        else:
                            title_tag = f"🚨 *[실시간 8-K 중요 공시]*\n"
                        
                        message = (
                            f"{title_tag}\n"
                            f"📝 *공시 제목:* {ko_title_text}\n"
                            f"📄 *한글 요약:* {ko_summary_text[:400]}\n"
                            f"🇺🇸 *영문 원문:* {summary_text[:200]}...\n\n"
                            f"🔗 *Link:* [SEC 원문보기]({link_url})"
                        )
                        log_print(f"📤 8-K 공시 발송 완료: {title_text[:30]}")
                        send_telegram_message(message)
            except Exception as inner_e:
                continue
                
    except Exception as e:
        log_print(f"❌ 전체 에러 발생: {e}")

def monitor_loop():
    log_print("🚀 SEC 8-K 실시간 한글 모니터링 루프 가동 완료...")
    while True:
        check_sec_filings()
        time.sleep(10)

class WebServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SEC 8-K Bot is fully functional.")

if __name__ == "__main__":
    log_print("🌐 백그라운드 스레드 및 웹서버 가동 시작...")
    monitor_thread = Thread(target=monitor_loop)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    server = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), WebServerHandler)
    server.serve_forever()
