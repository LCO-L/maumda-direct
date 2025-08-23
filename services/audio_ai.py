# services/audio_ai.py
import streamlit as st
import io
import tempfile
import os

# OpenAI 클라이언트
try:
    from openai import OpenAI
    import streamlit as st
    
    # API 키 가져오기
    api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    client = OpenAI(api_key=api_key) if api_key else None
except:
    client = None

def transcribe_audio(audio_bytes, filename="audio.wav"):
    """
    OpenAI Whisper API로 음성을 텍스트로 변환
    
    Args:
        audio_bytes: 오디오 파일 바이트
        filename: 파일명 (확장자 포함)
    
    Returns:
        str: 변환된 텍스트
    """
    if not client:
        return "❌ OpenAI API 키가 설정되지 않았습니다."
    
    try:
        # 임시 파일로 저장 (Whisper API는 파일 객체 필요)
        with tempfile.NamedTemporaryFile(suffix=f".{filename.split('.')[-1]}", delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file_path = tmp_file.name
        
        # Whisper API 호출
        with open(tmp_file_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ko",  # 한국어 지정
                response_format="text"
            )
        
        # 임시 파일 삭제
        os.unlink(tmp_file_path)
        
        return transcript
        
    except Exception as e:
        return f"❌ 음성 인식 실패: {str(e)}"

def create_audio_recorder():
    """
    Streamlit 오디오 녹음 컴포넌트
    audio-recorder-streamlit 패키지 필요
    """
    try:
        from audio_recorder_streamlit import audio_recorder
        
        # 녹음 버튼
        audio_bytes = audio_recorder(
            text="🎤 녹음 시작/중지",
            recording_color="#e74c3c",
            neutral_color="#4CAF50",
            icon_size="2x",
            pause_threshold=3.0,  # 3초 침묵 시 자동 중지
        )
        
        return audio_bytes
    except ImportError:
        # 패키지가 없으면 파일 업로드로 대체
        return None

def audio_input_section():
    """
    음성 입력 섹션 (녹음 또는 파일 업로드)
    """
    st.markdown("### 🎤 AI 음성 인식")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 방법 1: 음성 파일 업로드")
        audio_file = st.file_uploader(
            "음성 파일 선택",
            type=['wav', 'mp3', 'm4a', 'ogg', 'webm'],
            help="최대 25MB, 한국어 음성"
        )
        
        if audio_file:
            # 오디오 재생
            st.audio(audio_file, format=f'audio/{audio_file.type.split("/")[-1]}')
            
            if st.button("🔍 AI 음성 인식", key="transcribe_upload"):
                with st.spinner("AI가 음성을 인식하는 중... (5-10초)"):
                    # 파일 읽기
                    audio_bytes = audio_file.read()
                    
                    # Whisper API 호출
                    text = transcribe_audio(audio_bytes, audio_file.name)
                    
                    if text and not text.startswith("❌"):
                        st.success("✅ 인식 완료!")
                        st.text_area("인식된 텍스트:", text, height=100)
                        
                        # 세션에 저장
                        st.session_state['recognized_text'] = text
                        
                        # 복사 버튼
                        st.code(text, language=None)
                        st.info("위 텍스트를 복사해서 아래 입력란에 붙여넣으세요")
                    else:
                        st.error(text)
    
    with col2:
        st.markdown("#### 방법 2: 직접 녹음")
        
        # audio-recorder 패키지 시도
        audio_bytes = create_audio_recorder()
        
        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
            
            if st.button("🔍 AI 음성 인식", key="transcribe_record"):
                with st.spinner("AI가 음성을 인식하는 중..."):
                    text = transcribe_audio(audio_bytes, "recording.wav")
                    
                    if text and not text.startswith("❌"):
                        st.success("✅ 인식 완료!")
                        st.text_area("인식된 텍스트:", text, height=100)
                        st.session_state['recognized_text'] = text
                    else:
                        st.error(text)
        else:
            st.info("""
                🎙️ 녹음 방법:
                1. 스마트폰으로 녹음
                2. 파일로 저장
                3. 왼쪽에서 업로드
                
                또는 Windows 음성 녹음기 사용
            """)
    
    # 인식된 텍스트가 있으면 표시
    if 'recognized_text' in st.session_state:
        st.divider()
        st.markdown("#### 📝 인식된 내용")
        st.info(st.session_state['recognized_text'])
        
        if st.button("⬇️ 아래 입력란에 자동 입력"):
            return st.session_state['recognized_text']
    
    return None

# 간단한 버전 (파일 업로드만)
def simple_audio_upload():
    """
    간단한 음성 파일 업로드 및 인식
    """
    with st.expander("🎤 음성 파일로 입력 (AI 인식)"):
        audio_file = st.file_uploader(
            "음성 파일 업로드",
            type=['wav', 'mp3', 'm4a', 'ogg'],
            help="녹음한 음성 파일을 업로드하세요"
        )
        
        if audio_file:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.audio(audio_file)
            
            with col2:
                if st.button("🤖 인식", type="primary"):
                    with st.spinner("인식 중..."):
                        audio_bytes = audio_file.read()
                        text = transcribe_audio(audio_bytes, audio_file.name)
                        
                        if text and not text.startswith("❌"):
                            return text
                        else:
                            st.error(text)
    
    return None
