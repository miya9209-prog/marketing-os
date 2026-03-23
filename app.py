
import streamlit as st
import json
import base64
import mimetypes
import os
import re
from datetime import datetime
from openai import OpenAI

st.set_page_config(
    page_title="MISHARP 광고문구 자동생성기",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- State ----------
if "uploader_nonce" not in st.session_state:
    st.session_state.uploader_nonce = 0
if "loaded_notice" not in st.session_state:
    st.session_state.loaded_notice = False

# ---------- Styles ----------
st.markdown("""
<style>
:root{
  --bg:#030816;
  --panel:#0b1220;
  --panel-2:#111827;
  --panel-3:#1f2937;
  --line:#243244;
  --text:#f8fafc;
  --muted:#b6c2d1;
  --accent:#f5f2f1;
  --accent-text:#251a2e;
}
html, body, [class*="css"] {
  font-family: "Pretendard","Noto Sans KR",sans-serif;
}
.stApp {
  background: linear-gradient(180deg,#020617 0%, #030816 100%);
  color: var(--text);
}
[data-testid="stSidebar"], [data-testid="stSidebarNav"], [data-testid="collapsedControl"]{
  display:none !important;
}
.block-container {
  max-width: 1240px;
  padding-top: 2.2rem;
  padding-bottom: 3rem;
}
.misharp-header {
  background: var(--accent);
  border-radius: 26px;
  padding: 30px 32px 26px 32px;
  color: var(--accent-text);
  box-shadow: 0 8px 28px rgba(0,0,0,.18);
  margin-bottom: 18px;
}
.misharp-header h1{
  margin:0;
  font-size: 2.55rem;
  line-height: 1.12;
  font-weight: 900;
  letter-spacing: -0.03em;
}
.misharp-header p{
  margin: 12px 0 0 0;
  font-size: 1.05rem;
  color: #6b4f45;
}
.misharp-linkrow{
  margin-top: 14px;
  display:flex;
  gap:14px;
  flex-wrap:wrap;
}
.misharp-linkrow span{
  font-size:.92rem;
  color:#6b4f45;
}
.misharp-section-title{
  font-size: 2.05rem;
  font-weight: 900;
  letter-spacing: -0.03em;
  margin: 0 0 14px 0;
  color: white;
}
.misharp-card{
  background: transparent;
  border: 1px solid transparent;
  border-radius: 22px;
  padding: 0;
}
.misharp-result-card{
  background: rgba(10,18,32,.82);
  border:1px solid var(--line);
  border-radius: 22px;
  padding: 18px;
  margin-top: 20px;
}
.misharp-mini{
  color: var(--muted);
  font-size:.92rem;
}
[data-testid="stTextInputRoot"] > div,
[data-testid="stTextArea"] textarea,
[data-testid="stFileUploaderDropzone"]{
  background: rgba(31,41,55,.8) !important;
}
div[data-testid="stTextInputRoot"] input,
div[data-testid="stTextArea"] textarea{
  color: #f8fafc !important;
  border-radius: 14px !important;
  border:1px solid var(--line) !important;
}
div[data-testid="stTextInputRoot"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder{
  color:#93a4b8 !important;
}
[data-testid="stFileUploaderDropzone"]{
  border: 1px dashed #34455b !important;
  border-radius: 18px !important;
  padding: 18px !important;
}
.stButton > button,
.stDownloadButton > button,
a[data-testid="stLinkButton"]{
  width: 100%;
  min-height: 54px;
  border-radius: 16px !important;
  border: 1px solid #314156 !important;
  background: rgba(10,18,32,.72) !important;
  color: #ffffff !important;
  font-size: 1.08rem !important;
  font-weight: 800 !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
a[data-testid="stLinkButton"]:hover{
  border-color:#6b7b92 !important;
  background: rgba(17,24,39,.95) !important;
}
div[data-testid="stCheckbox"] label p{
  color: white !important;
  font-size: 1rem !important;
}
div[data-testid="stRadio"] label p{
  color:white !important;
}
hr.misharp-divider{
  border:none;
  border-top:1px solid rgba(52,69,91,.7);
  margin:22px 0;
}
.misharp-policy{
  display:flex;
  gap:12px;
  align-items:center;
  flex-wrap:wrap;
  margin-top:10px;
}
.misharp-policy span{
  color:#b6c2d1;
  font-size:.92rem;
}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def reset_all():
    keep = {"uploader_nonce"}
    for key in list(st.session_state.keys()):
        if key not in keep:
            del st.session_state[key]
    st.session_state.uploader_nonce += 1

def sanitize_filename(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", value)
    value = value.strip("._-")
    return value[:40] or "work"

def current_payload():
    return {
        "product_url": st.session_state.get("product_url", ""),
        "product_content": st.session_state.get("product_content", ""),
        "event_content": st.session_state.get("event_content", ""),
        "sms_mode": st.session_state.get("sms_mode", "단문"),
        "selected_channels": [k for k in CHANNELS if st.session_state.get(f"ch_{k}", False)],
    }

def encode_image_to_data_url(uploaded_file):
    mime = uploaded_file.type or mimetypes.guess_type(uploaded_file.name)[0] or "image/png"
    data = uploaded_file.getvalue()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def build_channel_prompt(data):
    selected = data["selected_channels"]
    channels_kr = [CHANNELS[k] for k in selected]
    sms_mode = data.get("sms_mode", "단문")
    return f"""
당신은 대한민국 4050 여성 패션 타겟에 강한 최고 수준의 온라인 마케터이자 카피라이터입니다.
미샵 브랜드 톤은 친근한 쇼핑호스트 + 노련한 옷가게 사장언니의 "~해요" 말투입니다.
모든 결과는 한국어로 작성하세요.

[입력 정보]
상품 URL:
{data.get("product_url","")}

상품내용:
{data.get("product_content","")}

이벤트 주요내용:
{data.get("event_content","")}

[선택 채널]
{", ".join(channels_kr)}

[공통 출력 규칙]
- 선택된 채널만 작성
- 채널별 제목을 아래 형식으로 정확히 구분
==============================
[채널명]
==============================
- 불필요한 설명 금지
- 바로 복사해서 쓸 수 있게 결과만 출력

[채널별 규칙]
1) SMS문자
- {sms_mode} 기준으로 작성
- 단문이면 반드시 '(광고)미샵♥'로 시작
- 단문은 전체 길이 55자 이내
- 장문도 첫 시작은 '(광고)미샵♥'
- 상품명 반복 과다 금지

2) 앱푸시
- 첫 시작은 반드시 '광고)'로 시작
- 짧고 클릭 유도형
- 2~4개 버전 제안

3) 동영상 원고
- 20~30초 길이용
- 짧은 10줄 구성, 1줄은 20자 내외
- 첫 줄은 후킹성 헤드라인
- 마지막 줄은 CTA
- A/B 2타입 작성
- 첫 줄 헤드라인 별도 5개 타입 제안

4) 인스타 릴스 피드
- 후킹 헤드라인 + 본문 + 해시태그
- 4050 여성 공감형 문체

5) 틱톡 피드
- 짧고 템포감 있게
- 후킹 강하게

6) 유튜브 쇼츠 피드
- 제목형 후킹 + 설명형 본문
- 클릭/시청 유지 유도

7) 카카오스타일
- 최상단 후킹성 헤드라인
- 상품명 적고 한 줄 내린 뒤 상세설명 150자 이내 뉴스형식 요약
- 본문 하단 '상품 바로가기 ▼' 포함
- 그 아래 실제 URL 그대로 삽입
- 한 줄 띄우고 '일상도 스타일도 미샵처럼, 심플하게! MISHARP' 삽입
- 해시태그 30개

8) REVIEW
- 실제 후기처럼 자연스럽게
- 과장 줄이고 설득력 있게
- 짧은 버전/중간 버전 함께 제안
"""

def enforce_sms_short_constraints(text: str) -> str:
    if "[SMS문자]" not in text:
        return text

    pattern = re.compile(r"(\[SMS문자\].*?\n)(.*?)(?=\n==============================|\Z)", re.DOTALL)
    prefix = "(광고)미샵♥"

    def shorten_line(line: str) -> str:
        s = line.strip()
        if not s:
            return s
        s = re.sub(r"^\(광고\)\s*미샵\s*♥\s*", prefix, s)
        if not s.startswith(prefix):
            s = prefix + s
        s = s.replace(prefix + " ", prefix)
        return s[:55]

    def repl(match):
        header = match.group(1)
        body = match.group(2).strip()
        fixed_lines = []
        for line in body.splitlines():
            raw = line.strip()
            if not raw:
                fixed_lines.append(line)
                continue
            if raw.startswith(("타입", "-", "예시", "수신거부", "[")):
                fixed_lines.append(line)
                continue
            fixed_lines.append(shorten_line(raw))
        return header + "\n".join(fixed_lines) + "\n"

    return pattern.sub(repl, text)

def enforce_app_push_prefix(text: str) -> str:
    if "[앱푸시]" not in text:
        return text
    pattern = re.compile(r"(\[앱푸시\].*?\n)(.*?)(?=\n==============================|\Z)", re.DOTALL)
    def repl(match):
        header = match.group(1)
        body = match.group(2).strip()
        fixed = []
        for line in body.splitlines():
            s = line.strip()
            if not s:
                fixed.append(line)
                continue
            if s.startswith(("타입", "-", "[", "헤드라인")):
                fixed.append(line)
                continue
            if not s.startswith("광고)"):
                s = "광고)" + s.lstrip(" )")
            fixed.append(s)
        return header + "\n".join(fixed) + "\n"
    return pattern.sub(repl, text)

def inject_kakaostyle_url(text: str, url: str) -> str:
    if not url.strip() or "[카카오스타일]" not in text:
        return text
    pattern = re.compile(r"(\[카카오스타일\].*?)(?=\n==============================|\Z)", re.DOTALL)
    def repl(match):
        block = match.group(1)
        if url in block:
            return block
        if "상품 바로가기 ▼" in block:
            return block.replace("상품 바로가기 ▼", f"상품 바로가기 ▼\n{url}", 1)
        return block.rstrip() + f"\n상품 바로가기 ▼\n{url}\n"
    return pattern.sub(repl, text)

def generate_marketing_copy(data, uploaded_files):
    client = OpenAI()
    content = [{"type": "input_text", "text": build_channel_prompt(data)}]

    # Use up to 2 images as supporting input for better results.
    img_count = 0
    for file in uploaded_files or []:
        ftype = (file.type or "")
        if ftype.startswith("image/") and img_count < 2:
            content.append({"type": "input_image", "image_url": encode_image_to_data_url(file), "detail": "low"})
            img_count += 1

    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        input=[{"role": "user", "content": content}],
    )
    output = response.output_text
    if data.get("sms_mode") == "단문" and "sms" in data.get("selected_channels", []):
        output = enforce_sms_short_constraints(output)
    if "app_push" in data.get("selected_channels", []):
        output = enforce_app_push_prefix(output)
    if "kakaostyle" in data.get("selected_channels", []):
        output = inject_kakaostyle_url(output, data.get("product_url", ""))
    return output

CHANNELS = {
    "sms": "SMS문자",
    "app_push": "앱푸시",
    "video_script": "동영상 원고",
    "insta_reels": "인스타 릴스 피드",
    "tiktok": "틱톡 피드",
    "youtube_shorts": "유튜브 쇼츠 피드",
    "kakaostyle": "카카오스타일",
    "review": "REVIEW",
}

# ---------- Header ----------
st.markdown("""
<div class="misharp-header">
  <h1>MISHARP 광고문구 자동생성기</h1>
  <p>온라인 셀러를 위한 SNS 매체별 최적화 광고문구 자동 생성기</p>
</div>
""", unsafe_allow_html=True)

# Policy popovers
policy_cols = st.columns([1,1,6])
with policy_cols[0]:
    with st.popover("개인정보처리방침"):
        st.markdown("""
**개인정보처리방침**

본 앱은 광고문구 생성을 위한 입력 정보만 사용합니다.  
입력한 텍스트와 업로드 파일은 요청 처리 목적 범위 내에서만 활용되며,
서비스 운영과 오류 대응을 위해 일시적으로 처리될 수 있습니다.

- 수집 항목: 상품 URL, 상품 설명, 이벤트 내용, 업로드한 이미지/동영상
- 이용 목적: 광고문구 생성, 서비스 품질 개선, 오류 확인
- 보관: 별도 저장 기능을 사용하지 않는 한 영구 보관을 전제로 하지 않습니다.
- 문의: 운영자에게 별도 고지된 연락처를 통해 요청할 수 있습니다.
""")
with policy_cols[1]:
    with st.popover("서비스 약관"):
        st.markdown("""
**서비스 약관**

본 앱이 생성한 문구는 사용자가 최종 검토 후 사용하는 것을 원칙으로 합니다.

- 생성 결과의 상업적 활용 책임은 사용자에게 있습니다.
- 외부 플랫폼 정책, 광고 심의, 표시광고법 등은 사용자가 확인해야 합니다.
- 서비스 안정성 향상을 위해 기능이 변경될 수 있습니다.
- 과도한 요청 또는 비정상 사용은 제한될 수 있습니다.
""")

# ---------- Buttons ----------
btn_cols = st.columns(5)
with btn_cols[0]:
    if st.button("초기화", use_container_width=True):
        reset_all()
        st.rerun()

with btn_cols[1]:
    file_base = sanitize_filename(st.session_state.get("product_content")[:24] or st.session_state.get("product_url"))
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
            "저장한 JSON 파일 선택",
            type=["json"],
            key=f"load_json_{st.session_state.uploader_nonce}",
            label_visibility="collapsed",
        )
        if load_file is not None:
            data = json.load(load_file)
            st.session_state.product_url = data.get("product_url", "")
            st.session_state.product_content = data.get("product_content", "")
            st.session_state.event_content = data.get("event_content", "")
            st.session_state.sms_mode = data.get("sms_mode", "단문")
            for key in CHANNELS:
                st.session_state[f"ch_{key}"] = key in data.get("selected_channels", [])
            st.success("작업을 불러왔습니다.")
            st.session_state.loaded_notice = True

with btn_cols[3]:
    st.link_button("이미지추출", "https://misharp-image-crop-v1.streamlit.app/", use_container_width=True)

with btn_cols[4]:
    st.link_button("URL 단축", "https://shor.kr", use_container_width=True)

if st.session_state.loaded_notice:
    st.success("불러온 작업이 입력창에 반영되었습니다.")
    st.session_state.loaded_notice = False

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# ---------- Input area ----------
left, right = st.columns([1.25, 0.9], gap="large")

with left:
    st.markdown('<div class="misharp-section-title">입력 정보</div>', unsafe_allow_html=True)
    st.text_input(
        "상품 URL",
        key="product_url",
        placeholder="상품 URL 또는 이벤트 링크를 입력하세요",
    )
    st.text_area(
        "상품내용",
        key="product_content",
        height=240,
        placeholder="상세페이지 상품설명, 상품스펙, 소재, 핏, 컬러, 사이즈, USP 등을 입력하세요",
    )
    st.text_area(
        "이벤트 주요내용",
        key="event_content",
        height=130,
        placeholder="할인율, 기간, 혜택, 쿠폰, 무료배송 등 이벤트 정보를 입력하세요",
    )

with right:
    st.markdown('<div class="misharp-section-title">이미지 / 동영상 등록</div>', unsafe_allow_html=True)
    uploaded_media = st.file_uploader(
        "상품 이미지 또는 동영상",
        type=["png", "jpg", "jpeg", "webp", "mp4", "mov", "m4v"],
        accept_multiple_files=True,
        key=f"media_uploader_{st.session_state.uploader_nonce}",
        help="입력값은 URL, 텍스트, 이미지, 동영상 중 1개 이상이면 생성 가능합니다.",
    )
    st.caption("입력값은 URL, 텍스트, 이미지, 동영상 중 1개 이상이면 생성 가능합니다.")

    if uploaded_media:
        img_files = [f for f in uploaded_media if (f.type or "").startswith("image/")]
        vid_files = [f for f in uploaded_media if (f.type or "").startswith("video/")]

        if img_files:
            preview_cols = st.columns(min(2, len(img_files)))
            for i, img in enumerate(img_files[:2]):
                with preview_cols[i]:
                    st.image(img, use_container_width=True)

        if vid_files:
            for vf in vid_files[:1]:
                st.video(vf)

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# ---------- Channel select ----------
st.markdown('<div class="misharp-section-title" style="font-size:1.8rem;">출력 채널 선택</div>', unsafe_allow_html=True)
ch1, ch2, ch3, ch4 = st.columns(4)
with ch1:
    st.checkbox("SMS문자", key="ch_sms")
    st.checkbox("앱푸시", key="ch_app_push")
with ch2:
    st.checkbox("동영상 원고", key="ch_video_script")
    st.checkbox("인스타 릴스 피드", key="ch_insta_reels")
with ch3:
    st.checkbox("틱톡 피드", key="ch_tiktok")
    st.checkbox("유튜브 쇼츠 피드", key="ch_youtube_shorts")
with ch4:
    st.checkbox("카카오스타일", key="ch_kakaostyle")
    st.checkbox("REVIEW", key="ch_review")

sms_left, _ = st.columns([0.28, 0.72])
with sms_left:
    st.radio("SMS 유형", ["단문", "장문"], key="sms_mode", horizontal=True)

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# ---------- Generate ----------
gen_cols = st.columns([1.2, 3])
with gen_cols[0]:
    generate = st.button("문구 생성", use_container_width=True)
with gen_cols[1]:
    st.markdown('<div class="misharp-mini">선택 채널을 한 번에 생성합니다. 결과는 아래 카드에 정리됩니다.</div>', unsafe_allow_html=True)

if generate:
    payload = current_payload()
    has_any_input = any([
        payload["product_url"].strip(),
        payload["product_content"].strip(),
        payload["event_content"].strip(),
        bool(uploaded_media),
    ])
    if not has_any_input:
        st.warning("URL, 상품내용, 이벤트 주요내용, 이미지/동영상 중 하나 이상 입력해주세요.")
    elif not payload["selected_channels"]:
        st.warning("출력 채널을 하나 이상 선택해주세요.")
    else:
        with st.spinner("문구를 생성하고 있습니다..."):
            try:
                result = generate_marketing_copy(payload, uploaded_media)
                st.session_state.generated_result = result
            except Exception as e:
                st.error(f"생성 중 오류가 발생했습니다: {e}")

if st.session_state.get("generated_result"):
    st.markdown('<div class="misharp-result-card">', unsafe_allow_html=True)
    st.markdown('<div class="misharp-section-title" style="font-size:1.8rem; margin-bottom:10px;">생성 결과</div>', unsafe_allow_html=True)
    st.text_area(
        "결과",
        value=st.session_state.get("generated_result", ""),
        height=540,
        label_visibility="collapsed",
    )
    st.download_button(
        "TXT 다운로드",
        data=st.session_state.get("generated_result", ""),
        file_name=f"misharp_copy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=False,
    )
    st.markdown('</div>', unsafe_allow_html=True)
