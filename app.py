
import streamlit as st

st.set_page_config(layout="wide")

st.title("MISHARP 광고문구 자동생성기")

st.text_area("상품내용")
st.button("문구 생성")

# ---------- RIGHT BOTTOM FOOTER ----------
st.markdown("""
<style>
.footer-fixed {
    position: fixed;
    bottom: 10px;
    right: 20px;
    font-size: 12px;
    color: #94a3b8;
    opacity: 0.8;
}
.footer-fixed a {
    color: #94a3b8;
    text-decoration: none;
    margin-left: 8px;
}
.footer-fixed a:hover {
    text-decoration: underline;
}
</style>

<div class="footer-fixed">
© 2026 MISHARP
<a href="#">개인정보</a> |
<a href="#">약관</a>
</div>
""", unsafe_allow_html=True)
