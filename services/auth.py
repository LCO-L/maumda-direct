# services/auth.py
import streamlit as st
import hashlib
import hmac
import time
from datetime import datetime, timedelta

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 비밀번호를 세션에서 삭제
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 첫 실행이거나 비밀번호가 아직 검증되지 않음
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # 비밀번호가 틀림
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # 비밀번호가 맞음
        return True

if check_password():
    st.write("🎈 여기에 메인 앱 내용을 작성하세요!")
    
    # 이미 로그인되어 있는지 확인
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if "login_time" not in st.session_state:
        st.session_state.login_time = None
    
    # 세션 타임아웃 (30분)
    if st.session_state.authenticated and st.session_state.login_time:
        elapsed = datetime.now() - st.session_state.login_time
        if elapsed > timedelta(minutes=30):
            st.session_state.authenticated = False
            st.warning("⏰ 세션이 만료되었습니다. 다시 로그인해주세요.")
    
    # 로그인 화면
    if not st.session_state.authenticated:
        st.markdown("## 🔐 마음다이렉트 로그인")
        
        with st.form("login_form"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.text_input(
                    "사용자명",
                    key="username",
                    placeholder="admin"
                )
                st.text_input(
                    "비밀번호",
                    type="password",
                    key="password",
                    placeholder="비밀번호 입력"
                )
            
            with col2:
                st.write("")
                st.write("")
                submitted = st.form_submit_button("🔓 로그인", use_container_width=True)
            
            if submitted:
                if check_password():
                    st.session_state.authenticated = True
                    st.session_state.login_time = datetime.now()
                    st.success("✅ 로그인 성공!")
                    st.rerun()
                else:
                    st.error("❌ 사용자명 또는 비밀번호가 틀렸습니다.")
        
        st.divider()
        st.info("""
            💡 **테스트 계정**
            - 사용자명: admin
            - 비밀번호: 관리자에게 문의
            
            📞 문의: 010-XXXX-XXXX
        """)
        
        # 로그인 실패 시 이후 코드 실행 방지
        st.stop()
    
    # 로그아웃 버튼
    col1, col2, col3 = st.columns([6, 1, 1])
    with col3:
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.login_time = None
            st.rerun()
    
    with col2:
        # 남은 시간 표시
        if st.session_state.login_time:
            elapsed = datetime.now() - st.session_state.login_time
            remaining = timedelta(minutes=30) - elapsed
            if remaining.total_seconds() > 0:
                minutes = int(remaining.total_seconds() / 60)
                st.caption(f"⏱️ {minutes}분")
    
def get_user_id():
    """현재 로그인한 사용자 ID 반환"""
    if st.session_state.get("authenticated"):
        return st.session_state.get("username", "unknown")
    return None

def rate_limit_check(action_name, max_calls=10, window_minutes=1):
    """API 호출 횟수 제한"""
    current_time = time.time()
    window_seconds = window_minutes * 60
    
    # 세션에 호출 기록 저장
    if f"{action_name}_calls" not in st.session_state:
        st.session_state[f"{action_name}_calls"] = []
    
    # 오래된 기록 제거
    st.session_state[f"{action_name}_calls"] = [
        call_time for call_time in st.session_state[f"{action_name}_calls"]
        if current_time - call_time < window_seconds
    ]
    
    # 호출 횟수 확인
    if len(st.session_state[f"{action_name}_calls"]) >= max_calls:
        st.error(f"⚠️ 너무 많은 요청! {window_minutes}분에 {max_calls}번만 가능합니다.")
        return False
    
    # 새 호출 기록
    st.session_state[f"{action_name}_calls"].append(current_time)
    return True

def sanitize_input(text):
    """입력 텍스트 검증 및 정화"""
    if not text:
        return ""
    
    # 최대 길이 제한
    max_length = 1000
    if len(text) > max_length:
        text = text[:max_length]
    
    # 위험한 문자 제거
    dangerous_chars = ['<script>', '</script>', 'javascript:', 'onclick=', 'onerror=']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    # SQL Injection 방지
    sql_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'EXEC', '--']
    for keyword in sql_keywords:
        text = text.replace(keyword, '')
    
    return text.strip()

def log_activity(action, details=None):
    """사용자 활동 로깅"""
    if "activity_log" not in st.session_state:
        st.session_state.activity_log = []
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user": get_user_id(),
        "action": action,
        "details": details
    }
    
    st.session_state.activity_log.append(log_entry)
    
    # 최대 100개 로그만 유지
    if len(st.session_state.activity_log) > 100:
        st.session_state.activity_log = st.session_state.activity_log[-100:]
    
    # 콘솔에도 출력 (디버깅용)
    print(f"[LOG] {log_entry}")

def validate_api_usage():
    """API 사용량 체크 및 제한"""
    # 일일 사용 제한
    today = datetime.now().strftime("%Y-%m-%d")
    
    if "api_usage" not in st.session_state:
        st.session_state.api_usage = {}
    
    if today not in st.session_state.api_usage:
        st.session_state.api_usage[today] = {
            "whisper_calls": 0,
            "gpt_calls": 0,
            "notion_saves": 0
        }
    
    usage = st.session_state.api_usage[today]
    
    # 제한 설정
    limits = {
        "whisper_calls": 100,  # 일일 음성인식 100회
        "gpt_calls": 500,       # 일일 GPT 호출 500회
        "notion_saves": 200     # 일일 노션 저장 200회
    }
    
    return usage, limits

def check_api_limit(api_type):
    """API 호출 전 제한 확인"""
    usage, limits = validate_api_usage()
    
    if usage.get(api_type, 0) >= limits.get(api_type, 0):
        st.error(f"⚠️ 일일 {api_type} 한도 초과! (제한: {limits[api_type]}회)")
        return False
    
    # 사용량 증가
    today = datetime.now().strftime("%Y-%m-%d")
    st.session_state.api_usage[today][api_type] += 1
    
    # 남은 횟수 표시
    remaining = limits[api_type] - st.session_state.api_usage[today][api_type]
    if remaining < 10:
        st.warning(f"📊 {api_type} 남은 횟수: {remaining}회")
    
    return True
