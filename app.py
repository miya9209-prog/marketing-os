
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
.misharp-section-title{
  font-size: 2.05rem;
  font-weight: 900;
  letter-spacing: -0.03em;
  margin: 0 0 14px 0;
  color: white;
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
hr.misharp-divider{
  border:none;
  border-top:1px solid rgba(52,69,91,.7);
  margin:22px 0;
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
    return value[:40] or "work"

def current_payload():
    return {
        "product_url": st.session_state.get("product_url", ""),
        "product_content": st.session_state.get("product_content", ""),
        "event_content": st.session_state.get("event_content", ""),
        "sms_mode": st.session_state.get("sms_mode", "단문"),
        "selected_channels": [],
    }

# ---------- Header ----------
st.markdown("""
<div class="misharp-header">
  <h1>MISHARP 광고문구 자동생성기</h1>
  <p>온라인 셀러를 위한 SNS 매체별 최적화 광고문구 자동 생성기</p>
</div>
""", unsafe_allow_html=True)

# ---------- Buttons ----------
btn_cols = st.columns(5)

if btn_cols[0].button("초기화"):
    reset_all()
    st.rerun()

# FIXED PART
product_content = st.session_state.get("product_content") or ""
product_url = st.session_state.get("product_url") or ""
file_base = sanitize_filename(product_content[:24] if product_content else product_url)

save_name = f"misharp_marketing_os_{file_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

btn_cols[1].download_button(
    "작업 저장",
    data=json.dumps(current_payload(), ensure_ascii=False, indent=2),
    file_name=save_name,
)

btn_cols[2].file_uploader("작업 불러오기", type=["json"])

btn_cols[3].link_button("이미지추출", "https://misharp-image-crop-v1.streamlit.app/")
btn_cols[4].link_button("URL 단축", "https://shor.kr")

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

# ---------- Inputs ----------
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 입력 정보")
    st.text_input("상품 URL", key="product_url")
    st.text_area("상품내용", key="product_content")
    st.text_area("이벤트 주요내용", key="event_content")

with col2:
    st.markdown("### 이미지 / 동영상 등록")
    st.file_uploader("파일 업로드", accept_multiple_files=True)

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

st.button("문구 생성")
