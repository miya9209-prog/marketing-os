
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

# =========================
# Session / constants
# =========================
if "ui_nonce" not in st.session_state:
    st.session_state.ui_nonce = 0
if "result" not in st.session_state:
    st.session_state.result = ""

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

# =========================
# Styles
# =========================
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
  max-width: 1240px;
  padding-top: 2.35rem !important;
  padding-bottom: 2.8rem;
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
.misharp-footer{
  color:#94a3b8;
  text-align:center;
  font-size:.92rem;
  margin-top:28px;
  padding:12px 0 6px 0;
}
</style>
""", unsafe_allow_html=True)

# =========================
# Helpers
# =========================
def ui_key(name: str) -> str:
    return f"{name}_{st.session_state.ui_nonce}"

def reset_all() -> None:
    st.session_state.result = ""
    st.session_state.ui_nonce += 1

def sanitize_filename(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", value)
    value = value.strip("._-")
    return value[:40] or "work"

def get_value(name: str, default=""):
    return st.session_state.get(ui_key(name), default)

def get_selected_channels():
    selected = []
    for key, _label in CHANNELS:
        if st.session_state.get(ui_key(key), False):
            selected.append(key)
    return selected

def current_payload():
    return {
        "product_url": get_value("product_url", ""),
        "product_content": get_value("product_content", ""),
        "event_content": get_value("event_content", ""),
        "sms_mode": get_value("sms_mode", "단문"),
        "selected_channels": get_selected_channels(),
    }

def build_prompt(data: dict) -> str:
    selected_labels = [CHANNEL_LABELS[ch] for ch in data["selected_channels"]]
    return f"""
당신은 대한민국 4050 여성 타겟 온라인 패션 마케팅에 강한 최고 수준의 카피라이터입니다.
브랜드 톤은 친근한 쇼핑호스트 + 노련한 옷가게 사장언니의 "~해요" 말투입니다.
모든 결과는 한국어로만 작성하세요.

[입력 정보]
상품 URL:
{data.get("product_url","")}

상품내용:
{data.get("product_content","")}

이벤트 주요내용:
{data.get("event_content","")}

[선택 채널]
{", ".join(selected_labels)}

[매우 중요한 공통 규칙]
- 선택된 채널만 작성
- 각 채널 결과는 아래 형식으로 반드시 정확히 구분
==============================
[채널명]
==============================
내용

- 채널명이 아닌 다른 머리말, 설명문, 서론 금지
- 상품명, 핵심 USP, 이벤트를 반영
- 상품정보가 부족하면 억지 추측 금지, 입력된 정보 중심으로 설득력 있게 작성

[채널별 규칙]

1) SMS문자
- SMS 유형: {data.get("sms_mode","단문")}
- 단문이면 반드시 "(광고)미샵♥"로 시작
- 단문은 전체 55자 이내
- 장문도 "(광고)미샵♥"로 시작
- [SMS문자] 섹션에는 결과 2개만 작성
- 불필요한 표기 금지

2) 앱푸시
- 각 문구는 반드시 "광고)"로 시작
- 짧고 클릭 유도형
- 3개 작성

3) 동영상 원고
- 20~30초 길이
- A/B 2타입
- 각 타입은 10줄 구성
- 첫 줄은 후킹 헤드라인
- 마지막 줄은 CTA
- 별도로 "헤드라인 후보 5개" 제안

4) 인스타 릴스 피드
- 후킹 헤드라인 1개
- 본문 8~12줄
- 해시태그 12~18개

5) 틱톡 피드
- 템포감 있게
- 후킹 강하게
- 본문은 짧고 직관적으로
- 해시태그 10개 내외

6) 유튜브 쇼츠 피드
- 제목형 후킹 1개
- 설명형 본문
- CTA 포함

7) 카카오스타일
- 최상단 후킹성 헤드라인
- 둘째 줄에 상품명 또는 상품 핵심명
- 그 아래 150자 이내 뉴스형식 요약
- "상품 바로가기 ▼" 다음 줄에 URL 그대로 삽입
- 다음 줄에 "일상도 스타일도 미샵처럼, 심플하게! MISHARP"
- 해시태그 30개

8) REVIEW
- 짧은 후기 3개
- 중간 길이 후기 2개
- 실제 구매후기처럼 자연스럽게
"""

def call_gpt(prompt: str) -> str:
    client = OpenAI()
    model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    response = client.responses.create(model=model_name, input=prompt)
    return response.output_text

def truncate_sms_line(line: str) -> str:
    prefix = "(광고)미샵♥"
    text = line.strip()
    if not text.startswith(prefix):
        text = prefix + text
    text = text.replace(prefix + " ", prefix)
    return text[:55]

def postprocess_output(text: str, data: dict) -> str:
    # SMS
    if "sms" in data["selected_channels"]:
        pattern = re.compile(r"(==============================\n\[SMS문자\]\n==============================\n)(.*?)(?=\n==============================|\Z)", re.DOTALL)
        def sms_repl(match):
            head = match.group(1)
            body = match.group(2).strip()
            lines = []
            for raw in body.splitlines():
                s = raw.strip()
                if not s:
                    continue
                if data["sms_mode"] == "단문":
                    s = truncate_sms_line(s)
                else:
                    if not s.startswith("(광고)미샵♥"):
                        s = "(광고)미샵♥" + s
                lines.append(s)
            return head + "\n".join(lines[:2]) + "\n"
        text = pattern.sub(sms_repl, text)

    # App push
    if "app_push" in data["selected_channels"]:
        pattern = re.compile(r"(==============================\n\[앱푸시\]\n==============================\n)(.*?)(?=\n==============================|\Z)", re.DOTALL)
        def push_repl(match):
            head = match.group(1)
            body = match.group(2).strip()
            lines = []
            for raw in body.splitlines():
                s = raw.strip()
                if not s:
                    continue
                if not s.startswith("광고)"):
                    s = "광고)" + s.lstrip(" )")
                lines.append(s)
            return head + "\n".join(lines[:3]) + "\n"
        text = pattern.sub(push_repl, text)

    # KakaoStyle URL
    if "kakaostyle" in data["selected_channels"] and data.get("product_url", "").strip():
        pattern = re.compile(r"(==============================\n\[카카오스타일\]\n==============================\n)(.*?)(?=\n==============================|\Z)", re.DOTALL)
        def kakao_repl(match):
            head = match.group(1)
            body = match.group(2).strip()
            url = data["product_url"].strip()
            if url in body:
                return match.group(0)
            if "상품 바로가기 ▼" in body:
                body = body.replace("상품 바로가기 ▼", f"상품 바로가기 ▼\n{url}", 1)
            else:
                body += f"\n상품 바로가기 ▼\n{url}"
            return head + body + "\n"
        text = pattern.sub(kakao_repl, text)

    return text

# =========================
# Header
# =========================
st.markdown("""
<div class="misharp-header">
  <h1>MISHARP 광고문구 자동생성기</h1>
  <p>온라인 셀러를 위한 SNS 매체별 최적화 광고문구 자동 생성기</p>
</div>
""", unsafe_allow_html=True)

# =========================
# Top button row
# =========================
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
        load_file = st.file_uploader(
            "파일 선택",
            type=["json"],
            label_visibility="collapsed",
            key=ui_key("load_json")
        )
        if load_file:
            data = json.load(load_file)
            st.session_state[ui_key("product_url")] = data.get("product_url", "")
            st.session_state[ui_key("product_content")] = data.get("product_content", "")
            st.session_state[ui_key("event_content")] = data.get("event_content", "")
            st.session_state[ui_key("sms_mode")] = data.get("sms_mode", "단문")
            selected = set(data.get("selected_channels", []))
            for ch, _label in CHANNELS:
                st.session_state[ui_key(ch)] = ch in selected
            st.success("불러오기 완료")

with btn_cols[3]:
    st.link_button("이미지추출", "https://misharp-image-crop-v1.streamlit.app/", use_container_width=True)

with btn_cols[4]:
    st.link_button("URL 단축", "https://shor.kr", use_container_width=True)

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# =========================
# Input area
# =========================
left, right = st.columns([1.05, 0.95], gap="large")
with left:
    st.markdown('<div class="misharp-section-title">입력 정보</div>', unsafe_allow_html=True)
    st.text_input("상품 URL", key=ui_key("product_url"), placeholder="상품 URL 또는 이벤트 링크를 입력하세요")
    st.text_area("상품내용", key=ui_key("product_content"), height=220, placeholder="상세페이지 상품설명, 상품스펙, 소재, 핏, 컬러, 사이즈, USP 등을 입력하세요")
    st.text_area("이벤트 주요내용", key=ui_key("event_content"), height=120, placeholder="할인율, 기간, 혜택, 쿠폰, 무료배송 등 이벤트 정보를 입력하세요")

with right:
    st.markdown('<div class="misharp-section-title">이미지 / 동영상 등록</div>', unsafe_allow_html=True)
    st.file_uploader("파일 업로드", accept_multiple_files=True, key=ui_key("media"))
    st.caption("입력값은 URL, 텍스트, 이미지, 동영상 중 1개 이상이면 생성 가능합니다.")

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# =========================
# Channel selection
# =========================
st.markdown('<div class="misharp-section-title" style="font-size:1.75rem;">출력 채널 선택</div>', unsafe_allow_html=True)

r1, r2, r3, r4 = st.columns(4)
with r1:
    st.checkbox("SMS문자", key=ui_key("sms"))
    st.checkbox("앱푸시", key=ui_key("app_push"))
with r2:
    st.checkbox("동영상 원고", key=ui_key("video_script"))
    st.checkbox("인스타 릴스 피드", key=ui_key("insta_reels"))
with r3:
    st.checkbox("틱톡 피드", key=ui_key("tiktok"))
    st.checkbox("유튜브 쇼츠 피드", key=ui_key("youtube_shorts"))
with r4:
    st.checkbox("카카오스타일", key=ui_key("kakaostyle"))
    st.checkbox("REVIEW", key=ui_key("review"))

sms_col, _ = st.columns([0.28, 0.72])
with sms_col:
    st.radio("SMS 유형", ["단문", "장문"], key=ui_key("sms_mode"), horizontal=True)

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# =========================
# Generate
# =========================
if st.button("문구 생성", use_container_width=True):
    payload = current_payload()
    has_input = bool(payload["product_url"] or payload["product_content"] or payload["event_content"])
    if not has_input:
        st.warning("입력값을 하나 이상 입력하세요.")
    elif not payload["selected_channels"]:
        st.warning("출력 채널을 하나 이상 선택하세요.")
    else:
        try:
            with st.spinner("문구를 생성하고 있습니다..."):
                raw = call_gpt(build_prompt(payload))
                cooked = postprocess_output(raw, payload)
            st.session_state.result = cooked
        except Exception as e:
            st.error(f"생성 중 오류가 발생했습니다: {e}")

# =========================
# Result
# =========================
st.markdown('<div class="misharp-section-title" style="font-size:1.75rem; margin-top:16px;">생성 결과</div>', unsafe_allow_html=True)
st.text_area("결과", value=st.session_state.get("result", ""), height=420, label_visibility="collapsed")

st.download_button(
    "TXT 다운로드",
    data=st.session_state.get("result", ""),
    file_name=f"misharp_copy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
    mime="text/plain",
    use_container_width=False,
)

# =========================
# Footer
# =========================
st.markdown('<div class="misharp-footer">© 2026 MISHARP. All rights reserved.</div>', unsafe_allow_html=True)
