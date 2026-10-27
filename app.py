import streamlit as st

# 기존 설정 코드
st.set_page_config(page_title="내 앱", layout="centered")

# 스트림릿 기본 UI 숨기기 CSS
hide_streamlit_style = """
<style>
/* 우측 상단 햄버거 메뉴 및 GitHub/Deploy 마크(헤더 전체) 숨기기 */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}

/* 우측 하단 스트림릿 워터마크(푸터) 숨기기 */
footer {visibility: hidden;}
</style>
"""

# CSS 적용 (unsafe_allow_html=True 옵션 필수)
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
