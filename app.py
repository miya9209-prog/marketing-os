
import streamlit as st
import json
from datetime import datetime
from openai import OpenAI

st.set_page_config(page_title="MISHARP Marketing OS", layout="wide")

def truncate_sms(text):
    prefix = "(광고)미샵♥"
    if not text.startswith(prefix):
        text = prefix + text
    return text[:55]

def build_prompt(data, channels):
    base = f"""당신은 최고의 온라인마케터이자 카피라이터입니다.

상품내용:
{data.get('product','')}

이벤트:
{data.get('event','')}

URL:
{data.get('url','')}
"""

    req = "아래 채널별로 각각 결과를 구분해서 작성:\n"

    if "sms" in channels:
        req += "- SMS 단문/장문\n"
    if "push" in channels:
        req += "- 앱푸시 (반드시 '광고)'로 시작)\n"
    if "video" in channels:
        req += "- 동영상 원고 (10줄)\n"
    if "insta" in channels:
        req += "- 인스타 릴스 피드\n"
    if "tiktok" in channels:
        req += "- 틱톡 피드\n"
    if "shorts" in channels:
        req += "- 유튜브 쇼츠\n"
    if "kakao" in channels:
        req += "- 카카오스타일 (상품 바로가기 URL 포함)\n"
    if "review" in channels:
        req += "- 리뷰\n"

    return base + req

def call_gpt(prompt):
    client = OpenAI()
    res = client.responses.create(
        model="gpt-5.3",
        input=prompt,
    )
    return res.output_text

st.title("MISHARP 광고문구 자동생성기")

cols = st.columns(5)

if cols[0].button("초기화"):
    st.session_state.clear()
    st.rerun()

def save_state():
    data = {
        "product": st.session_state.get("product",""),
        "event": st.session_state.get("event",""),
        "url": st.session_state.get("url","")
    }
    return json.dumps(data, ensure_ascii=False, indent=2)

filename = f"misharp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
cols[1].download_button("작업 저장", save_state(), file_name=filename)

uploaded = cols[2].file_uploader("작업 불러오기", type=["json"])
if uploaded:
    data = json.load(uploaded)
    st.session_state.update(data)
    st.success("불러오기 완료")

cols[3].link_button("이미지추출", "https://misharp-image-crop-v1.streamlit.app/")
cols[4].link_button("URL 단축", "https://shor.kr")

st.text_input("상품 URL", key="url")
st.text_area("상품내용", key="product", height=150)
st.text_area("이벤트 주요내용", key="event", height=100)

channels = {
    "sms": st.checkbox("SMS문자"),
    "push": st.checkbox("앱푸시"),
    "video": st.checkbox("동영상 원고"),
    "insta": st.checkbox("인스타 릴스 피드"),
    "tiktok": st.checkbox("틱톡 피드"),
    "shorts": st.checkbox("유튜브 쇼츠 피드"),
    "kakao": st.checkbox("카카오스타일"),
    "review": st.checkbox("REVIEW"),
}

if st.button("문구 생성"):
    selected = [k for k,v in channels.items() if v]

    if not selected:
        st.warning("채널을 선택하세요")
    else:
        prompt = build_prompt(st.session_state, selected)

        with st.spinner("생성중..."):
            result = call_gpt(prompt)

        if "sms" in selected:
            result = truncate_sms(result)

        if "push" in selected and not result.startswith("광고)"):
            result = "광고)" + result

        if "kakao" in selected:
            result += "\n\n상품 바로가기 ▼\n" + st.session_state.get("url","")

        st.text_area("결과", result, height=400)

st.markdown("[개인정보처리방침] | [서비스 약관]")
