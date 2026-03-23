
import streamlit as st
import json, re, os
from datetime import datetime
from openai import OpenAI

st.set_page_config(
    page_title="MISHARP 광고문구 자동생성기",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
  padding-top: 2.4rem !important;   /* 상단 잘림 방지 */
  padding-bottom: 2.5rem;
}
.misharp-header {
  background: #f5f2f1;
  border-radius: 26px;
  padding: 30px 32px 26px 32px;
  color: #251a2e;
  box-shadow: 0 8px 28px rgba(0,0,0,.18);
  margin-top: 0.4rem;              /* 헤더 위 여백 추가 */
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
a[data-testid="stLinkButton"]{
  width: 100%;
  min-height: 52px;
  border-radius: 16px !important;
  border: 1px solid #314156 !important;
  background: rgba(10,18,32,.72) !important;
  color:#fff !important;
  font-weight:800 !important;
}
hr.misharp-divider{
  border:none;
  border-top:1px solid rgba(52,69,91,.7);
  margin:18px 0;
}
div[data-testid="stTextInputRoot"] input,
div[data-testid="stTextArea"] textarea{
  border-radius: 14px !important;
}
</style>
""", unsafe_allow_html=True)

def reset_all():
    for k in list(st.session_state.keys()):
        if k != "uploader_nonce":
            del st.session_state[k]
    st.session_state.uploader_nonce = st.session_state.get("uploader_nonce", 0) + 1

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
    }

def build_prompt(data):
    return f"""당신은 최고의 온라인마케터이자 카피라이터입니다.

상품내용:
{data.get('product_content','')}

이벤트:
{data.get('event_content','')}

URL:
{data.get('product_url','')}

채널별로 결과를 구분해서 작성하세요.
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

st.markdown("""
<div class="misharp-header">
  <h1>MISHARP 광고문구 자동생성기</h1>
  <p>온라인 셀러를 위한 SNS 매체별 최적화 광고문구 자동 생성기</p>
</div>
""", unsafe_allow_html=True)

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
        f = st.file_uploader("파일 선택", type=["json"], label_visibility="collapsed")
        if f:
            data = json.load(f)
            st.session_state.product_url = data.get("product_url","")
            st.session_state.product_content = data.get("product_content","")
            st.session_state.event_content = data.get("event_content","")
            st.success("불러오기 완료")

with btn_cols[3]:
    st.link_button("이미지추출", "https://misharp-image-crop-v1.streamlit.app/", use_container_width=True)

with btn_cols[4]:
    st.link_button("URL 단축", "https://shor.kr", use_container_width=True)

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown("### 입력 정보")
    st.text_input("상품 URL", key="product_url")
    st.text_area("상품내용", key="product_content", height=220)
    st.text_area("이벤트 주요내용", key="event_content", height=120)

with c2:
    st.markdown("### 이미지 / 동영상 등록")
    st.file_uploader("파일 업로드", accept_multiple_files=True)

st.markdown("<hr class='misharp-divider'>", unsafe_allow_html=True)

if st.button("문구 생성", use_container_width=True):
    payload = current_payload()
    if not (payload["product_url"] or payload["product_content"] or payload["event_content"]):
        st.warning("입력값을 하나 이상 입력하세요.")
    else:
        with st.spinner("생성중..."):
            out = call_gpt(build_prompt(payload))
        out = truncate_sms(out)
        st.text_area("결과", out, height=420)
