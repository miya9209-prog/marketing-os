
import streamlit as st

st.set_page_config(layout="wide")

st.markdown("""
<style>
.custom-btn{
display:inline-block;
padding:12px 20px;
border-radius:12px;
border:1px solid #314156;
background:#0a1220;
color:white !important;
text-decoration:none;
font-weight:700;
margin-right:8px;
}
.custom-btn:hover{
background:#0a1220;
color:white !important;
}
</style>
""", unsafe_allow_html=True)

st.title("MISHARP 광고문구 자동생성기")

cols = st.columns(5)

with cols[0]:
    if st.button("초기화"):
        st.session_state.clear()

with cols[1]:
    st.download_button("작업 저장","{}",file_name="test.json")

with cols[2]:
    st.markdown('<a href="#" class="custom-btn">작업 불러오기</a>', unsafe_allow_html=True)

with cols[3]:
    st.markdown('<a href="https://misharp-image-crop-v1.streamlit.app/" target="_blank" class="custom-btn">이미지추출</a>', unsafe_allow_html=True)

with cols[4]:
    st.markdown('<a href="https://shor.kr" target="_blank" class="custom-btn">URL 단축</a>', unsafe_allow_html=True)

st.text_area("상품내용")

st.button("문구 생성")

st.markdown("made by MISHARP COMPANY, MIYAWA. 2006. All rights reserved.")
