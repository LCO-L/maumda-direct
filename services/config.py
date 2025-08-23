# services/config.py
import os
import streamlit as st

def get_secret(key):
    """로컬과 Streamlit Cloud 환경 모두 지원"""
    # Streamlit Cloud
    if hasattr(st, 'secrets'):
        try:
            return st.secrets[key]
        except:
            pass
    
    # 로컬 환경 (.env)
    return os.getenv(key)

# 사용 예시:
# NOTION_API_KEY = get_secret("NOTION_API_KEY")

