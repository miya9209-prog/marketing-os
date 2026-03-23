
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

CHANNELS = [
    ("sms", "SMS문자"),
    ("app_push", "앱푸시"),
    ("insta_reels", "인스타 릴스 피드"),
    ("tiktok", "틱톡 피드"),
    ("youtube_shorts", "유튜브 숏츠 피드"),
    ("review", "REVIEW"),
    ("video_script", "동영상 원고"),
    ("kakaostyle", "카카오스타일"),
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
  padding-top:2.35rem !important;
  padding-bottom:2.8rem;
}
.misharp-header{
  background:#f5f2f1;
  color:#251a2e;
  border-radius:26px;
  padding:30px 32px 26px 32px;
  box-shadow:0 8px 28px rgba(0,0,0,.18);
  margin-top:.35rem;
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
.misharp-mini{
  color:#9eb0c5;
  font-size:.92rem;
}
.misharp-footer{
  color:#94a3b8;
  text-align:center;
  font-size:.92rem;
  margin-top:28px;
  padding:12px 0 6px 0;
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

def build_prompt(data: dict) -> str:
    selected_labels = [CHANNEL_LABELS[ch] for ch in data["selected_channels"]]
    media_note = ", ".join(data.get("media_names", [])) if data.get("media_names") else "없음"

    return f"""
당신은 미샵의 광고문구 자동생성 엔진입니다.
반드시 아래 기획 지침을 그대로 따르세요.
모든 출력은 한국어로만 작성하세요.

[입력 정보]
상품 URL:
{data.get("product_url","")}

상품, 이벤트 주요 내용:
{data.get("product_content","")}

이벤트 추가 정보:
{data.get("event_content","")}

업로드 파일명 참고:
{media_note}

선택 채널:
{", ".join(selected_labels)}

[공통 출력 형식]
선택된 채널만 아래 형식으로 차례대로 출력:
==============================
채널명
==============================
내용

[매우 중요한 공통 규칙]
- 채널명 외의 서론, 설명, 사족 금지
- 선택하지 않은 채널은 절대 출력 금지
- 4050 여성이 실제로 공감할 말투로 작성
- 정보가 부족하면 입력된 내용만 바탕으로 작성
- 이모지 사용 금지

[SMS 문자 규칙]
- SMS 유형: {data.get("sms_mode","단문")}
- 단문문자는 한글 56자 기준 이내
- 첫문구 시작은 반드시 "(광고)미샵♥"
- 문구 끝은 반드시 "▶"
- 시작과 끝 포함 전체 56자 이내
- 후킹성, 신선함, 긴박감 반영
- 단문은 3가지 시안 출력

- 장문문자는 제한 없음
- 장문문자 출력 형식:
상담고정 제목 : (광고)미샵 "이벤트명"
이벤트 문구(연결 링크 등 포함)
그리고 아래 고정 문구를 반드시 그대로 하단에 붙일 것:

※혹시 피싱문자 우려되신다면 네이버 검색창에 "미샵" 검색 후 클릭하셔서 주말이벤트 확인해주세요:)

♡일상을 위한 데일리룩, 출근룩 쇼핑에 꼭 활용해보세요.

일상도 스타일도 미샵처럼, 심플하게! MISHARP

♡지금 미샵 바로가기
http://misharp.co.kr

♡요즘 핫한 미샵 인스타그램, 지금 만나보세요:)(@misharp2006)

♡유튜브 미샵TV, 틱톡, 카카오스토리에서 미샵의 다양한 컨텐츠를 만나보세요:)

M  I  S  H  A  R  P

- 장문은 3가지 시안 출력

[앱푸시 규칙]
아래 지침을 반드시 그대로 지킬 것.
- 할인율을 첫 문장에 바로 노출하지 말 것
- 과도한 느낌표, 자극적인 홈쇼핑 말투 금지
- 정보 나열형 문구 금지
- 광고내용에 상품명은 [상품명] 형식으로 구분, 광고문구에 상품명은 1번만 넣기
- 문구 구조는 반드시 상황 공감 → 이유 제시 → 행동 유도
- 아래 키워드 중 최소 1개 이상 자연스럽게 반영:
붙지 않음 / 체형커버 / 오래 입음 / 코디 쉬움 / 자주 손이 감

앱푸시는 반드시 아래 3타입을 모두 작성:
[타입1] 24시간 MD추천 앱푸시
출력 형식:
헤드라인 : 30자 이내(5가지 시안)
광고문구 : 3종 제안
광고)24시간 MD추천 10%할인 [상품명]
(푸시 문구 – 한글 50자 이내)
수신거부설정: 알림함-설정버튼

[타입2] 주말한정 MD추천 앱푸시
출력 형식:
헤드라인 : 30자 이내(5가지 시안)
광고문구 : 3종 제안
광고)주말한정 MD추천 10%할인 [상품명]
(푸시 문구 – 한글 50자 이내)
수신거부설정: 알림함-설정버튼

[타입3] 이벤트 관련 내용 인풋
출력 형식:
헤드라인 : 30자 이내(5가지 시안)
광고문구(3종 제안) : 광고) [이벤트명] + 광고문구 + 수신거부설정: 알림함-설정버튼
총 100자 이내

[인스타 릴스 피드 규칙]
- 총 15줄 작성
- 첫째줄: 헤드라인
- 둘째줄: 미샵 상품명
- 상품특성을 4050여성 공감형 내용으로 작성
- 진짜 사람이 말하는 여성들의 친근한 어투
- 마지막 줄은 CTA 문구
- 15줄 다음 한 줄 띄우고 해시태그 5개
- #미샵 을 제일 앞에, 나머지 4개 해시태그
- 해시태그 다음 한 줄 띄우고 아래 두 줄을 그대로 출력
자세한 상품정보는 상단 프로필 링크 참조
일상도 스타일도 미샵처럼, 심플하게! MISHARP

[틱톡 피드 규칙]
- 총 15줄 작성
- 첫째줄: 헤드라인
- 둘째줄: 미샵 상품명
- 상품특성을 4050여성 공감형 내용으로 작성
- 마지막 줄은 CTA 문구
- 15줄 다음 한 줄 띄우고 해시태그 5개
- #미샵 을 제일 앞에, 나머지 4개 해시태그
- 해시태그 다음 한 줄 띄우고 아래 두 줄을 그대로 출력
자세한 상품정보는 하단 상품링크 또는 상단 프로필 링크 참조
일상도 스타일도 미샵처럼, 심플하게! MISHARP

[유튜브 숏츠 피드 규칙]
- 타이틀 100자 이내
- 후킹성 강한 타이틀 다음에 해시태그 8~10개 포함
- #미샵 #shorts #ootd 포함 필수
- 설명 피드는 상품내용 공감형, TPO 담아 작성
- 마지막에 CTA 문구
- 최하단에 아래 문구 그대로 출력
상세한 상품정보는 영상 하단 상품배너 클릭
- 그 아래 상품 해시태그 10개

[REVIEW 규칙]
- 총 10개 작성
- 긴글 5개, 짧은 글 5개
- 각 후기 50자~300자
- 10명이 각각 다른 성격과 다른 글쓰기 스타일
- 키 155cm~163cm, 몸무게 52kg~63kg 범위
- 각 후기 앞에 반드시 (키/몸무게) 형식
- 배송받아서 처음 입어본 소감 말투
- 옷, 패션 전문용어 금지
- 4050 일반인 여성이 쓴 듯한 생활 문체
- 체형 대비 만족감, 품질, 구매경험, 활용성, 가성비 반영
- ㅎㅎ, ~~ , ^^, :) 등을 적절히 섞기
- 배송이 빨랐다 / 역시 미샵에서 사길 잘했다 같은 내용 적절히 반영
- 제목 금지, 상품명 금지

[동영상 원고 규칙]
당신은 최고의 온라인마케터이자 박웅현, 정철, 최인아와 같은 최고의 카피라이터입니다.
- 20~30초 길이
- 대한민국 4050 여성 타겟
- 합리적 소비, 납득 가능한 선택을 유도
- 친근한 쇼핑호스트 및 노련한 옷가게 사장언니의 ~해요 체
- 짧은 10줄 구성, 1줄 20자 내외
- 첫줄은 후킹성 헤드라인
- 마지막줄은 공감유도 CTA 문구
- pain point 제시 후 USP 연결
- 의성어 의태어 활용
- A/B 2타입
- 첫줄 헤드라인은 별도로 5개 타입 제안

[카카오스타일 규칙]
- 최상단: 후킹성 헤드라인
- 본문 둘째 줄: 상품명
- 그 아래 150자 이내 뉴스형식 요약
- 본문 하단 "상품 바로가기 ▼"
- 다음 줄에 URL 그대로 삽입
- 한 줄 띄우고 "일상도 스타일도 미샵처럼, 심플하게! MISHARP"
- 그 아래 해시태그 30개 삽입
- 필수 해시태그: #미샵 #여성의류쇼핑몰 #중년여성패션 #ootd #데일리룩 #출근룩

반드시 기획 지침을 빠짐없이 따르고, 선택 채널 결과를 차례대로 출력하세요.
"""

def call_gpt(prompt: str) -> str:
    client = OpenAI()
    model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    response = client.responses.create(model=model_name, input=prompt)
    return response.output_text

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

def long_sms_cleanup(body: str) -> str:
    required_footer = """※혹시 피싱문자 우려되신다면 네이버 검색창에 "미샵" 검색 후 클릭하셔서 주말이벤트 확인해주세요:)

♡일상을 위한 데일리룩, 출근룩 쇼핑에 꼭 활용해보세요.

일상도 스타일도 미샵처럼, 심플하게! MISHARP

♡지금 미샵 바로가기
http://misharp.co.kr

♡요즘 핫한 미샵 인스타그램, 지금 만나보세요:)(@misharp2006)

♡유튜브 미샵TV, 틱톡, 카카오스토리에서 미샵의 다양한 컨텐츠를 만나보세요:)

M  I  S  H  A  R  P"""
    if required_footer not in body:
        body = body.strip() + "\n\n" + required_footer
    return body

def enforce_sections(text: str, selected: list) -> str:
    # make sure section headers exist if model slightly deviates
    fixed = text.strip()

    # SMS postprocess
    if "sms" in selected:
        pattern = re.compile(r"(=+\nSMS문자\n=+\n)(.*?)(?=\n=+\n|\Z)", re.DOTALL)
        match = pattern.search(fixed)
        if match:
            body = match.group(2).strip()
            mode = get_value("sms_mode", "단문")
            body = short_sms_cleanup(body) if mode == "단문" else long_sms_cleanup(body)
            fixed = fixed[:match.start(2)] + body + fixed[match.end(2):]

    # app push basic cleanup
    if "app_push" in selected:
        fixed = re.sub(r"\[상품명\]", "[상품명]", fixed)

    # kakaostyle url inject
    if "kakaostyle" in selected:
        url = get_value("product_url", "").strip()
        if url and "카카오스타일" in fixed and url not in fixed:
            pattern = re.compile(r"(=+\n카카오스타일\n=+\n)(.*?)(?=\n=+\n|\Z)", re.DOTALL)
            m = pattern.search(fixed)
            if m:
                body = m.group(2).strip()
                if "상품 바로가기 ▼" in body:
                    body = body.replace("상품 바로가기 ▼", f"상품 바로가기 ▼\n{url}", 1)
                else:
                    body += f"\n상품 바로가기 ▼\n{url}"
                fixed = fixed[:m.start(2)] + body + fixed[m.end(2):]
    return fixed

# ---------------------------
# Header
# ---------------------------
st.markdown("""
<div class="misharp-header">
  <h1>MISHARP 광고문구 자동생성기</h1>
  <p>온라인 셀러를 위한 SNS 매체별 최적화 광고문구 자동 생성기</p>
</div>
""", unsafe_allow_html=True)

policy_cols = st.columns([1,1,6])
with policy_cols[0]:
    with st.popover("개인정보처리방침"):
        st.write("입력한 URL, 텍스트, 업로드 파일은 광고문구 생성을 위한 처리 목적으로만 사용합니다.")
with policy_cols[1]:
    with st.popover("서비스 약관"):
        st.write("생성 결과는 사용자가 최종 검토 후 사용하는 것을 원칙으로 합니다.")

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
    with st.popover("작업 불러오기", use_container_width=True):
        load_file = st.file_uploader("파일 선택", type=["json"], label_visibility="collapsed", key=ui_key("load_json"))
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

with btn_cols[3]:
    st.link_button("이미지추출", "https://misharp-image-crop-v1.streamlit.app/", use_container_width=True)

with btn_cols[4]:
    st.link_button("URL 단축", "https://shor.kr", use_container_width=True)

if st.session_state.loaded_notice:
    st.success("불러온 작업이 반영되었습니다.")
    st.session_state.loaded_notice = False

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# ---------------------------
# Input area
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
    st.checkbox("인스타 릴스 피드", key=ui_key("insta_reels"))
    st.checkbox("틱톡 피드", key=ui_key("tiktok"))
with r3:
    st.checkbox("유튜브 숏츠 피드", key=ui_key("youtube_shorts"))
    st.checkbox("REVIEW", key=ui_key("review"))
with r4:
    st.checkbox("동영상 원고", key=ui_key("video_script"))
    st.checkbox("카카오스타일", key=ui_key("kakaostyle"))

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
            with st.spinner("문구를 생성하고 있습니다..."):
                raw = call_gpt(build_prompt(payload))
                cooked = enforce_sections(raw, payload["selected_channels"])
            st.session_state.result = cooked
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

st.markdown('<div class="misharp-footer">copyright MISHARP COMPANY by MIYAWA. 2026. All rights reservde.</div>', unsafe_allow_html=True)
