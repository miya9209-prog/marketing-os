
import streamlit as st

st.set_page_config(layout="wide")

st.markdown("""
<style>
.block-container{
    padding-top: 3.5rem !important;
    padding-bottom: 2rem;
}

.header-box{
    background:#f5f2f1;
    border-radius:24px;
    padding:36px 32px;
    margin-bottom:20px;
}
.header-title{
    font-size:42px;
    font-weight:900;
    margin:0;
}

.footer-line{
    border-top:1px solid rgba(255,255,255,0.2);
    margin-top:40px;
    padding-top:12px;
    text-align:center;
    font-size:12px;
    color:#94a3b8;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <div class="header-title">MISHARP 광고문구 자동생성기</div>
</div>
""", unsafe_allow_html=True)

st.text_area("상품내용", height=200)
st.button("문구 생성")

st.markdown("""
<div class="footer-line">
made by MISHARP COMPANY, MIYAWA. 2006. All rights reserved.
</div>
""", unsafe_allow_html=True)
