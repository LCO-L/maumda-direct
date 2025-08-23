import streamlit as st
from services.llm import analyze_text          # (이전 단계에서 만든 최신 SDK + JSON 강제)
from services.utils import normalize_data      # 날짜/금액 예쁘게
from services.notion import save_record        # 방금 파일

st.set_page_config(page_title="M-DI 기록 시스템", page_icon="⚒️", layout="centered")
st.title("⚒️ M-DI 기록 시스템")
st.write("자연어 입력을 구조화하여 정당성 있는 기록으로 변환합니다.")

# Session State 초기화
if 'analyzed_data' not in st.session_state:
    st.session_state.analyzed_data = None
if 'saved' not in st.session_state:
    st.session_state.saved = False

user_input = st.text_area(
    "자연어 입력",
    placeholder="예) 북구청에서 다음주 수요일에 1000만원 잔금 들어온다."
)

# AI 분석 버튼
if st.button("AI 분석하기", type="primary"):
    if not user_input.strip():
        st.warning("내용을 입력해주세요.")
    else:
        with st.spinner("AI가 데이터를 분석 중입니다..."):
            try:
                raw = analyze_text(user_input)   # dict (who/what/when/where/why/how)
                normalized = normalize_data(raw)  # when, what 정제 + 보기용 필드 추가
                
                # 분석 결과를 session state에 저장
                st.session_state.analyzed_data = normalized
                st.session_state.saved = False  # 새로 분석했으므로 저장 상태 리셋
                
            except Exception as e:
                st.error(f"AI 호출 실패: {e}")
                st.session_state.analyzed_data = None

# 분석 결과가 있으면 표시
if st.session_state.analyzed_data:
    st.subheader("AI 분석 결과")
    st.json(st.session_state.analyzed_data)
    
    # 저장 버튼 (독립적으로 처리)
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("노션에 저장", type="secondary", disabled=st.session_state.saved):
            with st.spinner("Notion에 저장 중..."):
                status, msg = save_record(st.session_state.analyzed_data)
            
            if 200 <= status < 300:
                st.success(f"✅ 저장 완료! [노션에서 보기]({msg})")
                st.session_state.saved = True
            else:
                st.error(f"❌ 저장 실패\nHTTP {status}\n{msg}")
    
    with col2:
        if st.session_state.saved:
            st.info("이미 저장되었습니다. 새로운 내용을 분석하려면 위에서 다시 입력하세요.")

# 디버깅 정보 (개발 중에만 표시)
with st.expander("🔧 디버깅 정보"):
    st.write("Session State:")
    st.write(f"- analyzed_data 있음: {st.session_state.analyzed_data is not None}")
    st.write(f"- saved 상태: {st.session_state.saved}")
    if st.session_state.analyzed_data:
        st.write("- 현재 데이터:")
        st.json(st.session_state.analyzed_data)