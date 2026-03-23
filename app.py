
import streamlit as st
import json, re
from datetime import datetime
from openai import OpenAI

st.set_page_config(page_title="MISHARP 광고문구 자동생성기", layout="wide")

if "result" not in st.session_state:
    st.session_state.result = ""

def reset_all():
    st.session_state.clear()
    st.session_state.result = ""

def sanitize_filename(value):
    value = (value or "").strip()
    value = re.sub(r"[^0-9A-Za-z가-힣]+", "_", value)
    return value[:30] or "work"

def build_prompt(data, channels):
    return f"상품내용:{data.get('product','')} 이벤트:{data.get('event','')} URL:{data.get('url','')} 채널:{channels}"

def call_gpt(prompt):
    client = OpenAI()
    res = client.responses.create(model="gpt-4.1-mini", input=prompt)
    return res.output_text

def truncate_sms(text):
    prefix="(광고)미샵♥"
    if not text.startswith(prefix):
        text = prefix + text
    return text[:55]

st.title("MISHARP 광고문구 자동생성기")

c1,c2,c3,c4,c5 = st.columns(5)

with c1:
    if st.button("초기화"):
        reset_all()
        st.rerun()

with c2:
    name = sanitize_filename(st.session_state.get("product",""))
    fname = f"{name}_{datetime.now().strftime('%H%M%S')}.json"
    st.download_button("작업 저장", json.dumps(st.session_state), file_name=fname)

with c3:
    file = st.file_uploader("불러오기", type=["json"])
    if file:
        data = json.load(file)
        st.session_state.update(data)

with c4:
    st.link_button("이미지추출","https://misharp-image-crop-v1.streamlit.app/")
with c5:
    st.link_button("URL 단축","https://shor.kr")

col1,col2 = st.columns(2)
with col1:
    st.text_input("상품 URL", key="url")
    st.text_area("상품내용", key="product")
    st.text_area("이벤트", key="event")

with col2:
    st.file_uploader("이미지/영상", accept_multiple_files=True)

channels=[]
st.markdown("### 출력 채널 선택")
if st.checkbox("SMS"): channels.append("sms")
if st.checkbox("앱푸시"): channels.append("push")
if st.checkbox("동영상"): channels.append("video")

if st.button("문구 생성"):
    if channels:
        try:
            res = call_gpt(build_prompt(st.session_state, channels))
            if "sms" in channels:
                res = truncate_sms(res)
            st.session_state.result = res
        except Exception as e:
            st.error(e)
    else:
        st.warning("채널 선택")

st.markdown("### 생성 결과")
st.text_area("", st.session_state.result, height=300)

st.markdown("---")
st.markdown("© 2026 MISHARP")
