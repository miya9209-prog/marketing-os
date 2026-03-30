
import json
import os
import re
from datetime import datetime

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
    ("insta_reels", "인스타 릴스 피드"),
    ("tiktok", "틱톡 피드"),
    ("youtube_shorts", "유튜브 쇼츠 피드"),
    ("kakaostyle", "카카오스타일"),
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

def base_context(data: dict) -> str:
    media_note = ", ".join(data.get("media_names", [])) if data.get("media_names") else "없음"
    return f"""
[입력 정보]
상품 URL:
{data.get("product_url","")}

상품, 이벤트 주요 내용:
{data.get("product_content","")}

이벤트 추가 정보:
{data.get("event_content","")}

업로드 파일명 참고:
{media_note}
"""

def prompt_for_channel(channel: str, data: dict) -> str:
    base = base_context(data)

    # Keep existing SMS / 앱푸시 unchanged
    if channel == "sms":
        return f"""
당신은 미샵 SMS 카피라이터입니다. 모든 출력은 한국어로만 작성하세요.

{base}

[출력 형식]
단문이면 시안 3개만 출력.
장문이면 시안 3개만 출력.

[규칙]
- SMS 유형: {data.get("sms_mode","단문")}
- 단문문자는 반드시 "(광고)미샵♥"로 시작
- 문구 끝은 반드시 "▶"
- 시작과 끝 포함 전체 56자 이내
- 후킹성, 신선함, 긴박감 반영
- 장문문자는 아래 형식을 반드시 따를 것:
상담고정 제목 : (광고)미샵 "이벤트명"

이벤트 문구(연결 링크 등 포함)
"""
    if channel == "app_push":
        return f"""
당신은 4050 여성 패션 쇼핑몰 앱푸시 마케팅 전문가입니다.
모든 출력은 한국어로만 작성하세요.

{base}

[공통 작성 원칙]
- 할인율을 첫 문장에 바로 노출하지 말 것
- 과도한 느낌표, 자극적인 홈쇼핑 말투 금지
- 정보 나열형 문구, 광고 티가 강한 문구 금지
- 광고내용에 상품명은 [ ]로 구분. 상품명은 광고문구에 1번만 들어가기
- 문구 구조는 상황 공감 → 이유 제시 → 행동 유도

[출력 형식]
아래 3타입을 모두 출력

[타입1]
헤드라인 : 30자 이내(5가지 시안 제안)
광고문구 : 3종 제안
광고)24시간 MD추천 10%할인 [상품명]
(푸시 문구 – 한글 50자 이내)
수신거부설정: 알림함-설정버튼

[타입2]
헤드라인 : 30자 이내(5가지 시안 제안)
광고문구 : 3종 제안
광고)주말한정 MD추천 10%할인 [상품명]
(푸시 문구 – 한글 50자 이내)
수신거부설정: 알림함-설정버튼

[타입3]
헤드라인 : 30자 이내(5가지 시안 제안)
광고문구(3종 제안) : 광고) [이벤트명] + 광고문구 + 수신거부설정: 알림함-설정버튼 ->총 100자 이내
"""

    # Replaced with uploaded AI-optimized prompts
    if channel == "youtube_shorts":
        return f"""
유튜브 검색수 상승과 유튜브 쇼츠 노출 최적화를 위한 유튜브 쇼츠 컨텐츠 피드 작성 요청해.
모든 출력은 한국어로만 작성하고, 결과는 복붙 가능하게 바로 출력해.

{base}

-타이틀 : 100자 이내 후킹성 강한 타이틀 작성
-타이틀 구성 : 검색량 높은 핵심 키워드 + 상황형 키워드 + 공감형 후킹 문장 조합
-타이틀 마지막에 해시태그 5개 넣기 (#미샵 포함)
-설명 피드 :
 상품내용을 바탕으로 4050 여성의 공감형 고민, 검색형 질문, TPO를 담아 설명글 작성
 "누가 왜 이 영상을 보게 되는지"가 느껴지게 작성
 유튜브 검색에 반영될 수 있도록 아래 요소를 자연스럽게 포함
 1. 상품군 키워드
 2. 체형 고민 키워드
 3. 상황형 키워드(출근룩, 모임룩, 학교방문룩, 여행룩, 데일리룩 등)
 4. 연령 공감 키워드(4050여성, 40대코디, 50대코디 등)
-첫 2줄 안에는 검색형 핵심 키워드가 반드시 들어가야 함
-본문은 단순 광고보다 "왜 필요한지", "어떤 분께 잘 맞는지", "어떤 상황에 활용도 높은지"가 드러나게 작성
-설명글 안에 고객이 실제 검색할 만한 문장 흐름을 자연스럽게 반영
 예) 50대 봄코디 고민될 때 / 학교 갈 때 단정한 옷 찾을 때 / 아랫배 커버되는 티셔츠 찾을 때
-마지막에 CTA 문구
-최하단에 "상세한 상품정보는 영상 하단 상품배너 클릭" 넣기
-그 아래 상품 해시태그 10개 넣기
-해시태그는 브랜드, 상품군, 상황형, 체형고민형, 연령타깃형 키워드를 적절히 섞어 작성
-이모지 빼기
-너무 과장된 낚시형 제목 금지
"""
    if channel == "insta_reels":
        return f"""
1.작성된 상품 원고를 바탕으로 인스타 피드 15줄 원고 작성
  첫째줄 - 헤드라인
  둘째줄 - 미샵 (상품명)
2.상품특성을 4050여성의 공감을 얻을 수 있는 내용으로 작성
3.진짜 사람이 말하는 것 같은 여성들만의 친근한 어투
4.인스타 저장, 공유, 댓글 반응이 나오기 좋은 공감형 문장 흐름으로 작성
5.첫 3줄 안에 아래 요소 중 2개 이상 자연스럽게 포함
  - 상품 핵심 키워드
  - 상황형 키워드
  - 체형 고민 키워드
  - 4050 여성 공감 키워드
6.본문은 "예쁘다" 중심보다
  "왜 손이 가는지 / 어떤 체형에 덜 부담스러운지 / 어떤 자리에서 입기 좋은지"가 보이도록 작성
7.중간 문장에는 실제 여성 고객이 공감할 생활밀착형 포인트 반영
 예) 괜히 부해 보일까 걱정될 때 / 학교 갈 때 너무 꾸민 느낌 싫을 때 / 출근할 때 단정한데 편한 옷 찾을 때
8.마지막 줄은 CTA 문구
9.15줄 작성하고 다음에 한줄 띄우고 해시태그 5개 작성
 ("#미샵"을 제일 앞에, 나머지 4개는 상품/상황/타깃 중심 해시태그)
10.해시태그 다음에 한줄 띄우고
 "자세한 상품정보는 상단 프로필 링크 참조"
 "일상도 스타일도 미샵처럼, 심플하게! MISHARP"
 넣기
11.이모지 빼기
12.문장은 너무 길지 않게, 모바일에서 읽기 좋게 끊기
13.광고 티가 너무 나지 않게, 저장해두고 싶은 정보형 공감 피드 느낌으로 작성
14.결과는 복붙 가능하게 바로 출력

{base}
"""
    if channel == "tiktok":
        return f"""
1.작성된 상품 원고를 바탕으로 틱톡 피드 15줄 원고 작성
  첫째줄 - 헤드라인
  둘째줄 - 미샵 (상품명)
2.상품특성을 4050여성의 공감을 얻을 수 있는 내용으로 작성
3.진짜 사람이 말하는 것 같은 여성들만의 친근한 어투
4.틱톡 특성상 첫 2~3줄은 더 짧고 강하게, 후킹성 있게 작성
5.첫 줄 또는 둘째 줄 안에 검색형/공감형 키워드가 들어가게 작성
 예) 50대코디 / 체형커버 / 학교방문룩 / 출근룩 / 데일리룩 / 날씬해보이는핏
6.본문은 빠르게 읽히도록 짧은 문장 위주로 작성
7.상품특성은 단순 나열하지 말고
  "왜 이 옷이 요즘 필요한지"
  "누가 입으면 만족도가 높을지"
  "어떤 상황에서 실패 확률이 낮은지"
  중심으로 작성
8.4050 여성의 생활감 있는 공감 문장 반드시 포함
9.마지막 줄은 CTA 문구
10.15줄 작성하고 다음에 한줄 띄우고 해시태그 5개 작성
 ("#미샵"을 제일 앞에, 나머지 4개는 검색성과 공감성을 함께 고려)
11.해시태그 다음에 한줄 띄우고
 "자세한 상품정보는 하단 상품 배너 또는 상단 프로필 링크 참조"
 "일상도 스타일도 미샵처럼, 심플하게! MISHARP"
 넣기
12.이모지 빼기
13.틱톡용은 인스타보다 조금 더 직관적이고 빠른 템포로 작성
14.결과는 복붙 가능하게 바로 출력

{base}
"""
    if channel == "kakaostyle":
        return f"""
카카오스타일 미샵계정 피드 원고 작성
-최상단 : 해당 상품 홍보를 위한 후킹성 헤드라인 작성
-헤드라인은 검색형 키워드 + 공감형 문장 조합으로 작성
-본내용 : 상품명 적고, 한줄 내려서 상품 상세설명 150자 이내 뉴스형식으로 요약
-150자 이내 설명에는 아래 요소를 자연스럽게 포함
  1. 상품 핵심 키워드
  2. 4050 여성 공감 포인트
  3. 활용 상황 또는 체형 커버 포인트
-설명은 짧지만 "왜 이 상품이 필요한지"가 바로 보이게 작성
-과도한 감성 표현보다 정보형 + 생활형 요약 우선
-본 내용 하단 "상품 바로가기 ▼" 넣기
-한 줄 띄우고 "일상도 스타일도 미샵처럼, 심플하게! MISHARP" 넣기
-그 아래 해당 상품 관련 해시태그 20개 삽입
-필수 해시태그 포함 :
 #미샵 #여성의류쇼핑몰 #중년여성패션 #ootd #데일리룩
-추가 해시태그는 상품 키워드, 상황형 키워드, 체형 고민 키워드, 타깃 키워드를 섞어 작성
-이모지 빼기
-결과는 복붙 가능하게 바로 출력

{base}
"""
    if channel == "review":
        return f"""
제시한 설명의 미샵 여성의류 상품에 대해
고객 구매를 도와줄 수 있는 생활 밀착형, 공감형 상품 사용 후기 작성하되
아래 지침대로 작성해줘

<지침>
- 4050대 일반인 여성이 쓴 듯한 일상적 문체
- 배송받아서 처음 입어본 소감의 말투
- 옷, 패션 관련 전문용어 자제, 일반인의 생활 문장
- 50자에서 300자 내외 총 10개
- 10개 중 긴글 5개, 짧은 글 5개
- 짧으면 50자, 길면 300자까지
- 차분하고 세심한 후기는 길게
- 옷에 대한 칭찬과 흥분으로 쓴 후기는 짧게
- 10개의 후기가 각각 작성자의 성격이 다르게, 글쓰는 스타일도 각각 다 완전히 달라야 함
- 작성자 스펙은 키155cm~163cm 사이, 체중 52kg~63kg 사이로 다양하게 설정
- 정말 일반인이 적은 듯한 캐주얼한 말투
- 후기글 앞에 각각 (키/몸무게) 넣고 시작
- 체형 대비 입었을 때의 핏 만족감 반영
- 옷 품질, 구매과정 경험, 활용성 반영
- 가성비 강조
- ㅎㅎ, ~~, ^^, :) 등 적절히 넣기
- 배송이 빨랐다거나 역시 미샵에서 사길 잘했다는 내용 적절히 섞기
- 후기글에 제목 빼기
- 후기글에 상품명 빼기
- 너무 광고처럼 완벽한 후기 말투 금지
- 실제로 고객이 많이 남길 법한 검색형/공감형 표현도 자연스럽게 섞기
 예) 부해 보이지 않아요 / 뱃살이 덜 신경 쓰여요 / 학교 갈 때 입기 좋겠어요 / 출근룩으로 괜찮아요 / 생각보다 편해요
- 10개 후기는 길이, 말투, 성격, 만족 포인트가 겹치지 않게 작성
- 결과는 번호 없이 후기 10개만 복붙 가능하게 바로 출력

{base}
"""
    if channel == "video_script":
        return f"""
당신은 최고의 온라인마케터이자 박웅현, 정철, 최인아와 같은 최고의 카피라이터입니다.
다음 프로젝트 지침대로 작성해주세요.

프로젝트 목적
20~30초 길이, 인스타 릴스, 유튜브 쇼츠용 동영상 원고 카피 작성
대한민국 4050 여성 타겟을 겨냥해
'합리적 소비', '스스로 납득할 수 있는 선택'을 유도하는
이성적 + 논리적 + 생활밀착형 브랜드 소구 전략을 사용한다.
"패션 쇼핑호스트"처럼 친근하고 직접 말 걸듯 제안하는 톤을 유지한다.
말투 : 친근한 쇼핑호스트 및 노련한 옷가게 사장언니의 ~해요 체로.

해당 상품 상세페이지 문구를 바탕으로 아래 프롬프트로 문구 구성

프롬프트
1. 짧은 10줄로 구성, 1줄은 20자 내외
2. 임팩트 있는 광고 카피라이팅
3. 첫줄은 후킹성 헤드라인(stick 요소 강하게)
   - TPO, pain point, 검색형 고민 키워드에 기반해
   " ~ 분들을 위한 ** " 형식으로 작성
4. 마지막줄은 공감유도 CTA 문구
5. 윗부분에서 실생활에서 공감가는 고객의 pain point 제시
   글이 진행되면서 상품 USP와 연결하여 상품 어필
6. 여성들이 많이 쓰는 대중적인 의성어 의태어 활용
7. A/B 2타입 작성
8. 첫줄 헤드라인은 별도 5개 타입 제안
9. 헤드라인에는 아래 요소 중 2개 이상 자연스럽게 반영
   - 상품 키워드
   - 상황형 키워드
   - 체형 고민 키워드
   - 연령 공감 키워드
10. 전체 원고는 "예쁘다"보다
   "왜 지금 필요한지 / 왜 실패 확률이 낮은지 / 왜 손이 자주 갈지" 중심으로 전개
11. 유튜브 쇼츠/릴스 검색에도 걸릴 수 있도록
   영상 안에서 실제 고객이 검색할 만한 표현을 자연스럽게 포함
12. 너무 긴 문장, 추상적인 문장, 뻔한 칭찬 반복 금지
13. 결과는 아래 순서로 복붙 가능하게 출력
   - 헤드라인 5개
   - A타입 10줄
   - B타입 10줄

{base}
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
        parts.append(f"==============================\n{label}\n==============================\n{body}")
    return "\n\n".join(parts)

# ---------------------------
# Header
# ---------------------------
st.markdown("""
<div class="misharp-header">
  <h1>MISHARP 광고문구 자동생성기</h1>
  <p>온라인 셀러를 위한 SNS 매체별 최적화 광고문구 자동 생성기</p>
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
with r2:
    st.checkbox("동영상 원고", key=ui_key("video_script"))
    st.checkbox("인스타 릴스 피드", key=ui_key("insta_reels"))
with r3:
    st.checkbox("틱톡 피드", key=ui_key("tiktok"))
    st.checkbox("유튜브 숏츠 피드", key=ui_key("youtube_shorts"))
with r4:
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
