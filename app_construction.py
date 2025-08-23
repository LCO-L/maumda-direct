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

# Tab 1: 미수금 입력
with tab1:
    st.subheader("받을 돈 기록하기")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 음성 입력 섹션
        st.markdown("### 🎤 음성으로 입력하기")
        get_voice_input()  # 음성 입력 컴포넌트
        
        # 텍스트 입력
        st.markdown("### ✍️ 직접 입력하기")
        user_input = st.text_area(
            "그냥 편하게 말씀하세요",
            placeholder="""예시:
- 강남 아파트 타일공사 500만원 다음주 받기로 했어
- 북구청 방수 작업 끝나면 1000만원 잔금""",
            height=100,
            key="voice_text_input"
        )
        <div>
            <button onclick="startRecognition()" style="
                background-color: #FF5722;
                color: white;
                border: none;
                padding: 12px 24px;
                font-size: 16px;
                border-radius: 8px;
                cursor: pointer;
                margin: 10px 0;
            ">
                🎤 말하기 (클릭 후 말씀하세요)
            </button>
            <div id="result" style="margin-top: 10px; padding: 10px; background: #f0f0f0; border-radius: 5px; min-height: 50px;"></div>
        </div>
        
        <script>
        function startRecognition() {
            if ('webkitSpeechRecognition' in window) {
                const recognition = new webkitSpeechRecognition();
                recognition.lang = 'ko-KR';
                recognition.continuous = false;
                recognition.interimResults = true;
                
                recognition.onstart = function() {
                    document.getElementById('result').innerHTML = '🔴 듣고 있습니다...';
                };
                
                recognition.onresult = function(event) {
                    let finalTranscript = '';
                    let interimTranscript = '';
                    
                    for (let i = event.resultIndex; i < event.results.length; ++i) {
                        if (event.results[i].isFinal) {
                            finalTranscript += event.results[i][0].transcript;
                        } else {
                            interimTranscript += event.results[i][0].transcript;
                        }
                    }
                    
                    document.getElementById('result').innerHTML = finalTranscript || interimTranscript;
                    
                    if (finalTranscript) {
                        // Streamlit으로 텍스트 전달
                        window.parent.postMessage({
                            type: 'voice_input',
                            text: finalTranscript
                        }, '*');
                    }
                };
                
                recognition.onerror = function(event) {
                    document.getElementById('result').innerHTML = '❌ 에러: ' + event.error;
                };
                
                recognition.start();
            } else {
                alert('음성 인식이 지원되지 않는 브라우저입니다. Chrome을 사용해주세요.');
            }
        }
        </script>
        """
        
        components.html(speech_html, height=150)
        
        # 텍스트 입력
        st.markdown("### ✍️ 직접 입력하기")
        user_input = st.text_area(
            "그냥 편하게 말씀하세요",
            placeholder="""예시:
• 강남 아파트 타일공사 500만원 다음주 받기로 했어
• 북구청 방수 작업 끝나면 1000만원 잔금
• 김사장한테 인테리어 대금 300만원 15일에 받아야 돼""",
            height=100,
            value=st.session_state.voice_input
        )
    
    with col2:
        st.markdown("### 빠른 입력")
        
        # 템플릿 버튼들
        if st.button("📝 계약금", use_container_width=True):
            st.session_state.voice_input = "현장이름 계약금 금액 오늘 받음"
            st.rerun()
        
        if st.button("💵 중도금", use_container_width=True):
            st.session_state.voice_input = "현장이름 중도금 금액 날짜 예정"
            st.rerun()
        
        if st.button("💰 잔금", use_container_width=True):
            st.session_state.voice_input = "현장이름 잔금 금액 완료시 받기"
            st.rerun()
    
    # 분석 버튼
    if st.button("📝 기록하기", type="primary"):
        if not user_input.strip():
            st.warning("내용을 입력해주세요.")
        else:
            with st.spinner("정리 중..."):
                try:
                    raw = analyze_text(user_input)
                    
                    # 디버깅: 원본 분석 결과 확인
                    print(f"LLM 분석 결과: {raw}")
                    
                    normalized = normalize_data(raw)
                    
                    # 디버깅: 정규화 후 결과 확인
                    print(f"정규화 후: {normalized}")
                    
                    # 금액 추출 - what 필드에서 금액 부분만 추출
                    what_text = normalized.get('what', '')
                    amount = None
                    
                    # 우선 정규화된 what에서 금액 찾기
                    if what_text:
                        amount = extract_amount(what_text)
                    
                    # 못 찾았으면 원본 what_display에서 찾기
                    if not amount and normalized.get('what_display'):
                        amount = extract_amount(normalized.get('what_display'))
                        # 원본에서 찾은 경우 변환 필요
                        if amount and '만' in normalized.get('what_display', ''):
                            # 다시 정규화
                            import re
                            num_match = re.search(r'(\d+)\s*만', normalized.get('what_display', ''))
                            if num_match:
                                num = int(num_match.group(1))
                                amount = f"{num * 10000:,}원"
                    
                    # 최종 금액 설정
                    if amount and amount != "000,000원":
                        normalized['display_amount'] = amount
                    else:
                        # 기본값
                        normalized['display_amount'] = what_text if what_text else '금액 미입력'
                    
                    # 디버깅: 최종 금액 확인
                    print(f"표시할 금액: {normalized.get('display_amount')}")
                    
                    st.session_state.analyzed_data = normalized
                    st.session_state.saved = False
                    
                except Exception as e:
                    st.error(f"처리 실패: {e}")
    
    # 분석 결과 표시
    if st.session_state.analyzed_data and not st.session_state.saved:
        st.divider()
        data = st.session_state.analyzed_data
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("현장/발주처", data.get('who', '-'))
        
        with col2:
            amount = data.get('display_amount', data.get('what', '-'))
            # 금액이 비어있거나 잘못된 경우 처리
            if not amount or amount == '-' or amount == '000,000원':
                # what 필드에서 다시 추출 시도
                if data.get('what'):
                    amount = extract_amount(data.get('what'))
                    if not amount:
                        amount = data.get('what')
                else:
                    amount = '금액 미입력'
            st.metric("금액", amount)
        
        with col3:
            when = data.get('when_display', data.get('when', '-'))
            st.metric("예정일", when)
        
        if st.button("✅ 맞아요, 저장", type="secondary"):
            with st.spinner("저장 중..."):
                status, msg = save_record(data)
                
            if 200 <= status < 300:
                st.success("✅ 저장 완료!")
                st.balloons()
                st.session_state.saved = True
            else:
                st.error("저장 실패. 다시 시도해주세요.")

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
