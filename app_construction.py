import streamlit as st
import streamlit.components.v1 as components
from services.llm import analyze_text
from services.utils import normalize_data
from services.notion import save_record
from services.voice_input import get_voice_input
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
from PIL import Image
import io

# 페이지 설정
st.set_page_config(page_title="마음다이렉트 💼", page_icon="🏗️", layout="wide")

# 세션 상태 초기화
if 'analyzed_data' not in st.session_state:
    st.session_state.analyzed_data = None
if 'saved' not in st.session_state:
    st.session_state.saved = False
if 'voice_input' not in st.session_state:
    st.session_state.voice_input = ""

# 헬퍼 함수들
def extract_amount(text):
    """텍스트에서 금액 추출"""
    if not text:
        return None
    
    patterns = [
        r'(\d+)만\s*원',
        r'(\d+)만',
        r'(\d+,\d+)원',
        r'(\d+)원'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return text

def process_ocr_image(image):
    """이미지에서 텍스트 추출 (간단한 시뮬레이션)"""
    # 실제로는 Google Vision API나 AWS Textract 사용
    # 여기서는 데모용 시뮬레이션
    demo_text = """
    한솔건설자재
    2025-01-23
    
    시멘트 20포: 150,000원
    타일 50박스: 850,000원
    
    합계: 1,000,000원
    """
    return demo_text

def create_payment_chart(data):
    """잔금 현황 차트 생성"""
    fig = go.Figure()
    
    for index, row in data.iterrows():
        # 전체 대비 받은 금액 비율
        received_pct = (row['받은금액'] / row['계약금액']) * 100
        remaining_pct = 100 - received_pct
        
        fig.add_trace(go.Bar(
            name='받은 돈',
            x=[row['현장명']],
            y=[row['받은금액']],
            text=f"{row['받은금액']:,}원",
            textposition='inside',
            marker_color='#4CAF50'
        ))
        
        fig.add_trace(go.Bar(
            name='받을 돈',
            x=[row['현장명']],
            y=[row['잔금']],
            text=f"{row['잔금']:,}원",
            textposition='inside',
            marker_color='#FF9800'
        ))
    
    fig.update_layout(
        barmode='stack',
        height=400,
        title="현장별 수금 현황",
        yaxis_title="금액 (원)",
        showlegend=True,
        hovermode='x unified'
    )
    
    return fig

# 타이틀
st.title("🏗️ 마음다이렉트")
st.caption("건설현장 사장님의 든든한 비즈니스 파트너")

# 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["💰 미수금", "📸 영수증", "📊 현황", "💳 잔금표"])

# Tab 1: 미수금 입력 부분 수정
with tab1:
    st.subheader("받을 돈 기록하기")
    
    # 음성/텍스트 입력 통합
    input_method = st.radio(
        "입력 방법 선택",
        ["✍️ 텍스트 입력", "🎤 음성 녹음"],
        horizontal=True
    )
    
    user_input = ""
    
    if input_method == "🎤 음성 녹음":
        st.info("🎤 녹음 버튼을 누르고 말씀하세요 (최대 30초)")
        
        try:
            from audio_recorder_streamlit import audio_recorder
            from openai import OpenAI
            import tempfile
            import os
            
            # 녹음 컴포넌트
            audio_bytes = audio_recorder(
                text="🔴 녹음 시작 (클릭)",
                recording_color="#FF0000",
                neutral_color="#008CBA",
                icon_name="microphone-lines",
                icon_size="6x",
                pause_threshold=2.0,
                sample_rate=16000
            )
            
            if audio_bytes:
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.audio(audio_bytes, format="audio/wav")
                
                with col2:
                    if st.button("🤖 인식", type="primary", use_container_width=True):
                        with st.spinner("인식 중..."):
                            try:
                                # OpenAI 클라이언트 초기화
                                api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
                                if not api_key:
                                    st.error("API 키가 설정되지 않았습니다")
                                else:
                                    client = OpenAI(api_key=api_key)
                                    
                                    # 임시 파일 생성
                                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                                        tmp.write(audio_bytes)
                                        tmp_path = tmp.name
                                    
                                    # Whisper API 호출
                                    with open(tmp_path, 'rb') as audio_file:
                                        response = client.audio.transcriptions.create(
                                            model="whisper-1",
                                            file=audio_file,
                                            language="ko",
                                            response_format="text"
                                        )
                                    
                                    # 임시 파일 삭제
                                    os.unlink(tmp_path)
                                    
                                    # 결과 저장
                                    user_input = response
                                    st.success("✅ 인식 완료!")
                                    st.text_area("인식된 내용", user_input, height=100)
                                    
                            except Exception as e:
                                st.error(f"오류: {str(e)}")
                                st.info("다시 녹음해주세요")
        
        except ImportError:
            st.error("음성 녹음 패키지 설치가 필요합니다")
            st.code("pip install audio-recorder-streamlit", language="bash")
            
            # 대체 방법 제공
            st.divider()
            st.markdown("#### 대체 방법: 파일 업로드")
            audio_file = st.file_uploader("음성 파일", type=['wav', 'mp3', 'm4a'])
            
            if audio_file:
                st.audio(audio_file)
                if st.button("🤖 AI 인식"):
                    st.info("파일 인식 기능 준비 중...")
    
    else:  # 텍스트 입력
        user_input = st.text_area(
            "내용을 입력하세요",
            placeholder="""예시:
• 강남 아파트 타일공사 500만원 다음주 받기로 했어
• 북구청 방수 작업 끝나면 1000만원 잔금
• 김사장한테 인테리어 대금 300만원 15일에 받아야 돼""",
            height=150
        )
    
    # 빠른 입력 템플릿
    st.markdown("#### 빠른 입력")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 계약금", use_container_width=True):
            user_input = "현장명 계약금 금액 오늘 받음"
    
    with col2:
        if st.button("💵 중도금", use_container_width=True):
            user_input = "현장명 중도금 금액 날짜 예정"
    
    with col3:
        if st.button("💰 잔금", use_container_width=True):
            user_input = "현장명 잔금 금액 완료시 받기"
    
    # 분석 버튼
    if st.button("📝 기록하기", type="primary", use_container_width=True):
        if not user_input or not user_input.strip():
            st.warning("내용을 입력하거나 녹음해주세요.")
        else:
            with st.spinner("AI가 분석 중..."):
                try:
                    raw = analyze_text(user_input)
                    normalized = normalize_data(raw)
                    
                    # 금액 추출
                    amount = extract_amount(normalized.get('what', ''))
                    if amount:
                        normalized['display_amount'] = amount
                    
                    st.session_state.analyzed_data = normalized
                    st.session_state.saved = False
                    
                except Exception as e:
                    st.error(f"처리 실패: {e}")
# Tab 2: 영수증 OCR
with tab2:
    st.subheader("영수증 촬영 & 자동 인식")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 카메라 입력
        uploaded_file = st.camera_input("영수증 촬영 📸")
        
        # 또는 파일 업로드
        uploaded_image = st.file_uploader(
            "또는 사진 선택",
            type=['png', 'jpg', 'jpeg'],
            help="영수증 사진을 선택하세요"
        )
        
        image_to_process = uploaded_file or uploaded_image
        
        if image_to_process:
            st.image(image_to_process, caption="업로드된 영수증")
    
    with col2:
        if image_to_process:
            st.markdown("### 📝 인식 결과")
            
            with st.spinner("영수증 분석 중..."):
                # OCR 처리 (실제로는 Google Vision API 사용)
                extracted_text = process_ocr_image(image_to_process)
                
            # 추출된 텍스트 표시
            st.text_area("인식된 내용", extracted_text, height=200)
            
            # 카테고리 선택
            category = st.selectbox(
                "분류",
                ["🔨 자재비", "👷 인건비", "⛽ 유류비", "🍚 식대", "🚗 기타"]
            )
            
            # 현장 선택
            site = st.text_input("현장명", placeholder="예: 강남 오피스텔")
            
            if st.button("💾 저장하기", type="primary"):
                # LLM으로 영수증 텍스트 구조화
                with st.spinner("저장 중..."):
                    try:
                        # 영수증 텍스트를 5W1H로 변환
                        receipt_input = f"{site} {category} {extracted_text}"
                        raw = analyze_text(receipt_input)
                        normalized = normalize_data(raw)
                        status, msg = save_record(normalized)
                        
                        if 200 <= status < 300:
                            st.success(f"✅ '{category}' 영수증이 저장되었습니다!")
                        else:
                            st.error("저장 실패")
                    except Exception as e:
                        st.error(f"처리 실패: {e}")

# Tab 3: 현황 대시보드
with tab3:
    st.subheader("이번 달 현황")
    
    # 메트릭 카드
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="총 계약금액",
            value="8,500만원",
            delta="신규 500만원"
        )
    
    with col2:
        st.metric(
            label="받은 돈",
            value="5,250만원",
            delta="이번주 +500만원"
        )
    
    with col3:
        st.metric(
            label="받을 돈",
            value="3,250만원",
            delta="38.2%"
        )
    
    with col4:
        st.metric(
            label="지출",
            value="2,130만원",
            delta="-230만원"
        )
    
    st.divider()
    
    # 미수금 알림
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📌 이번 주 받을 돈")
        
        # 미수금 데이터
        receivables_df = pd.DataFrame([
            {"현장": "강남 오피스텔", "구분": "중도금", "금액": 5000000, "예정일": "2025-01-25", "D-Day": 2},
            {"현장": "북구청 방수", "구분": "잔금", "금액": 10000000, "예정일": "2025-01-28", "D-Day": 5},
            {"현장": "서초 아파트", "구분": "계약금", "금액": 3000000, "예정일": "2025-01-23", "D-Day": 0},
            {"현장": "판교 빌라", "구분": "중도금", "금액": 4500000, "예정일": "2025-01-30", "D-Day": 7},
        ])
        
        for _, row in receivables_df.iterrows():
            col_a, col_b, col_c, col_d, col_e = st.columns([3, 2, 2, 1, 1])
            
            with col_a:
                st.write(f"**{row['현장']}**")
            with col_b:
                st.write(f"{row['구분']}")
            with col_c:
                st.write(f"{row['금액']:,}원")
            with col_d:
                if row['D-Day'] == 0:
                    st.write("🔴 오늘")
                elif row['D-Day'] <= 2:
                    st.write(f"🟡 D-{row['D-Day']}")
                else:
                    st.write(f"D-{row['D-Day']}")
            with col_e:
                if st.button("📞", key=f"call_{row['현장']}"):
                    st.info(f"{row['현장']} 담당자 연결")
    
    with col2:
        # 수금률 파이 차트
        fig = go.Figure(data=[go.Pie(
            labels=['받은 돈', '받을 돈'],
            values=[5250, 3250],
            hole=.3,
            marker_colors=['#4CAF50', '#FFC107']
        )])
        
        fig.update_layout(
            title="수금 현황",
            height=300,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)

# Tab 4: 잔금 현황표
with tab4:
    st.subheader("💳 현장별 잔금 현황")
    
    # 샘플 데이터
    payment_data = pd.DataFrame([
        {"현장명": "강남 오피스텔", "계약금액": 15000000, "받은금액": 10000000, "잔금": 5000000, "진행률": 67},
        {"현장명": "북구청 방수", "계약금액": 30000000, "받은금액": 20000000, "잔금": 10000000, "진행률": 67},
        {"현장명": "서초 아파트", "계약금액": 8000000, "받은금액": 5000000, "잔금": 3000000, "진행률": 63},
        {"현장명": "판교 빌라", "계약금액": 12000000, "받은금액": 7500000, "잔금": 4500000, "진행률": 63},
        {"현장명": "분당 주택", "계약금액": 20000000, "받은금액": 20000000, "잔금": 0, "진행률": 100},
    ])
    
    # 차트 표시
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 막대 차트
        fig = create_payment_chart(payment_data)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # 요약 정보
        st.metric("총 계약금액", f"{payment_data['계약금액'].sum():,}원")
        st.metric("총 받은금액", f"{payment_data['받은금액'].sum():,}원")
        st.metric("총 잔금", f"{payment_data['잔금'].sum():,}원")
        
        avg_progress = payment_data['진행률'].mean()
        st.metric("평균 수금률", f"{avg_progress:.1f}%")
    
    # 상세 테이블
    st.divider()
    st.markdown("### 📋 상세 내역")
    
    # 테이블 스타일링
    styled_df = payment_data.copy()
    styled_df['계약금액'] = styled_df['계약금액'].apply(lambda x: f"{x:,}원")
    styled_df['받은금액'] = styled_df['받은금액'].apply(lambda x: f"{x:,}원")
    styled_df['잔금'] = styled_df['잔금'].apply(lambda x: f"{x:,}원")
    styled_df['진행률'] = styled_df['진행률'].apply(lambda x: f"{x}%")
    
    # 편집 가능한 테이블
    edited_df = st.data_editor(
        styled_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "현장명": st.column_config.TextColumn("현장명", width="medium"),
            "계약금액": st.column_config.TextColumn("계약금액", width="small"),
            "받은금액": st.column_config.TextColumn("받은금액", width="small"),
            "잔금": st.column_config.TextColumn("잔금", width="small"),
            "진행률": st.column_config.ProgressColumn(
                "진행률",
                help="수금 진행률",
                format="%d%%",
                min_value=0,
                max_value=100,
            ),
        }
    )
    
    # 엑셀 다운로드 버튼
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("📊 엑셀 다운로드", use_container_width=True):
            # 엑셀 파일 생성 (실제로는 pandas to_excel 사용)
            st.success("수금현황.xlsx 다운로드 완료!")
    
    with col2:
        if st.button("📨 세무사 전송", use_container_width=True):
            st.success("세무사님께 자료 전송 완료!")

# 하단 메뉴
st.divider()
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📞 고객센터", use_container_width=True):
        st.info("☎️ 1588-0000")

with col2:
    if st.button("📚 사용법", use_container_width=True):
        st.info("동영상 가이드 준비중")

with col3:
    if st.button("👥 내 정보", use_container_width=True):
        st.info("사업자 정보 관리")

with col4:
    if st.button("⚙️ 설정", use_container_width=True):
        st.info("알림 설정")
