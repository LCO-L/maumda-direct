# llm.py - 건설현장 특화 버전 (간단 버전)
import os
import json
from openai import OpenAI
import re

# Streamlit Cloud와 로컬 환경 모두 지원
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Streamlit Cloud에서는 secrets 사용

# DeepSeek API 설정
try:
    import streamlit as st
    DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY"))
except:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# DeepSeek 클라이언트 설정
deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

def analyze_text(text):
    """건설현장 맞춤형 자연어 분석"""
    
    prompt = """
    당신은 건설 현장을 데이터베이스에 옮기는 마법사입니다.
    사장님들이 일상적으로 사용하는 말을 분석해서 구조화합니다.
    
    다음 텍스트를 아래의 형식으로 분석하되, 건설업 맥락에 맞게 해석하세요:
    
    🏗️ 현장:
    📋 내용: (ex.타일공사)
    💰 금액:
    📅 언제:
    📍 위치:
    ❓ 어떻게:
    💡 왜:
    
    입력 예시:
    - "강남 아파트 타일공사 500만원 다음주 받기로 했어"
    - "북구청 방수 작업 끝나면 1000만원 잔금"
    - "김사장한테 인테리어 대금 300만원 15일에 받아야 돼"
    
    분석할 텍스트: {text}
    
    주의사항:
    1. 건설 현장 용어를 정확히 이해하세요 (미장, 방수, 조적, 타일, 인테리어)
    2. 금액은 "만원" 단위로 자주 표현됩니다
    3. 발주처와 현장명이 혼용되어 사용됩니다
    4. 계약금/중도금/잔금은 how 필드에 넣으세요
    5. 정보가 없는 필드는 빈 문자열("")로 남겨두세요
    
    반드시 유효한 JSON 형식으로만 응답하세요.
    """
    
    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "당신은 한국 건설현장 전문 데이터 분석가입니다. 반드시 JSON 형식으로만 응답하세요."},
                {"role": "user", "content": prompt.format(text=text)}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content or "{}")
        result = post_process_construction(result, text)
        return result
        
    except Exception as e:
        print(f"DeepSeek 분석 오류: {e}")
        return fallback_parse(text)

def post_process_construction(result, original_text):
    """건설현장 데이터 후처리"""
    
    # who 필드 보정: 현장명이 비어있으면 where나 why에서 가져오기
    if not result.get('who'):
        if result.get('where'):
            result['who'] = result['where']
        elif '아파트' in original_text or '현장' in original_text:
            import re
            match = re.search(r'(\S+(?:아파트|현장|빌딩|오피스텔|주택|빌라))', original_text)
            if match:
                result['who'] = match.group(1)
    
    # what 필드 보정: 금액 + 공사내용 조합
    if not result.get('what'):
        import re
        # 금액 찾기
        amount_match = re.search(r'(\d+)\s*만\s*원?', original_text)
        # 공사 종류 찾기
        work_match = re.search(r'(타일|방수|미장|조적|인테리어|도배|도장|철거|설비|전기)(?:공사)?', original_text)
        
        if amount_match and work_match:
            result['what'] = f"{work_match.group(0)} {amount_match.group(0)}"
        elif amount_match:
            result['what'] = amount_match.group(0)
    
    # how 필드 보정: 계약금/중도금/잔금 자동 감지
    if not result.get('how'):
        if '계약금' in original_text:
            result['how'] = '계약금'
        elif '중도금' in original_text:
            result['how'] = '중도금'
        elif '잔금' in original_text or '마지막' in original_text or '끝나면' in original_text:
            result['how'] = '잔금'
            
    return result

def fallback_parse(text):
    """LLM 실패시 규칙 기반 파싱"""
    import re
    
    result = {
        'who': '',
        'what': '',
        'when': '',
        'where': '',
        'why': '',
        'how': ''
    }
    
    # 현장명/업체명 추출
    site_patterns = [
        r'(\S+(?:아파트|현장|빌딩|오피스텔|주택|빌라|청|구청))',
        r'(\S+사장(?:님)?)',
        r'(\S+건설)',
    ]
    for pattern in site_patterns:
        match = re.search(pattern, text)
        if match:
            result['who'] = match.group(1)
            break
    
    # 금액 추출
    amount_match = re.search(r'(\d+)\s*만\s*원?', text)
    if amount_match:
        result['what'] = f"{amount_match.group(1)}만원"
    
    # 날짜 추출
    date_patterns = [
        r'(오늘|내일|모레|어제)',
        r'(이번\s*주|다음\s*주|다음주)',
        r'(\d+일)',
        r'(월요일|화요일|수요일|목요일|금요일|토요일|일요일)'
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            result['when'] = match.group(1)
            break
    
    # 공사 종류 추출
    work_match = re.search(r'(타일|방수|미장|조적|인테리어|도배|도장|철거|설비|전기)(?:공사)?', text)
    if work_match:
        result['why'] = work_match.group(0)
        if result['what'] and '만원' in result['what']:
            result['what'] = f"{work_match.group(0)} {result['what']}"
    
    # 결제 방식
    if '계약금' in text:
        result['how'] = '계약금'
    elif '중도금' in text:
        result['how'] = '중도금'
    elif '잔금' in text:
        result['how'] = '잔금'
    
    return result

# 테스트
if __name__ == "__main__":
    test_cases = [
        "강남 아파트 타일공사 500만원 다음주 받기로 했어",
        "북구청 방수 작업 끝나면 1000만원 잔금",
        "김사장한테 인테리어 대금 300만원 15일에 받아야 돼",
        "서초 빌라 미장 200만원 계약금 오늘 받았어",
        "판교 오피스텔 도배 끝나고 450만원 받기로 함"
    ]
    
    for text in test_cases:
        print(f"\n입력: {text}")
        result = analyze_text(text)
        print(f"분석 결과:")
        for key, value in result.items():
            if value:
                print(f"  {key}: {value}")

