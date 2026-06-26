import os
import requests
import time
import sys
import re
import xml.etree.ElementTree as ET
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
import translators as ts

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SEC_EMAIL = os.environ.get("SEC_EMAIL", "your_trading_bot_admin@email.com")

session = requests.Session()
session.headers.update({'User-Agent': SEC_EMAIL})

seen_links = set()

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

def extract_company_name(title):
    if not title: return "알 수 없는 기업"
    try:
        if ' - ' in title:
            parts = title.split(' - ')
            name = parts[1] if len(parts) > 1 else parts[0]
            name = re.sub(r'\s*\([^)]*\)', '', name)
            return name.strip().upper()
        clean_title = re.sub(r'^\d+\s*-\s*', '', title)
        clean_title = re.sub(r'\s*\([^)]*\)', '', clean_title)
        return clean_title.strip().upper()
    except Exception:
        return "기업명 분석 보류"

def convert_to_real_doc_url(index_url):
    if "-index.htm" in index_url:
        base_url = index_url.replace("-index.htm", "")
        parts = base_url.split('/')
        if parts:
            accession_no = parts[-1]
            accession_no_clean = accession_no.replace("-", "")
            real_doc_url = index_url.replace(f"{accession_no}-index.htm", f"{accession_no_clean}/{accession_no}.htm")
            return real_doc_url
    return index_url

def crawl_real_sec_content(url):
    try:
        real_url = convert_to_real_doc_url(url)
        res = session.get(real_url, timeout=8)
        
        if res.status_code != 200:
            res = session.get(url, timeout=6)
            if res.status_code != 200: return ""
        
        html_content = res.text
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'</p>|<br\s*/?>|</div>|</td>', '\n', html_content, flags=re.IGNORECASE)
        
        plain_text = re.sub(r'<[^>]+>', '', html_content)
        plain_text = re.sub(r'\s+', ' ', plain_text)
        
        if "uses javascript" in plain_text.lower() or "browser" in plain_text.lower():
            return ""

        item_match = re.search(r'(Item\s+\d+\.\d+.*)', plain_text, re.IGNORECASE)
        if item_match:
            return item_match.group(1)[:400].strip()
        
        # 의미 있는 텍스트가 최소 40자 이상 있을 때만 반환
        if len(plain_text.strip()) > 40:
            return plain_text[:300].strip()
        return ""
    except Exception as e:
        log_print(f"⚠️ 원문 크롤링 실패: {e}")
        return ""

def translate_to_korean(text):
    if not text or text.strip() == "": return "내용 없음"
    safe_text = text[:250]
    try:
        return ts.translate_text(safe_text, from_language='en', to_language='ko', translator='kakao', timeout=4)
    except Exception:
        try:
            time.sleep(0.5)
            return ts.translate_text(safe_text, from_language='en', to_language='ko', translator='google', timeout=4)
        except Exception:
            return safe_text

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: 
        session.post(url, json=payload, timeout=5)
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
        response = session.get(url, timeout=6)
        if response.status_code != 200: return
        
        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)

        for entry in entries[:12]:
            try:
                title_text = entry.find('atom:title', ns).text  
                link_url = entry.find('atom:link', ns).attrib['href']
                summary_node = entry.find('atom:summary', ns)
                summary_text = summary_node.text if summary_node is not None else ""

                if link_url not in seen_links:
                    seen_links.add(link_url)
                    
                    is_target = False
                    form_type = "공시"
                    
                    if '8-K' in title_text:
                        is_target, form_type = True, "8-K 수시공시"
                    elif '6-K' in title_text:
                        is_target, form_type = True, "6-K 외인공시"
                    elif 'SC 13G' in title_text or 'SC 13D' in title_text:
                        is_target, form_type = True, "지분대량보유(5%↑)"
                    elif 'Form 4' in title_text:
                        if ' code: P ' in summary_text.lower() or 'purchase' in summary_text.lower():
                            is_target, form_type = True, "내부자 대량매수(Form 4)"
                    
                    if is_target:
                        company_name = extract_company_name(title_text)
                        log_print(f"🎯 [{company_name}] {form_type} 발견 -> 본문 파싱 가동")
                        
                        real_content = crawl_real_sec_content(link_url)
                        
                        # 💡 [보강 핵심] 만약 원문 크롤링이 실패해 비어있다면, 
                        # RSS 피드가 제공하는 기본 요약 메타데이터에서 찌꺼기를 제외한 줄만 뽑아 대입합니다.
                        if not real_content or len(real_content.strip()) < 5:
                            text_clean = re.sub(r'<[^>]+>', '', summary_text)
                            lines = []
                            for l in text_clean.split('\n'):
                                l_clean = l.strip()
                                if not l_clean: continue
                                # 단순 크기, 접수번호 정보 라인은 제외하고 알맹이 문자열만 취합
                                if "accno:" in l_clean.lower() or "size:" in l_clean.lower() or "filed:" in l_clean.lower():
                                    continue
                                lines.append(l_clean)
                            real_content = "\n".join(lines).strip() if lines else "상세 본문 요약 제한 (원문 링크를 참고하세요)"

                        full_content = title_text + " " + real_content
                        positive_factors = extract_positive_factors(full_content)
                        
                        ko_title_text = translate_to_korean(title_text)
                        ko_summary_text = translate_to_korean(real_content)
                        clean_summary_en = real_content[:140]
                        
                        if "Form 4" in form_type:
                            title_tag = f"💎 *[내부자 지분 매수 포착 (Form 4)]* 💎\n⚠️ *내용:* 임원진이 개인 자금으로 주식을 매수했습니다!\n"
                        elif "지분대량보유" in form_type:
                            title_tag = f"🐋 *[거물 기관 고래 탑승 (SC 13)]* 🐋\n⚠️ *내용:* 대형 기관이 지분 5% 이상을 신규 확보했습니다.\n"
                        elif positive_factors:
                            factors_str = ", ".join(positive_factors)
                            title_tag = f"🔥 *[초특급 호재 의심 {form_type} 포착]* 🔥\n⚠️ *핵심 요인:* {factors_str}\n"
                        else:
                            title_tag = f"🚨 *[실시간 {form_type}]*\n"
                        
                        # 어색했던 문구를 깔끔하게 정리
                        message = (
                            f"{title_tag}\n"
                            f"🏢 *대상 기업:* `{company_name}`\n"
                            f"📝 *공시 분류:* {form_type}\n"
                            f"📌 *공시 제목:* {ko_title_text}\n\n"
                            f"📄 *핵심 내용 요약(한글):*\n{ko_summary_text}\n\n"
                            f"🇺🇸 *영문 핵심 원문:*\n{clean_summary_en}...\n\n"
                            f"🔗 *Link:* [SEC 원문보기]({link_url})"
                        )
                        send_telegram_message(message)
                        time.sleep(1.5)
            except Exception as inner_e:
                continue
                
    except Exception as e:
        log_print(f"❌ 전체 에러 발생: {e}")

def monitor_loop():
    log_print("🚀 SEC 딥크롤링 우회 및 백업 통합 엔진 가동...")
    while True:
        check_sec_filings()
        time.sleep(14)

class WebServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"SEC Deep-Crawling Engine is running perfectly.")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()

if __name__ == "__main__":
    log_print("🌐 백그라운드 스레드 및 웹서버 가동...")
    monitor_thread = Thread(target=monitor_loop)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    server = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), WebServerHandler)
    server.serve_forever()
