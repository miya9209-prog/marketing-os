
import streamlit as st
import json, re, os
from datetime import datetime
from openai import OpenAI

st.set_page_config(
    page_title="MISHARP 광고문구 자동생성기",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------- Styles ----------
st.markdown("""
<style>
html, body, [class*="css"] {
  font-family: "Pretendard","Noto Sans KR",sans-serif;
}
.stApp {
  background: linear-gradient(180deg,#020617 0%, #030816 100%);
}
[data-testid="stSidebar"], [data-testid="stSidebarNav"], [data-testid="collapsedControl"]{
  display:none !important;
}
.block-container {
  max-width: 1240px;
  padding-top: 2.4rem !important;
  padding-bottom: 2.8rem;
}
.misharp-header {
  background: #f5f2f1;
  border-radius: 26px;
  padding: 30px 32px 26px 32px;
  color: #251a2e;
  box-shadow: 0 8px 28px rgba(0,0,0,.18);
  margin-top: 0.4rem;
  margin-bottom: 14px;
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
div[data-testid="stPopover"] > button,
button[kind="secondary"],
button[kind="tertiary"]{
  width: 100% !important;
  height: 52px !important;
  min-height: 52px !important;
  max-height: 52px !important;
  border-radius: 16px !important;
  border: 1px solid #314156 !important;
  background: rgba(10,18,32,.72) !important;
  color:#fff !important;
  font-weight:800 !important;
  padding: 0 16px !important;
  line-height: 1 !important;
  display:flex !important;
  align-items:center !important;
  justify-content:center !important;
  box-sizing:border-box !important;
  margin:0 !important;
}
div[data-testid="stPopover"]{
  width:100% !important;
}
div[data-testid="stPopover"] > button p,
.stButton > button p,
.stDownloadButton > button p,
button[kind="secondary"] p,
button[kind="tertiary"] p{
  font-size: 1.08rem !important;
  font-weight: 800 !important;
  margin: 0 !important;
}
hr.misharp-divider{
  border:none;
  border-top:1px solid rgba(52,69,91,.7);
  margin:18px 0;
}
div[data-testid="stTextInputRoot"] input,
div[data-testid="stTextArea"] textarea{
  border-radius: 14px !important;
  background: rgba(31,41,55,.82) !important;
  color: #fff !important;
}
div[data-testid="stTextInputRoot"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder{
  color:#97a5b8 !important;
}
[data-testid="stFileUploaderDropzone"]{
  border: 1px dashed #34455b !important;
  border-radius: 18px !important;
  background: rgba(31,41,55,.82) !important;
}
div[data-testid="stCheckbox"] label p,
div[data-testid="stRadio"] label p,
label, .stMarkdown, .stCaption, .stTextInput label, .stTextArea label {
  color:#f8fafc !important;
}
.misharp-section-title{
  font-size: 1.9rem;
  font-weight: 900;
  letter-spacing: -0.03em;
  margin: 0 0 12px 0;
  color: white;
}
.misharp-sub{
  color:#b6c2d1;
  font-size:.93rem;
}
.misharp-result textarea{
  min-height: 420px !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- State ----------
if "uploader_nonce" not in st.session_state:
    st.session_state.uploader_nonce = 0

CHANNELS = [
    ("ch_sms", "SMS문자"),
    ("ch_app_push", "앱푸시"),
    ("ch_video_script", "동영상 원고"),
    ("ch_insta_reels", "인스타 릴스 피드"),
    ("ch_tiktok", "틱톡 피드"),
    ("ch_youtube_shorts", "유튜브 쇼츠 피드"),
    ("ch_kakaostyle", "카카오스타일"),
    ("ch_review", "REVIEW"),
]

def reset_all():
    keep = {"uploader_nonce"}
    for k in list(st.session_state.keys()):
        if k not in keep:
            del st.session_state[k]
    st.session_state.uploader_nonce += 1

def sanitize_filename(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", value)
    value = value.strip("._-")
    return value[:40] or "work"

def current_payload():
    return {
        "product_url": st.session_state.get("product_url",""),
        "product_content": st.session_state.get("product_content",""),
        "event_content": st.session_state.get("event_content",""),
        "sms_mode": st.session_state.get("sms_mode","단문"),
        "selected_channels": [key for key, _ in CHANNELS if st.session_state.get(key, False)],
    }

def build_prompt(data):
    selected = data["selected_channels"]
    names = []
    for key, label in CHANNELS:
        if key in selected:
            names.append(label)
    return f"""당신은 최고의 온라인마케터이자 카피라이터입니다.
모든 결과는 한국어로 작성하세요.
4050 여성 타겟에 맞게 공감형이면서 실용적으로 작성하세요.

상품내용:
{data.get('product_content','')}

이벤트:
{data.get('event_content','')}

URL:
{data.get('product_url','')}

선택 채널:
{", ".join(names)}

선택된 채널만 각각 구분해서 작성하세요.
"""

def call_gpt(prompt):
    client = OpenAI()
    res = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        input=prompt
    )
    return res.output_text

def truncate_sms(text):
    prefix="(광고)미샵♥"
    if not text.startswith(prefix):
        text = prefix + text
    return text[:55]

# ---------- Header ----------
st.markdown("""
<div class="misharp-header">
  <h1>MISHARP 광고문구 자동생성기</h1>
  <p>온라인 셀러를 위한 SNS 매체별 최적화 광고문구 자동 생성기</p>
</div>
""", unsafe_allow_html=True)

# ---------- Top buttons ----------
btn_cols = st.columns(5, gap="small")

with btn_cols[0]:
    if st.button("초기화", use_container_width=True):
        reset_all()
        st.rerun()

with btn_cols[1]:
    product_content = st.session_state.get("product_content") or ""
    product_url = st.session_state.get("product_url") or ""
    file_base = sanitize_filename(product_content[:24] if product_content else product_url)
    save_name = f"misharp_marketing_os_{file_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    st.download_button(
        "작업 저장",
        data=json.dumps(current_payload(), ensure_ascii=False, indent=2),
        file_name=save_name,
        mime="application/json",
        use_container_width=True
    )

with btn_cols[2]:
    with st.popover("작업 불러오기", use_container_width=True):
        f = st.file_uploader("파일 선택", type=["json"], label_visibility="collapsed", key=f"load_{st.session_state.uploader_nonce}")
        if f:
            data = json.load(f)
            st.session_state.product_url = data.get("product_url","")
            st.session_state.product_content = data.get("product_content","")
            st.session_state.event_content = data.get("event_content","")
            st.session_state.sms_mode = data.get("sms_mode","단문")
            for key, _ in CHANNELS:
                st.session_state[key] = key in data.get("selected_channels", [])
            st.success("불러오기 완료")

with btn_cols[3]:
    st.link_button("이미지추출", "https://misharp-image-crop-v1.streamlit.app/", use_container_width=True)

with btn_cols[4]:
    st.link_button("URL 단축", "https://shor.kr", use_container_width=True)

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# ---------- Inputs ----------
c1, c2 = st.columns([1.05, 0.95], gap="large")
with c1:
    st.markdown('<div class="misharp-section-title">입력 정보</div>', unsafe_allow_html=True)
    st.text_input("상품 URL", key="product_url", placeholder="상품 URL 또는 이벤트 링크를 입력하세요")
    st.text_area("상품내용", key="product_content", height=220, placeholder="상세페이지 상품설명, 상품스펙, 소재, 핏, 컬러, 사이즈, USP 등을 입력하세요")
    st.text_area("이벤트 주요내용", key="event_content", height=120, placeholder="할인율, 기간, 혜택, 쿠폰, 무료배송 등 이벤트 정보를 입력하세요")

with c2:
    st.markdown('<div class="misharp-section-title">이미지 / 동영상 등록</div>', unsafe_allow_html=True)
    st.file_uploader("파일 업로드", accept_multiple_files=True, key=f"media_{st.session_state.uploader_nonce}")
    st.caption("입력값은 URL, 텍스트, 이미지, 동영상 중 1개 이상이면 생성 가능합니다.")

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# ---------- Channel selection (restored) ----------
st.markdown('<div class="misharp-section-title" style="font-size:1.75rem;">출력 채널 선택</div>', unsafe_allow_html=True)
r1, r2, r3, r4 = st.columns(4)
with r1:
    st.checkbox("SMS문자", key="ch_sms")
    st.checkbox("앱푸시", key="ch_app_push")
with r2:
    st.checkbox("동영상 원고", key="ch_video_script")
    st.checkbox("인스타 릴스 피드", key="ch_insta_reels")
with r3:
    st.checkbox("틱톡 피드", key="ch_tiktok")
    st.checkbox("유튜브 쇼츠 피드", key="ch_youtube_shorts")
with r4:
    st.checkbox("카카오스타일", key="ch_kakaostyle")
    st.checkbox("REVIEW", key="ch_review")

sms_col, _ = st.columns([0.28, 0.72])
with sms_col:
    st.radio("SMS 유형", ["단문", "장문"], key="sms_mode", horizontal=True)

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# ---------- Generate ----------
if st.button("문구 생성", use_container_width=True):
    payload = current_payload()
    has_input = bool(payload["product_url"] or payload["product_content"] or payload["event_content"])
    if not has_input:
        st.warning("입력값을 하나 이상 입력하세요.")
    elif not payload["selected_channels"]:
        st.warning("출력 채널을 하나 이상 선택하세요.")
    else:
        with st.spinner("생성중..."):
            out = call_gpt(build_prompt(payload))
        if "ch_sms" in payload["selected_channels"] and payload["sms_mode"] == "단문":
            out = truncate_sms(out)
        st.session_state.generated_result = out

if st.session_state.get("generated_result"):
    st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)
    st.markdown('<div class="misharp-section-title" style="font-size:1.75rem;">생성 결과</div>', unsafe_allow_html=True)
    st.text_area("결과", value=st.session_state.get("generated_result",""), height=420, label_visibility="collapsed")
