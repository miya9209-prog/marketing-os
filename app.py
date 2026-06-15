
import json
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import streamlit as st
from openai import OpenAI

st.set_page_config(
    page_title="MISHARP 광고문구 자동생성기",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------
# Session
# ---------------------------
if "ui_nonce" not in st.session_state:
    st.session_state.ui_nonce = 0
if "result" not in st.session_state:
    st.session_state.result = ""
if "loaded_notice" not in st.session_state:
    st.session_state.loaded_notice = False
if "show_load_uploader" not in st.session_state:
    st.session_state.show_load_uploader = False

CHANNELS = [
    ("sms", "SMS문자"),
    ("app_push", "앱푸시"),
    ("video_script", "동영상 원고"),
    ("insta_reels", "인스타 릴스"),
    ("insta_feed", "인스타 피드"),
    ("insta_cardnews", "인스타 카드뉴스 10장"),
    ("tiktok", "틱톡 피드"),
    ("youtube_shorts", "유튜브 쇼츠"),
    ("naver_clip", "네이버 클립"),
    ("shopping_live_shortclip", "쇼핑라이브 숏클립"),
    ("kakaostory", "카카오스토리"),
    ("kakaostyle", "카카오스타일"),
    ("blog_seo", "블로그 SEO"),
    ("review", "REVIEW"),
]
CHANNEL_LABELS = dict(CHANNELS)

# ---------------------------
# Styles
# ---------------------------
st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="stSidebarNav"], [data-testid="collapsedControl"]{
  display:none !important;
}
html, body, [class*="css"] {
  font-family: "Pretendard","Noto Sans KR",sans-serif;
}
.stApp{
  background: linear-gradient(180deg,#020617 0%, #030816 100%);
  color:#f8fafc;
}
.block-container{
  max-width:1240px;
  padding-top:2.8rem !important;
  padding-bottom:5rem;
}
.misharp-header{
  background:#f5f2f1;
  color:#251a2e;
  border-radius:26px;
  padding:34px 32px 28px 32px;
  box-shadow:0 8px 28px rgba(0,0,0,.18);
  margin-top:.4rem;
  margin-bottom:14px;
}
.misharp-header h1{
  margin:0;
  font-size:2.45rem;
  font-weight:900;
  line-height:1.12;
  letter-spacing:-0.03em;
}
.misharp-header p{
  margin:10px 0 0 0;
  color:#6b4f45;
  font-size:1.02rem;
}
.stButton > button,
.stDownloadButton > button,
a[data-testid="stLinkButton"],
div[data-testid="stPopover"] > button{
  width:100% !important;
  height:52px !important;
  min-height:52px !important;
  max-height:52px !important;
  border-radius:16px !important;
  border:1px solid #314156 !important;
  background:rgba(10,18,32,.72) !important;
  color:#fff !important;
  font-weight:800 !important;
  padding:0 16px !important;
  box-sizing:border-box !important;
}
div[data-testid="stPopover"]{
  width:100% !important;
}
div[data-testid="stTextInputRoot"] input,
div[data-testid="stTextArea"] textarea{
  border-radius:14px !important;
  background:rgba(31,41,55,.82) !important;
  color:#fff !important;
}
div[data-testid="stTextInputRoot"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder{
  color:#97a5b8 !important;
}
[data-testid="stFileUploaderDropzone"]{
  border:1px dashed #34455b !important;
  border-radius:18px !important;
  background:rgba(31,41,55,.82) !important;
}
div[data-testid="stCheckbox"] label p,
div[data-testid="stRadio"] label p,
label, .stMarkdown, .stCaption{
  color:#f8fafc !important;
}
hr.misharp-divider{
  border:none;
  border-top:1px solid rgba(52,69,91,.7);
  margin:18px 0;
}
.misharp-section-title{
  font-size:1.9rem;
  font-weight:900;
  letter-spacing:-0.03em;
  margin:0 0 12px 0;
  color:white;
}
.footer-fixed{
  position:fixed;
  right:16px;
  bottom:10px;
  z-index:999;
  text-align:right;
  font-size:11px;
  color:#94a3b8;
  opacity:.84;
  line-height:1.35;
}
.footer-fixed .line{
  white-space:nowrap;
}
.footer-fixed .links{
  margin-top:2px;
}
.footer-fixed a{
  color:#94a3b8;
  text-decoration:none;
  margin-left:6px;
}
.footer-fixed a:hover{
  text-decoration:underline;
}
/* force hide multipage sidebar/nav */
section[data-testid="stSidebar"]{display:none !important;}
div[data-testid="stSidebarNav"]{display:none !important;}
button[kind="header"]{display:none !important;}
/* custom link buttons for image/url */
.custom-link-btn{
  display:flex;
  align-items:center;
  justify-content:center;
  width:100%;
  height:52px;
  border-radius:16px;
  border:1px solid #314156;
  background:rgba(10,18,32,.72);
  color:#ffffff !important;
  text-decoration:none !important;
  font-weight:800;
  box-sizing:border-box;
}
.custom-link-btn:hover,
.custom-link-btn:active,
.custom-link-btn:focus,
.custom-link-btn:visited{
  background:rgba(10,18,32,.72);
  color:#ffffff !important;
  text-decoration:none !important;
  border:1px solid #314156;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Helpers
# ---------------------------
def ui_key(name: str) -> str:
    return f"{name}_{st.session_state.ui_nonce}"

def get_value(name: str, default=""):
    return st.session_state.get(ui_key(name), default)

def selected_channels():
    out = []
    for key, _label in CHANNELS:
        if st.session_state.get(ui_key(key), False):
            out.append(key)
    return out

def reset_all():
    st.session_state.result = ""
    st.session_state.show_load_uploader = False
    st.session_state.ui_nonce += 1

def sanitize_filename(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", value)
    value = value.strip("._-")
    return value[:40] or "work"

def current_payload():
    uploaded = st.session_state.get(ui_key("media"), []) or []
    media_names = [getattr(f, "name", "") for f in uploaded]
    return {
        "product_url": get_value("product_url", ""),
        "product_content": get_value("product_content", ""),
        "event_content": get_value("event_content", ""),
        "sms_mode": get_value("sms_mode", "단문"),
        "selected_channels": selected_channels(),
        "media_names": media_names,
    }


def fetch_product_page_context(url: str) -> str:
    url = (url or "").strip()
    if not url.startswith("http"):
        return ""
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"}
        res = requests.get(url, headers=headers, timeout=12)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        parts = []
        og = soup.find("meta", attrs={"property": "og:title"})
        if og and og.get("content"):
            parts.append(f"상품명/페이지 제목: {og.get('content').strip()}")
        for tag in soup.find_all(["h2","h3","strong","p","li"]):
            txt = tag.get_text(" ", strip=True)
            if not txt:
                continue
            if any(k in txt for k in ["[상품 포인트]", "[이 상품을 초이스한 이유입니다.]", "[원단", "[체형", "[이렇게 입는 날이 많아집니다]", "소재 :", "사이즈 TIP", "실측 사이즈"]):
                parts.append(txt)
            if len(parts) >= 18:
                break
        dedup=[]
        seen=set()
        for p in parts:
            if p not in seen:
                dedup.append(p); seen.add(p)
        return "\n".join(dedup[:18])
    except Exception:
        return ""

def compose_grounded_source(data: dict) -> str:
    sections = []
    entered = (data.get("product_content","") or "").strip()
    if entered:
        sections.append("[사용자 입력 상품/이벤트 내용]\n" + entered)
    page_ctx = fetch_product_page_context(data.get("product_url",""))
    if page_ctx:
        sections.append("[상품 URL에서 추출한 참고 정보]\n" + page_ctx)
    extra = (data.get("event_content","") or "").strip()
    if extra:
        sections.append("[이벤트 추가 정보]\n" + extra)
    return "\n\n".join(sections).strip()

def detect_primary_product_label(data: dict) -> str:
    source = compose_grounded_source(data)
    for line in source.splitlines():
        if line.startswith("상품명/페이지 제목:"):
            return line.split(":",1)[1].strip()
    return ""

def sanitize_output_against_source(text: str, data: dict) -> str:
    source = compose_grounded_source(data)
    if not source:
        return text
    if "셔츠" in source or "블라우스" in source:
        swaps = {
            "슬림핏 레이어드 티셔츠":"체크 셔츠",
            "슬림핏 레깅스":"체크 셔츠",
            "체형커버 원피스":"체크 셔츠",
            "세미부츠컷 팬츠":"체크 셔츠",
            "슬림핏 팬츠":"체크 셔츠",
            "원피스":"셔츠",
            "레깅스":"셔츠",
            "팬츠":"셔츠",
            "티셔츠":"셔츠",
        }
        for a,b in swaps.items():
            text = text.replace(a,b)
    label = detect_primary_product_label(data)
    if label:
        text = text.replace("[상품명]", label)
    return text

def base_context(data: dict) -> str:
    media_note = ", ".join(data.get("media_names", [])) if data.get("media_names") else "없음"
    grounded = compose_grounded_source(data)
    return f"""
[입력 정보]
상품 URL:
{data.get("product_url","")}

상품 근거 정보:
{grounded}

업로드 파일명 참고:
{media_note}

[절대 규칙]
- 상품명, 상품군, 카테고리를 절대 바꾸지 말 것
- URL/입력 정보에 없는 다른 상품군으로 바꾸지 말 것
- 셔츠를 티셔츠/레깅스/원피스/팬츠로 바꾸면 안 됨
- 근거가 부족하면 오답 추측 대신 "이 상품", "이 아이템"처럼 보수적으로 표현
"""


def misharp_master_strategy() -> str:
    return """
[미샵 콘텐츠 마스터 전략 V2]
- 상품을 팔지 말고, 고객의 문제 해결 결과를 팔 것
- 상품 소개로 시작하지 말 것
- 콘텐츠 흐름은 반드시 아래 구조를 우선 적용
  오해깨기 → 체형 고민 → 생활 상황 → 반전 정보 → 결과 → 상품 연결 → CTA
- 4050 여성의 실제 고민을 기준으로 작성
- '예쁘다'보다 '왜 필요한지', '왜 실패 확률이 낮은지', '왜 자주 손이 가는지'를 설명
- 고객은 상품을 저장하지 않고 해결책을 저장한다
- 저장, 공유, 프로필 방문, 사이트 유입, 구매를 목표로 작성

[반드시 포함할 관점]
1. 체형: 팔뚝, 뱃살, 허벅지, 종아리, 상체통통, 하체통통 중 상품에 맞는 고민
2. 상황: 출근룩, 여행룩, 모임룩, 학교방문룩, 학부모모임, 주말외출, 데일리룩 중 상품에 맞는 상황
3. 반전: 편한데 단정함, 가벼운데 핏이 살아남, 시원한데 비침 없음, 와이드인데 부해 보이지 않음 등
4. 결과: 날씬해 보임, 체형이 정리돼 보임, 코디 고민이 줄어듦, 자꾸 손이 감

[SEO/AEO/GEO 규칙]
- SEO: 상품군, 시즌, 상황, 체형, 연령 키워드를 자연스럽게 포함
- AEO: AI가 '누구에게 좋은 옷인가 / 어떤 체형에 좋은가 / 어떤 상황에 좋은가 / 왜 좋은가'를 바로 이해하게 작성
- GEO: 생성형 검색에 잡히도록 결론형 문장을 포함
  예: 이 팬츠는 하체커버가 필요한 4050 여성에게 적합합니다.
- 억지 키워드 반복 금지. 자연스러운 문맥 우선

[금지]
- 홈쇼핑 말투
- 과장광고
- 상품 스펙 나열
- 원단명만 나열
- 신조어/MZ 말투
- 상품군 오인
- 이모지 남발
"""


def prompt_for_channel(channel: str, data: dict) -> str:
    base = base_context(data)
    strategy = misharp_master_strategy()

    if channel == "sms":
        return f"""
당신은 미샵 SMS 카피라이터입니다. 모든 출력은 한국어로만 작성하세요.

{base}
{strategy}

[출력 형식]
단문이면 시안 3개만 출력.
장문이면 시안 3개만 출력.

[규칙]
- SMS 유형: {data.get("sms_mode","단문")}
- 단문문자는 반드시 "(광고)미샵♥"로 시작
- 문구 끝은 반드시 "▶"
- 시작과 끝 포함 전체 56자 이내
- 상품명/상품군 오인 금지
- 짧지만 체형, 상황, 결과 중 1개 이상 반영
- 장문문자는 아래 형식을 반드시 따를 것:
상담고정 제목 : (광고)미샵 "이벤트명"

이벤트 문구(연결 링크 등 포함)
"""

    if channel == "app_push":
        return f"""
당신은 4050 여성 패션 쇼핑몰 앱푸시 마케팅 전문가입니다.
모든 출력은 한국어로만 작성하세요.

{base}
{strategy}

[출력 형식]
아래 3타입을 모두 출력

[타입1]
헤드라인 : 30자 이내 5가지
광고문구 : 3종
광고)24시간 MD추천 10%할인 [상품명]
(푸시 문구 – 한글 50자 이내)
수신거부설정: 알림함-설정버튼

[타입2]
헤드라인 : 30자 이내 5가지
광고문구 : 3종
광고)주말한정 MD추천 10%할인 [상품명]
(푸시 문구 – 한글 50자 이내)
수신거부설정: 알림함-설정버튼

[타입3]
헤드라인 : 30자 이내 5가지
광고문구 : 3종
광고) [이벤트명] + 광고문구 + 수신거부설정: 알림함-설정버튼
총 100자 이내

[작성 원칙]
- 할인율보다 고객 고민을 먼저 말할 것
- 상황 공감 → 결과 → 행동 유도
- 좋아요 유도 금지, 클릭/확인/구매 전환 중심
"""

    if channel == "video_script":
        return f"""
당신은 미샵의 30초 숏폼 영상 원고 카피라이터입니다.
인스타 릴스, 유튜브 쇼츠, 네이버 클립에 함께 쓸 수 있는 원고를 작성하세요.

{base}
{strategy}

[출력 형식]
1. 헤드라인 10개
2. 썸네일 문구 10개
3. A타입 30초 원고
4. B타입 30초 원고
5. 저장 CTA 10개

[원고 구조]
후킹 → 문제 → 공감 → 정보 → 반전 → 결과 → 상품 → CTA

[카피 규칙]
- 한 줄 최대 10자 내외
- 한 문장 최대 15자 내외
- 자막 넣기 좋게 줄바꿈
- 첫 3초는 상품명이 아니라 오해깨기/의외의 사실로 시작
- 마지막은 좋아요가 아니라 저장, 댓글, 프로필 방문 유도
"""

    if channel == "insta_reels":
        return f"""
당신은 미샵 인스타 릴스 전문 카피라이터입니다.
조회수보다 저장, 공유, 프로필 방문, 구매전환을 목표로 작성하세요.

{base}
{strategy}

[출력 형식]
1. 릴스 주제 5개
2. 첫 3초 후킹 10개
3. 썸네일 문구 10개
4. 30초 릴스 카피 1개
5. 댓글 CTA 10개
6. 저장 CTA 10개

[릴스 카피 구조]
오해깨기
체형 고민
생활 상황
반전 정보
고객이 얻는 결과
상품 연결
저장/댓글 CTA

[작성 규칙]
- 상품명은 중후반 이후 1회만 등장
- 첫 줄은 반드시 공감 또는 반전
- 한 줄은 짧고 정확하고 임팩트 있게
- 4050 여성의 실제 말투와 고민 반영
"""

    if channel == "insta_cardnews":
        return f"""
당신은 미샵의 인스타 카드뉴스 기획자입니다.
10장 이미지 피드용 카드뉴스 카피를 작성하세요.

{base}
{strategy}

[출력 형식]
[1장]
제목:
본문:

[2장]
제목:
본문:

... [10장]까지 작성

[10장 구성]
1장: 강력한 후킹
2장: 대부분이 착각하는 내용
3장: 왜 그런지 이유
4장: 고객 공감 상황
5장: 전문가 팁
6장: 반전 정보
7장: 실전 적용 방법
8장: 상품 연결
9장: 활용 상황
10장: 저장 CTA

[카피 규칙]
- 한 카드 1메시지
- 제목은 15자 이내
- 본문은 최대 2문장
- 상품 소개가 아니라 저장하고 싶은 정보처럼 작성
"""

    if channel == "insta_feed":
        return f"""
당신은 미샵의 인스타 피드 캡션 전문 카피라이터입니다.
SEO, AEO, GEO를 반영한 인스타 피드 글을 작성하세요.

{base}
{strategy}

[출력 형식]
헤드라인

미샵 [상품명]

본문

이런 분께 추천합니다
✔ ...
✔ ...
✔ ...

상세한 상품정보는 이미지 태그 상품배너 클릭 또는 상단 프로필 링크 참조

일상도 스타일도 미샵처럼 심플하게

#미샵 #데일리룩 포함 해시태그 총 5개

[본문 구조]
공감 → 문제 → 이유 → 반전 → 결과 → 상품 연결 → 추천 대상

[SEO 키워드]
본문 초반 3줄 안에 상품군, 시즌, 상황형 키워드를 자연스럽게 넣을 것
예: 여름코디, 출근룩, 체형커버룩, 4050패션, 중년여성코디, 데일리룩

[규칙]
- 250~450자 내외
- 1~2문장 단위로 줄바꿈
- 감성 40%, 공감 30%, 정보 30%
- 광고보다 스타일 코치 느낌
"""

    if channel == "youtube_shorts":
        return f"""
당신은 미샵 유튜브 쇼츠 SEO/AEO 최적화 에디터입니다.
유튜브 검색과 쇼츠 추천에 걸릴 수 있도록 작성하세요.

{base}
{strategy}

[출력 형식]
1. 검색형 제목 10개
2. 최종 추천 제목 1개
3. 설명글
4. 해시태그 10개
5. 고정댓글 문구 3개

[제목 규칙]
- 100자 이내
- 검색 키워드 + 상황 키워드 + 공감 후킹 조합
- 예: 50대 여름코디, 하체커버 바지, 여름 출근룩, 팔뚝커버 가디건

[설명글 규칙]
- 첫 2줄 안에 핵심 검색 키워드 포함
- 누가, 왜, 어떤 상황에서 보면 좋은 영상인지 명확히 작성
- 마지막에 "상세한 상품정보는 영상 하단 상품배너 클릭" 포함
- 이모지 금지
"""

    if channel == "naver_clip":
        return f"""
당신은 미샵 네이버 클립 SEO 최적화 카피라이터입니다.
네이버 검색, 쇼핑 검색, 클립 추천에 유리하게 작성하세요.

{base}
{strategy}

[출력 형식]
1. 네이버 클립 제목 10개
2. 최종 추천 제목 1개
3. 클립 캡션
4. 해시태그 10개
5. 검색 키워드 10개

[제목 규칙]
- 질문형 우선
- 예: 50대도 반바지 입어도 될까요?
- 예: 통통체형은 와이드팬츠가 답일까요?
- 상품명보다 고객 질문을 먼저

[캡션 구조]
질문 → 오해깨기 → 이유 → 상품 연결 → 저장/방문 CTA

[필수]
- 4050 여성
- 상품군 키워드
- 체형 고민 키워드
- 상황 키워드
- 결론형 AEO 문장 1개
"""

    if channel == "shopping_live_shortclip":
        return f"""
당신은 미샵 쇼핑라이브 숏클립 판매전환 카피라이터입니다.
구매 직전 고객을 움직이는 짧은 캡션과 영상 카피를 작성하세요.

{base}
{strategy}

[출력 형식]
1. 숏클립 제목 10개
2. 20초 숏클립 원고
3. 쇼핑라이브 캡션
4. 구매 CTA 10개
5. 상품 배너 문구 5개

[구조]
문제 → 공감 → 반전 → 결과 → 상품 → 혜택 → 구매 CTA

[규칙]
- 저장보다 구매 전환 중심
- 그러나 과장/압박 금지
- "이런 분께 추천"을 반드시 포함
- 방송 중 바로 읽기 쉬운 짧은 문장
"""

    if channel == "kakaostory":
        return f"""
당신은 미샵 카카오스토리 감성형 캡션 카피라이터입니다.
4050 여성 고객이 카톡/스토리에서 편하게 읽고 공감하도록 작성하세요.

{base}
{strategy}

[출력 형식]
1. 카카오스토리 제목 5개
2. 카카오스토리 캡션 본문
3. 댓글 유도 문구 5개
4. 구매/방문 CTA 5개
5. 해시태그 5개

[본문 구조]
일상 이야기 → 고민 → 공감 → 해결 → 상품 연결 → 마무리

[규칙]
- 인스타보다 조금 더 따뜻하고 차분하게
- 너무 짧은 광고문 말투 금지
- 4050 고객이 친구에게 말하듯 자연스럽게
- "일상도 스타일도 미샵처럼 심플하게" 포함
"""

    if channel == "tiktok":
        return f"""
당신은 미샵 틱톡 피드 카피라이터입니다.
틱톡 특성에 맞게 빠르고 직관적인 문장으로 작성하세요.

{base}
{strategy}

[출력 형식]
1. 틱톡 헤드라인 10개
2. 틱톡 피드 15줄
3. 해시태그 5개
4. 댓글 CTA 5개

[규칙]
- 첫 2~3줄은 강하게
- 검색형/공감형 키워드 포함
- 빠른 템포
- 그래도 4050 여성 타깃을 벗어나지 말 것
- 하단에 "자세한 상품정보는 하단 상품 배너 또는 상단 프로필 링크 참조" 포함
- 하단에 "일상도 스타일도 미샵처럼, 심플하게! MISHARP" 포함
"""

    if channel == "kakaostyle":
        return f"""
당신은 미샵 카카오스타일 피드 카피라이터입니다.
카카오스타일 상품 피드에 맞게 정보형 + 생활형 요약으로 작성하세요.

{base}
{strategy}

[출력 형식]
후킹 헤드라인

상품명

150자 이내 상품 설명

상품 바로가기 ▼

일상도 스타일도 미샵처럼, 심플하게! MISHARP

해시태그 20개

[규칙]
- 150자 안에 상품군, 4050 공감 포인트, 활용 상황 또는 체형커버 포인트 포함
- 필수 해시태그: #미샵 #여성의류쇼핑몰 #중년여성패션 #ootd #데일리룩
- 상품군 오인 금지
"""

    if channel == "blog_seo":
        return f"""
당신은 미샵 블로그 SEO/AEO/GEO 콘텐츠 작가입니다.
검색 유입과 AI 추천에 유리한 블로그 글 구조를 작성하세요.

{base}
{strategy}

[출력 형식]
1. 블로그 제목 10개
2. 메타 설명 1개
3. H2 목차
4. 블로그 본문 초안
5. FAQ 5개
6. SEO 키워드 15개
7. AEO/GEO 핵심 답변 문장 5개

[본문 구조]
고객 질문으로 시작
오해깨기
체형/상황 문제
상품 선택 기준
상품 연결
이런 분께 추천
마무리 CTA

[규칙]
- 검색 키워드 자연 삽입
- FAQ는 실제 고객 질문처럼 작성
- 답변은 짧고 명확하게
- 과장 광고보다 선택 기준 중심
"""

    if channel == "review":
        return f"""
제시한 설명의 미샵 여성의류 상품에 대해
반드시 같은 상품군을 유지해서 작성하고, 상품군 오인 금지.
고객 구매를 도와줄 수 있는 생활 밀착형, 공감형 상품 사용 후기 작성.

{base}
{strategy}

[출력 규칙]
- 4050대 일반인 여성이 쓴 듯한 일상적 문체
- 배송받아서 처음 입어본 소감
- 50자에서 300자 내외 총 10개
- 긴글 5개, 짧은 글 5개
- 작성자 스펙은 키155cm~163cm, 체중 52kg~63kg 사이로 다양하게
- 후기글 앞에 각각 (키/몸무게) 넣고 시작
- 체형 대비 핏 만족감 반영
- 품질, 구매과정, 활용성, 가성비 반영
- ㅎㅎ, ~~, ^^ 등 자연스럽게 일부 사용
- 상품명 빼기
- 번호 없이 후기 10개만 출력
"""

    return base

def call_gpt(prompt: str) -> str:
    client = OpenAI()
    model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    response = client.responses.create(model=model_name, input=prompt)
    return response.output_text.strip()

def short_sms_cleanup(body: str) -> str:
    lines = []
    for raw in body.splitlines():
        s = raw.strip()
        if not s:
            continue
        if not s.startswith("(광고)미샵♥"):
            s = "(광고)미샵♥" + s
        if not s.endswith("▶"):
            s = s.rstrip("▶") + "▶"
        s = s.replace("(광고)미샵♥ ", "(광고)미샵♥")
        s = s[:56]
        if not s.endswith("▶"):
            s = s[:-1] + "▶" if len(s) >= 1 else "(광고)미샵♥▶"
        lines.append(s)
    return "\n".join(lines[:3])

def build_final_output(channel_outputs: dict, data: dict) -> str:
    parts = []
    for ch, label in CHANNELS:
        if ch not in channel_outputs:
            continue
        body = channel_outputs[ch].strip()
        if ch == "sms" and data.get("sms_mode") == "단문":
            body = short_sms_cleanup(body)
        if ch == "kakaostyle":
            url = data.get("product_url", "").strip()
            if url and "상품 바로가기 ▼" in body and url not in body:
                body = body.replace("상품 바로가기 ▼", f"상품 바로가기 ▼\n{url}", 1)
        body = sanitize_output_against_source(body, data)
        parts.append(f"==============================\n{label}\n==============================\n{body}")
    return "\n\n".join(parts)

# ---------------------------
# Header
# ---------------------------
st.markdown("""
<div class="misharp-header">
  <h1>MISHARP 광고문구 자동생성기</h1>
  <p>미샵 4050 여성 콘텐츠 · SEO/AEO/GEO · 매체별 카피 자동 생성기</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------
# Buttons
# ---------------------------
btn_cols = st.columns(5, gap="small")

with btn_cols[0]:
    if st.button("초기화", use_container_width=True):
        reset_all()
        st.rerun()

with btn_cols[1]:
    product_content = get_value("product_content", "")
    product_url = get_value("product_url", "")
    file_base = sanitize_filename(product_content[:24] if product_content else product_url)
    save_name = f"misharp_marketing_os_{file_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    st.download_button(
        "작업 저장",
        data=json.dumps(current_payload(), ensure_ascii=False, indent=2),
        file_name=save_name,
        mime="application/json",
        use_container_width=True,
    )

with btn_cols[2]:
    if st.button("작업 불러오기", use_container_width=True):
        st.session_state.show_load_uploader = not st.session_state.show_load_uploader

with btn_cols[3]:
    st.markdown('<a class="custom-link-btn" href="https://misharp-image-crop-v1.streamlit.app/" target="_blank">이미지추출</a>', unsafe_allow_html=True)

with btn_cols[4]:
    st.markdown('<a class="custom-link-btn" href="https://shor.kr" target="_blank">URL 단축</a>', unsafe_allow_html=True)

if st.session_state.show_load_uploader:
    load_file = st.file_uploader("작업 불러오기 파일 선택", type=["json"], key=ui_key("load_json"))
    if load_file:
        data = json.load(load_file)
        st.session_state[ui_key("product_url")] = data.get("product_url", "")
        st.session_state[ui_key("product_content")] = data.get("product_content", "")
        st.session_state[ui_key("event_content")] = data.get("event_content", "")
        st.session_state[ui_key("sms_mode")] = data.get("sms_mode", "단문")
        selected = set(data.get("selected_channels", []))
        for ch, _ in CHANNELS:
            st.session_state[ui_key(ch)] = ch in selected
        st.session_state.loaded_notice = True
        st.session_state.show_load_uploader = False

if st.session_state.loaded_notice:
    st.success("불러온 작업이 반영되었습니다.")
    st.session_state.loaded_notice = False

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# ---------------------------
# Input
# ---------------------------
left, right = st.columns([1.05, 0.95], gap="large")
with left:
    st.markdown('<div class="misharp-section-title">입력 정보</div>', unsafe_allow_html=True)
    st.text_input("상품 URL", key=ui_key("product_url"), placeholder="상품 URL 또는 이벤트 링크를 입력하세요")
    st.text_area("상품, 이벤트 주요 내용", key=ui_key("product_content"), height=240, placeholder="상품 원고, 상품 스펙, 소재, 핏, 컬러, 사이즈, USP, 이벤트 내용을 입력하세요")
    st.text_area("이벤트 추가 내용", key=ui_key("event_content"), height=120, placeholder="할인율, 기간, 쿠폰, 무료배송 등 추가 이벤트 내용을 입력하세요")

with right:
    st.markdown('<div class="misharp-section-title">이미지 등록</div>', unsafe_allow_html=True)
    st.file_uploader("파일 업로드", accept_multiple_files=True, key=ui_key("media"))
    st.caption("URL, 텍스트, 이미지 중 1가지 이상만 입력하면 출력 가능합니다.")

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# ---------------------------
# Channel selection
# ---------------------------
st.markdown('<div class="misharp-section-title" style="font-size:1.75rem;">출력 채널 선택</div>', unsafe_allow_html=True)

r1, r2, r3, r4 = st.columns(4)
with r1:
    st.checkbox("SMS 문자", key=ui_key("sms"))
    st.checkbox("앱푸시", key=ui_key("app_push"))
    st.checkbox("블로그 SEO", key=ui_key("blog_seo"))
with r2:
    st.checkbox("동영상 원고", key=ui_key("video_script"))
    st.checkbox("인스타 릴스", key=ui_key("insta_reels"))
    st.checkbox("인스타 피드", key=ui_key("insta_feed"))
    st.checkbox("인스타 카드뉴스 10장", key=ui_key("insta_cardnews"))
with r3:
    st.checkbox("틱톡 피드", key=ui_key("tiktok"))
    st.checkbox("유튜브 쇼츠", key=ui_key("youtube_shorts"))
    st.checkbox("네이버 클립", key=ui_key("naver_clip"))
    st.checkbox("쇼핑라이브 숏클립", key=ui_key("shopping_live_shortclip"))
with r4:
    st.checkbox("카카오스토리", key=ui_key("kakaostory"))
    st.checkbox("카카오스타일", key=ui_key("kakaostyle"))
    st.checkbox("REVIEW", key=ui_key("review"))

sms_col, _ = st.columns([0.28, 0.72])
with sms_col:
    st.radio("SMS 유형", ["단문", "장문"], key=ui_key("sms_mode"), horizontal=True)

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# ---------------------------
# Generate
# ---------------------------
if st.button("문구 생성", use_container_width=True):
    payload = current_payload()
    has_input = bool(payload["product_url"] or payload["product_content"] or payload["event_content"] or payload["media_names"])
    if not has_input:
        st.warning("URL, 텍스트, 이미지 중 하나 이상 입력해주세요.")
    elif not payload["selected_channels"]:
        st.warning("출력 채널을 하나 이상 선택해주세요.")
    else:
        try:
            outputs = {}
            with st.spinner("문구를 생성하고 있습니다..."):
                for ch in payload["selected_channels"]:
                    outputs[ch] = call_gpt(prompt_for_channel(ch, payload))
                st.session_state.result = build_final_output(outputs, payload)
        except Exception as e:
            st.error(f"생성 중 오류가 발생했습니다: {e}")

# ---------------------------
# Output
# ---------------------------
st.markdown('<div class="misharp-section-title" style="font-size:1.75rem; margin-top:16px;">생성 결과</div>', unsafe_allow_html=True)
st.text_area("결과", value=st.session_state.get("result", ""), height=540, label_visibility="collapsed")

st.download_button(
    "TXT 다운로드",
    data=st.session_state.get("result", ""),
    file_name=f"misharp_copy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
    mime="text/plain",
    use_container_width=False,
)

# ---------------------------
# Compact footer
# ---------------------------
st.markdown("""
<div class="footer-fixed">
  <div class="line">made by MISHARP COMPANY, MIYAWA. 2006. All rights reserved.</div>
  <div class="links"><a href="#">개인정보</a> | <a href="#">약관</a></div>
</div>
""", unsafe_allow_html=True)
