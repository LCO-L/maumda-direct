import streamlit as st
import streamlit.components.v1 as components
from services.llm import analyze_text, normalize_data
from services.notion import save_record
from services.voice_input import get_voice_input
from services.auth import check_password, validate_api_usage, log_activity, check_api_limit
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
from PIL import Image
import io

# 페이지 설정
st.set_page_config(
    page_title="마음다이렉트 💼",
    page_icon="🗏",
    layout="wide"
)

# ============================================
# 🔐 보안: 로그인 체크 (가장 먼저!)
# ============================================
if not check_password():
    st.stop()  # 로그인 안 하면 여기서 멈춤

# ============================================
# 메인 앱 시작 (로그인 성공 후)
# ============================================

# API 사용량 표시
usage, limits = validate_api_usage()
with st.sidebar:
    st.markdown("### 📊 오늘 사용량")
    st.progress(usage['gpt_calls'] / limits['gpt_calls'] if limits['gpt_calls'] > 0 else 0)
    st.caption(f"AI 분석: {usage['gpt_calls']}/{limits['gpt_calls']}")
    st.progress(usage['whisper_calls'] / limits['whisper_calls'] if limits['whisper_calls'] > 0 else 0)
    st.caption(f"음성인식: {usage['whisper_calls']}/{limits['whisper_calls']}")
    st.progress(usage['notion_saves'] / limits['notion_saves'] if limits['notion_saves'] > 0 else 0)
    st.caption(f"저장: {usage['notion_saves']}/{limits['notion_saves']}")
        
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
        received_pct = (row['받은금액'] / row['계약금액']) * 100 if row['계약금액'] > 0 else 0
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
st.title("🗏 마음다이렉트")
st.caption("건설현장 사장님의 든든한 비즈니스 파트너")

# 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["💰 미수금", "📸 영수증", "📊 현황", "💳 잔금표"])

with tab1:
    st.subheader("받을 돈 기록하기")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 음성 입력 섹션
        st.markdown("### 🎤 음성으로 입력하기")
        
        # 사용 안내
        with st.expander("💡 음성 입력 사용법", expanded=False):
            st.info("""
            **🎙️ 녹음 방법:**
            1. 아래 **🔴 녹음 시작** 버튼을 클릭하세요
            2. 편하게 말씀하세요 (예: "강남 아파트 타일공사 500만원 다음주")
            3. 말이 끝나면 **⏹️ 녹음 중지** 버튼을 클릭하세요
            4. **🤖 AI 인식** 버튼으로 텍스트 변환
            
            **💬 말하기 예시:**
            - "북구청 방수 작업 끝나면 천만원 잔금"
            - "김사장 인테리어 삼백만원 내일 계약금"
            - "서초 빌라 미장 이백만원 다음주 수요일"
            """)
        
        # 세션 상태 초기화
        if 'is_recording' not in st.session_state:
            st.session_state.is_recording = False
        if 'audio_data' not in st.session_state:
            st.session_state.audio_data = None
        
        # 음성 녹음 시도
        try:
            from audio_recorder_streamlit import audio_recorder
            
            # 녹음 버튼 분리
            col_rec1, col_rec2, col_rec3 = st.columns([1, 1, 2])
            
            with col_rec1:
                if not st.session_state.is_recording:
                    if st.button("🔴 녹음 시작", use_container_width=True, key="start_recording_btn", type="secondary"):
                        st.session_state.is_recording = True
                        st.rerun()
            
            with col_rec2:
                if st.session_state.is_recording:
                    if st.button("⏹️ 녹음 중지", use_container_width=True, key="stop_recording_btn", type="secondary"):
                        st.session_state.is_recording = False
                        st.rerun()
            
            with col_rec3:
                if st.session_state.is_recording:
                    st.error("🔴 **녹음 중... 말씀해 주세요!**")
                else:
                    st.success("📍 준비됨")
            
            # 실제 녹음 컴포넌트 (숨김)
            if st.session_state.is_recording:
                with st.container():
                    audio_bytes = audio_recorder(
                        text="녹음 중...",
                        recording_color="#FF0000",
                        neutral_color="#4CAF50",
                        icon_name="microphone",
                        icon_size="2x",
                        pause_threshold=30.0,  # 30초로 늘림
                        key="audio_recorder_widget"
                    )
                    
                    if audio_bytes:
                        st.session_state.audio_data = audio_bytes
                        st.session_state.is_recording = False
                        
                        # 🔥 자동으로 AI 인식 시작
                        with st.spinner("🎧 음성을 텍스트로 변환 중... (5~10초)"):
                            try:
                                from openai import OpenAI
                                import tempfile
                                import os
                                import time
                                
                                # API 제한 체크
                                if check_api_limit("whisper_calls"):
                                    # OpenAI 클라이언트
                                    api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
                                    client = OpenAI(api_key=api_key)
                                    
                                    # 임시 파일 저장
                                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                                        tmp.write(audio_bytes)
                                        tmp_path = tmp.name
                                    
                                    # Whisper API 호출
                                    with open(tmp_path, 'rb') as audio_file:
                                        transcript = client.audio.transcriptions.create(
                                            model="whisper-1",
                                            file=audio_file,
                                            language="ko"
                                        )
                                    
                                    # 임시 파일 삭제
                                    os.unlink(tmp_path)
                                    
                                    # 결과 저장
                                    st.session_state.recognized_text = transcript.text
                                    st.session_state.voice_text_input = transcript.text
                                    
                                    # 인식 결과 표시
                                    st.success(f"✅ 인식 완료!")
                                    st.info(f"📝 **인식된 텍스트:** {transcript.text}")
                                    
                                    # 활동 로깅
                                    log_activity("voice_recognition", {"success": True, "text_length": len(transcript.text)})
                                    
                                    # 오디오 데이터 삭제
                                    st.session_state.audio_data = None
                                    
                                    # 1초 후 새로고침으로 텍스트 반영
                                    time.sleep(1)
                                    st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ 인식 실패: {e}")
                                log_activity("voice_recognition", {"success": False, "error": str(e)})
                                # 실패시에도 오디오는 보관
            
            # 녹음된 오디오가 있지만 인식 실패한 경우 수동 버튼 제공
            if st.session_state.audio_data and not st.session_state.is_recording:
                st.divider()
                st.warning("⚠️ 자동 인식이 실패했습니다. 아래 버튼을 눌러 다시 시도하세요.")
                st.audio(st.session_state.audio_data, format="audio/wav")
                
                col_ai1, col_ai2 = st.columns([1, 1])
                
                with col_ai1:
                    if st.button("🤖 **다시 인식**", type="primary", use_container_width=True, key="retry_recognize_btn"):
                        with st.spinner("🎧 음성을 텍스트로 변환 중..."):
                            try:
                                from openai import OpenAI
                                import tempfile
                                import os
                                import time
                                
                                api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
                                client = OpenAI(api_key=api_key)
                                
                                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                                    tmp.write(st.session_state.audio_data)
                                    tmp_path = tmp.name
                                
                                with open(tmp_path, 'rb') as audio_file:
                                    transcript = client.audio.transcriptions.create(
                                        model="whisper-1",
                                        file=audio_file,
                                        language="ko"
                                    )
                                
                                os.unlink(tmp_path)
                                
                                st.session_state.recognized_text = transcript.text
                                st.session_state.voice_text_input = transcript.text
                                st.success(f"✅ 인식 완료: {transcript.text}")
                                st.session_state.audio_data = None
                                time.sleep(1)
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"인식 실패: {e}")
                
                with col_ai2:
                    if st.button("🔄 다시 녹음", use_container_width=True, key="re_record_btn"):
                        st.session_state.audio_data = None
                        st.session_state.is_recording = False
                        st.rerun()
        
        except ImportError:
            # 대체 음성 입력 방법 - 파일 업로드
            st.warning("🎤 실시간 녹음 기능을 사용할 수 없습니다. 파일 업로드를 사용하세요.")
            
            audio_file = st.file_uploader(
                "녹음된 음성 파일을 선택하세요",
                type=['wav', 'mp3', 'm4a', 'webm', 'ogg'],
                help="스마트폰이나 컴퓨터로 녹음한 파일을 업로드하세요",
                key="audio_file_uploader"
            )
            
            if audio_file:
                st.audio(audio_file)
                
                # 파일 업로드시 자동 인식
                with st.spinner("🎧 음성 인식 중..."):
                    try:
                        from openai import OpenAI
                        import tempfile
                        import time
                        
                        api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
                        client = OpenAI(api_key=api_key)
                        
                        # 파일을 바이트로 읽기
                        audio_bytes = audio_file.read()
                        
                        # 임시 파일로 저장
                        with tempfile.NamedTemporaryFile(suffix=f".{audio_file.name.split('.')[-1]}", delete=False) as tmp:
                            tmp.write(audio_bytes)
                            tmp_path = tmp.name
                        
                        # Whisper API
                        with open(tmp_path, 'rb') as f:
                            transcript = client.audio.transcriptions.create(
                                model="whisper-1",
                                file=f,
                                language="ko"
                            )
                        
                        os.unlink(tmp_path)
                        
                        # 자동으로 텍스트 입력란에 추가
                        st.session_state.recognized_text = transcript.text
                        st.session_state.voice_text_input = transcript.text
                        st.success(f"✅ 인식 완료!")
                        st.info(f"📝 **인식된 텍스트:** {transcript.text}")
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ 인식 실패: {e}")
                        st.info("음성 파일을 다시 업로드해주세요.")
        
        # time 모듈 import 추가 (필요한 경우)
        import time
        
        # 대체 방법: audio_recorder_streamlit 패키지 사용
        try:
            from audio_recorder_streamlit import audio_recorder
            
            st.markdown("#### 또는 간편 녹음")
            
            # 녹음 버튼 분리
            col_rec1, col_rec2, col_rec3 = st.columns([1, 1, 2])
            
            with col_rec1:
                if not st.session_state.is_recording:
                    if st.button("🔴 녹음 시작", use_container_width=True, key="start_rec"):
                        st.session_state.is_recording = True
                        st.rerun()
            
            with col_rec2:
                if st.session_state.is_recording:
                    if st.button("⏹️ 녹음 중지", use_container_width=True, key="stop_rec"):
                        st.session_state.is_recording = False
                        st.rerun()
            
            with col_rec3:
                if st.session_state.is_recording:
                    st.error("🔴 **녹음 중... 말씀해 주세요!**")
                else:
                    st.success("📍 준비됨")
            
            # 실제 녹음 컴포넌트 (숨김)
            if st.session_state.is_recording:
                audio_bytes = audio_recorder(
                    text="",
                    recording_color="#FF0000",
                    neutral_color="#4CAF50",
                    icon_name="microphone",
                    icon_size="1x",
                    pause_threshold=30.0,  # 30초로 늘림
                    key="hidden_recorder"
                )
                
                if audio_bytes:
                    st.session_state.audio_data = audio_bytes
                    st.session_state.is_recording = False
                    st.rerun()
            
            # 녹음된 오디오 처리
            if st.session_state.audio_data:
                st.success("✅ 녹음 완료!")
                st.audio(st.session_state.audio_data, format="audio/wav")
                
                col_ai1, col_ai2, col_ai3 = st.columns([2, 2, 1])
                
                with col_ai1:
                    if st.button("🤖 AI 인식", type="primary", use_container_width=True):
                        # 🔐 API 제한 체크
                        if not check_api_limit("whisper_calls"):
                            st.stop()
                        
                        with st.spinner("🎧 음성을 텍스트로 변환 중... (5~10초)"):
                            try:
                                from openai import OpenAI
                                import tempfile
                                import os
                                
                                # OpenAI 클라이언트
                                api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
                                client = OpenAI(api_key=api_key)
                                
                                # 임시 파일 저장
                                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                                    tmp.write(st.session_state.audio_data)
                                    tmp_path = tmp.name
                                
                                # Progress bar 추가
                                progress_bar = st.progress(0)
                                progress_bar.progress(30, text="음성 파일 처리 중...")
                                
                                # Whisper API 호출
                                with open(tmp_path, 'rb') as audio_file:
                                    progress_bar.progress(60, text="AI 분석 중...")
                                    transcript = client.audio.transcriptions.create(
                                        model="whisper-1",
                                        file=audio_file,
                                        language="ko"
                                    )
                                
                                progress_bar.progress(100, text="완료!")
                                
                                # 임시 파일 삭제
                                os.unlink(tmp_path)
                                
                                # 결과 저장
                                st.session_state.recognized_text = transcript.text
                                st.session_state.voice_text_input = transcript.text
                                st.success(f"✅ 인식 완료: \"{transcript.text}\"")
                                
                                # Progress bar 제거
                                progress_bar.empty()
                                
                                # 🔐 활동 로깅
                                log_activity("voice_recognition", {"success": True, "text_length": len(transcript.text)})
                                
                                # 페이지 새로고침으로 텍스트 반영
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ 인식 실패: {e}")
                                log_activity("voice_recognition", {"success": False, "error": str(e)})
                
                with col_ai2:
                    if st.button("🔄 다시 녹음", use_container_width=True):
                        st.session_state.audio_data = None
                        st.session_state.is_recording = False
                        st.rerun()
        
        except ImportError:
            # 대체 음성 입력 방법
            st.divider()
            st.markdown("#### 📁 음성 파일 업로드")
            
            audio_file = st.file_uploader(
                "녹음된 음성 파일을 선택하세요",
                type=['wav', 'mp3', 'm4a', 'webm'],
                help="스마트폰이나 컴퓨터로 녹음한 파일을 업로드하세요"
            )
            
            if audio_file:
                st.audio(audio_file)
                
                if st.button("🤖 AI 음성 인식", type="primary"):
                    with st.spinner("🎧 음성 인식 중..."):
                        try:
                            from openai import OpenAI
                            import tempfile
                            
                            api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
                            client = OpenAI(api_key=api_key)
                            
                            # 파일 저장
                            with tempfile.NamedTemporaryFile(suffix=f".{audio_file.name.split('.')[-1]}", delete=False) as tmp:
                                tmp.write(audio_file.read())
                                tmp_path = tmp.name
                            
                            # Whisper API
                            with open(tmp_path, 'rb') as f:
                                transcript = client.audio.transcriptions.create(
                                    model="whisper-1",
                                    file=f,
                                    language="ko"
                                )
                            
                            os.unlink(tmp_path)
                            
                            st.session_state.recognized_text = transcript.text
                            st.session_state.voice_text_input = transcript.text
                            st.success(f"✅ 인식 완료: \"{transcript.text}\"")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"인식 실패: {e}")
        
        # 텍스트 입력
        st.markdown("### ✏️ 직접 입력하기")
        
        # 인식된 텍스트가 있으면 자동 입력
        default_text = ""
        if 'recognized_text' in st.session_state and st.session_state.recognized_text:
            default_text = st.session_state.recognized_text
            st.success(f"🎤 인식된 내용이 아래에 자동 입력되었습니다!")
            # 인식 후 세션에서 제거하여 중복 방지
            del st.session_state.recognized_text
        
        # voice_text_input 세션 값 확인
        if 'voice_text_input' in st.session_state and st.session_state.voice_text_input:
            default_text = st.session_state.voice_text_input
        
        user_input = st.text_area(
            "그냥 편하게 말씀하세요",
            value=default_text,
            placeholder="""예시:
- 강남 아파트 타일공사 500만원 다음주 받기로 했어
- 북구청 방수 작업 끝나면 1000만원 잔금""",
            height=120,
            key="main_text_input"  # key 변경
        )
    
    with col2:
        # 빠른 입력 템플릿
        st.markdown("### 빠른 입력")
        if st.button("📝 계약금", use_container_width=True):
            st.session_state.voice_text_input = "현장명 계약금 금액 오늘 받음"
            st.rerun()
        
        if st.button("💵 중도금", use_container_width=True):
            st.session_state.voice_text_input = "현장명 중도금 금액 날짜 예정"
            st.rerun()
        
        if st.button("💰 잔금", use_container_width=True):
            st.session_state.voice_text_input = "현장명 잔금 금액 완료시 받기"
            st.rerun()
    
    # 분석 버튼
    if st.button("🔍 기록하기", type="primary"):
        if not user_input or not user_input.strip():
            st.warning("내용을 입력해주세요.")
        else:
            # 🔐 API 제한 체크
            if not check_api_limit("gpt_calls"):
                st.stop()
            
            with st.spinner("AI가 분석 중..."):
                try:
                    # 분석 및 정규화
                    raw = analyze_text(user_input)
                    normalized = normalize_data(raw)
                    
                    # 세션에 저장
                    st.session_state.analyzed_data = normalized
                    st.session_state.saved = False
                    
                    # 🔐 활동 로깅
                    log_activity("text_analysis", {"success": True, "text_length": len(user_input)})
                    
                except Exception as e:
                    st.error(f"처리 실패: {e}")
                    log_activity("text_analysis", {"success": False, "error": str(e)})

    # 분석 결과 표시
    if st.session_state.analyzed_data:
        st.divider()
        st.subheader("📋 AI 분석 결과")
        
        data = st.session_state.analyzed_data
        
        if data:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # 분석 결과 카드
                st.markdown("### 📋 내용 정리")
                
                with st.container():
                    st.markdown(f"""
                    - **🏗️ 현장:** {data.get('who', '-')}
                    - **📋 내용:** {data.get('what', '-')}  
                    - **💰 금액:** {data.get('how', '-')}
                    - **📅 언제:** {data.get('when', '-')}
                    - **📍 위치:** {data.get('where', '-')}
                    - **❓ 유형:** {data.get('why', '-')}
                    """)
                
                # 수정 가능한 필드들
                with st.expander("✏️ 수정하기"):
                    data['who'] = st.text_input("현장명", data.get('who', ''))
                    data['what'] = st.text_input("작업 내용", data.get('what', ''))
                    data['when'] = st.text_input("날짜", data.get('when', ''))
                    data['where'] = st.text_input("위치", data.get('where', ''))
                    data['why'] = st.text_input("유형", data.get('why', ''))
                    data['how'] = st.text_input("금액", data.get('how', ''))
            
            with col2:
                st.markdown("### 💾 저장")
                
                if not st.session_state.saved:
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        if st.button("💾 확정 저장", type="primary", use_container_width=True):
                            # 🔐 API 제한 체크
                            if not check_api_limit("notion_saves"):
                                st.stop()
                                
                            with st.spinner("저장 중..."):
                                try:
                                    status, msg = save_record(data)
                                    if 200 <= status < 300:
                                        st.success("✅ 저장 완료!")
                                        st.session_state.saved = True
                                        
                                        # 🔐 활동 로깅
                                        log_activity("notion_save", {"success": True, "site": data.get('who')})
                                        
                                        # 세션 정리
                                        if 'analyzed_data' in st.session_state:
                                            del st.session_state.analyzed_data
                                        if 'recognized_text' in st.session_state:
                                            del st.session_state.recognized_text
                                    else:
                                        st.error(f"❌ 저장 실패: {msg}")
                                        log_activity("notion_save", {"success": False})
                                except Exception as e:
                                    st.error(f"저장 실패: {e}")
                                    log_activity("notion_save", {"success": False, "error": str(e)})
                    
                    with col2:
                        if st.button("🗑️ 취소", use_container_width=True):
                            st.session_state.analyzed_data = None
                            st.rerun()
                else:
                    st.success("✅ 저장됨")
                    if st.button("🔄 새로 기록", use_container_width=True):
                        st.session_state.analyzed_data = None
                        st.session_state.saved = False
                        if 'recognized_text' in st.session_state:
                            del st.session_state.recognized_text
                        st.rerun()

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
            st.markdown("### 📋 인식 결과")
            
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
                # 🔐 API 제한 체크
                if not check_api_limit("notion_saves"):
                    st.stop()
                    
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
                            # 🔐 활동 로깅
                            log_activity("receipt_save", {"success": True, "category": category})
                        else:
                            st.error("저장 실패")
                            log_activity("receipt_save", {"success": False})
                    except Exception as e:
                        st.error(f"처리 실패: {e}")
                        log_activity("receipt_save", {"success": False, "error": str(e)})

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

# ============================================
# 하단 상태바
# ============================================
st.divider()

# 한 줄로 모든 정보 표시
footer_cols = st.columns([4, 1, 1, 1])

with footer_cols[0]:
    # 세션 정보
    if st.session_state.get('authenticated'):
        from datetime import datetime, timedelta
        
        # 사용자 및 시간 정보
        user = st.session_state.get('username', 'guest')
        
        # 남은 시간 계산
        remaining_minutes = 30
        if st.session_state.get('login_time'):
            elapsed = (datetime.now() - st.session_state.login_time).seconds // 60
            remaining_minutes = max(0, 30 - elapsed)
        
        # 사용량 정보
        usage, limits = validate_api_usage()
        
        st.caption(
            f"👤 {user} | "
            f"⏱️ {remaining_minutes}분 | "
            f"📊 AI {usage['gpt_calls']}/{limits['gpt_calls']} | "
            f"🎤 음성 {usage['whisper_calls']}/{limits['whisper_calls']}"
        )

with footer_cols[1]:
    st.button("📞 지원", use_container_width=True)

with footer_cols[2]:
    st.button("⚙️ 설정", use_container_width=True)

with footer_cols[3]:
    if st.button("🚪 로그아웃", use_container_width=True, key="logout_btn_main"):
        st.session_state.clear()
        st.rerun()
