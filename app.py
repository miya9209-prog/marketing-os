
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
    ("video_script", "동영상 원고"),
    ("insta_reels", "인스타 릴스 피드"),
    ("tiktok", "틱톡 피드"),
    ("youtube_shorts", "유튜브 숏츠 피드"),
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
    if channel == "review":
        return f"""
당신은 미샵 여성의류 상품의 실사용 후기를 쓰는 카피라이터입니다.
반드시 아래 지침을 빠짐없이 지키세요.
모든 출력은 한국어로만 작성하세요.

{base}

[출력 형식]
- 제목 금지
- 설명 금지
- 후기 10개만 바로 출력
- 각 후기 앞에 반드시 (키/몸무게) 형식으로 시작
예: (158/54)

[리뷰 작성 지침]
- 제시한 설명 또는 URL, 이미지의 미샵 여성의류 상품에 대해 고객 구매를 도와줄 수 있는 생활 밀착형, 공감형 상품 사용 후기 작성
- 4050대 일반인 여성이 쓴 듯한 일상적 문체
- 배송받아서 처음 입어본 소감의 말투
- 옷, 패션 관련 전문용어 금지, 일반인들이 생활 속에서 사용하는 문장과 단어로 구성
- 총 10개 작성
- 10개 중 긴글 5개, 짧은 글 5개
- 각 후기는 50자에서 300자 사이
- 10명의 다른 작성자가 쓴 것처럼 성격과 글쓰기 스타일이 전부 달라야 함
- 키 155cm~163cm 사이, 체중 52kg~63kg 사이로만 설정
- 후기글 앞에 각각 (키/몸무게) 넣고 시작, 매우 중요
- 체형 대비 입었을 때의 만족감이 드러나야 함
- 옷 품질, 구매과정 경험, 활용성 반영
- 가성비 강조
- ㅎㅎ, ~~, ^^, :) 등을 적절히 섞기
- 배송이 빨랐다, 역시 미샵에서 사길 잘했다 같은 내용 적절히 섞기
- 후기글에 제목 빼기
- 후기글에 상품명 빼기
- 같은 문장 반복 금지
- 10개 후기를 한 줄씩 구분해서 출력

[길이 구성 규칙]
- 1~5번 후기는 120자~300자
- 6~10번 후기는 50자~120자
"""
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
    if channel == "insta_reels":
        return f"""
모든 출력은 한국어로만 작성하세요.

{base}

[규칙]
1. 첫째줄 - 헤드라인
2. 둘째줄 - 미샵 상품명
3. 상품특성을 4050여성의 공감을 얻을 수 있는 내용
4. 진짜 사람이 말하는 거 같은 여성들만의 친근한 어투
5. 마지막 줄은 CTA 문구
6. 총 15줄 작성
7. 다음에 한줄 띄우고 해시태그 5개("#미샵"을 제일 앞에, 나머지 4개 해시태그)
8. 해시태그 다음에 한줄 띄우고 아래 문구 그대로 출력
자세한 상품정보는 상단 프로필 링크 참조
일상도 스타일도 미샵처럼, 심플하게! MISHARP
9. 이모지 빼기
"""
    if channel == "tiktok":
        return f"""
모든 출력은 한국어로만 작성하세요.

{base}

[규칙]
1. 첫째줄 - 헤드라인
2. 둘째줄 - 미샵 상품명
3. 상품특성을 4050여성의 공감을 얻을 수 있는 내용
4. 마지막 줄은 CTA 문구
5. 총 15줄 작성
6. 다음에 한줄 띄우고 해시태그 5개("#미샵"을 제일 앞에, 나머지 4개 해시태그)
7. 해시태그 다음에 한줄 띄우고 아래 문구 그대로 출력
자세한 상품정보는 하단 상품링크 또는 상단 프로필 링크 참조
일상도 스타일도 미샵처럼, 심플하게! MISHARP
8. 이모지 빼기
"""
    if channel == "youtube_shorts":
        return f"""
모든 출력은 한국어로만 작성하세요.

{base}

[규칙]
- 타이틀 : 100자 이내 후킹성 강한 타이틀
- 타이틀 바로 뒤에 해시태그 8~10개 포함
- #미샵 #shorts #ootd 포함 필수
- 설명 피드 : 상품내용 공감형, TPO 담아 설명글 작성
- 마지막에 CTA 문구
- 최하단에 "상세한 상품정보는 영상 하단 상품배너 클릭" 넣기
- 그 아래 상품 해시태그 10개 넣기
"""
    if channel == "video_script":
        return f"""
당신은 최고의 온라인마케터이자 카피라이터입니다.
모든 출력은 한국어로만 작성하세요.

{base}

[규칙]
- 20~30초 길이
- 친근한 쇼핑호스트 및 노련한 옷가게 사장언니의 ~해요 체
- 짧은 10줄 구성, 1줄 20자 내외
- 첫줄은 후킹성 헤드라인
- 마지막줄은 공감유도 CTA 문구
- A/B 2타입
- 첫줄 헤드라인은 별도로 5개 타입 제안
"""
    if channel == "kakaostyle":
        return f"""
모든 출력은 한국어로만 작성하세요.

{base}

[규칙]
- 최상단 : 후킹성 헤드라인
- 본문 둘째 줄 : 상품명
- 그 아래 150자 이내 뉴스형식 요약
- 본문 하단 "상품 바로가기 ▼"
- 다음 줄에 URL 그대로 삽입
- 한 줄 띄우고 "일상도 스타일도 미샵처럼, 심플하게! MISHARP"
- 그 아래 해시태그 30개 삽입
- 필수 해시태그 : #미샵 #여성의류쇼핑몰 #중년여성패션 #ootd #데일리룩 #출근룩
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
