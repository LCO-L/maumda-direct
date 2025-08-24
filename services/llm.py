# llm.py - 건설현장 특화 버전 (완성 버전)
import os
import json
import re
from datetime import datetime, timedelta
from openai import OpenAI

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
    
    prompt = f"""
    당신은 건설 현장 관리 전문 AI입니다. 사용자의 말을 분석해서 다음과 같은 JSON 형식으로 변환해주세요:

    {{
        "site": "현장 이름 (예: 서울 XX아파트)",
        "amount": 금액 (숫자만),
        "type": "거래 유형 (중도금, 잔금, 계약금, 자재비, 인건비, 기타)",
        "due_date": "YYYY-MM-DD 형식",
        "contractor": "발주처/업체명",
        "category": "분류 (미장, 방수, 조적, 타일, 인테리어, 기타)",
        "payment_method": "결제 방식 (현금, 계좌이체, 외상, 카드)"
    }}

    **분석 규칙:**
    1. 금액은 항상 숫자만 포함 (예: 5000000)
    2. 날짜는 반드시 YYYY-MM-DD 형식으로 변환
    3. "다음 주 수요일" → 실제 날짜로 계산
    4. "OO아파트" → "서울 OO아파트"로 보완
    5. 분류는 건설업 종사자가 사용하는 용어로

    분석할 텍스트: "{text}"

    반드시 유효한 JSON 형식으로만 응답하세요.
    """
    
    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "당신은 건설 현장 관리 전문 AI입니다. 사용자의 말을 분석해서 구조화된 데이터로 변환해주세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
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
    # 금액 정규화 (문자열 → 숫자)
    if 'amount' in result and isinstance(result['amount'], str):
        # '500만원' → 5000000으로 변환
        amount_str = result['amount']
        if '만원' in amount_str:
            result['amount'] = int(amount_str.replace('만원', '').replace(',', '')) * 10000
        elif '원' in amount_str:
            result['amount'] = int(amount_str.replace('원', '').replace(',', ''))
    
    # 날짜 정규화 (상대적 표현 → 절대적 날짜)
    if 'due_date' in result and isinstance(result['due_date'], str):
        due_date = result['due_date']
        today = datetime.now()
        
        # 상대적 날짜 변환
        if '내일' in due_date:
            result['due_date'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif '모레' in due_date:
            result['due_date'] = (today + timedelta(days=2)).strftime('%Y-%m-%d')
        elif '다음 주' in due_date or '다음주' in due_date:
            # 다음 주 월요일 찾기
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:  # 이미 월요일인 경우
                days_until_monday = 7
            next_monday = today + timedelta(days=days_until_monday)
            
            # 요일 매칭
            if '월요일' in due_date:
                result['due_date'] = next_monday.strftime('%Y-%m-%d')
            elif '화요일' in due_date:
                result['due_date'] = (next_monday + timedelta(days=1)).strftime('%Y-%m-%d')
            elif '수요일' in due_date:
                result['due_date'] = (next_monday + timedelta(days=2)).strftime('%Y-%m-%d')
            elif '목요일' in due_date:
                result['due_date'] = (next_monday + timedelta(days=3)).strftime('%Y-%m-%d')
            elif '금요일' in due_date:
                result['due_date'] = (next_monday + timedelta(days=4)).strftime('%Y-%m-%d')
    
    # 현장명 보완
    if 'site' in result and '아파트' in result['site'] and '서울' not in result['site']:
        result['site'] = f"서울 {result['site']}"
    
    # 거래 유형 자동 분류
    if 'type' not in result:
        if any(keyword in original_text for keyword in ['중도금', '중도 금']):
            result['type'] = '중도금'
        elif any(keyword in original_text for keyword in ['잔금', '잔 금']):
            result['type'] = '잔금'
        elif any(keyword in original_text for keyword in ['계약금', '계약 금']):
            result['type'] = '계약금'
        elif any(keyword in original_text for keyword in ['자재비', '자재 값']):
            result['type'] = '자재비'
        elif any(keyword in original_text for keyword in ['인건비', '일당', '노무비']):
            result['type'] = '인건비'
        else:
            result['type'] = '기타'
    
    # 카테고리 자동 분류
    if 'category' not in result:
        if any(keyword in original_text for keyword in ['미장', '미장공']):
            result['category'] = '미장'
        elif any(keyword in original_text for keyword in ['방수', '방수공']):
            result['category'] = '방수'
        elif any(keyword in original_text for keyword in ['조적', '조적공']):
            result['category'] = '조적'
        elif any(keyword in original_text for keyword in ['타일', '타일공']):
            result['category'] = '타일'
        elif any(keyword in original_text for keyword in ['인테리어', '인테리어공']):
            result['category'] = '인테리어'
        else:
            result['category'] = '기타'
    
    # 결제 방식 자동 분류
    if 'payment_method' not in result:
        if any(keyword in original_text for keyword in ['현금', '현금으로']):
            result['payment_method'] = '현금'
        elif any(keyword in original_text for keyword in ['계좌', '이체', '송금']):
            result['payment_method'] = '계좌이체'
        elif any(keyword in original_text for keyword in ['카드', '체크카드', '신용카드']):
            result['payment_method'] = '카드'
        elif any(keyword in original_text for keyword in ['외상', '빚']):
            result['payment_method'] = '외상'
        else:
            result['payment_method'] = '미정'
    
    return result

def fallback_parse(text):
    """LLM 실패시 규칙 기반 파싱"""
    result = {
        'site': '',
        'amount': 0,
        'type': '기타',
        'due_date': '',
        'contractor': '',
        'category': '기타',
        'payment_method': '미정'
    }
    
    # 현장명/업체명 추출
    site_patterns = [
        r'(\S+(?:아파트|현장|빌딩|오피스텔|주택|빌라))',
        r'(\S+(?:구청|시청|동사무소))',
        r'(\S+건설)',
        r'(\S+인테리어)',
    ]
    
    for pattern in site_patterns:
        match = re.search(pattern, text)
        if match:
            result['site'] = match.group(1)
            # 서울 접두사 추가
            if '아파트' in result['site'] and '서울' not in result['site']:
                result['site'] = f"서울 {result['site']}"
            break
    
    # 발주처/업체명 추출
    contractor_patterns = [
        r'(\S+(?:건설|인테리어|시공사))',
        r'(\S+사장님)',
        r'(\S+씨)',
    ]
    
    for pattern in contractor_patterns:
        match = re.search(pattern, text)
        if match:
            result['contractor'] = match.group(1)
            break
    
    # 금액 추출 (만원 단위)
    amount_patterns = [
        r'(\d+)\s*만\s*원',
        r'(\d+)\s*만원',
        r'약\s*(\d+)\s*만',
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, text)
        if match:
            result['amount'] = int(match.group(1)) * 10000
            break
    
    # 날짜 추출 및 변환
    today = datetime.now()
    date_patterns = [
        (r'내일', (today + timedelta(days=1)).strftime('%Y-%m-%d')),
        (r'모레', (today + timedelta(days=2)).strftime('%Y-%m-%d')),
        (r'다음\s*주\s*월요일', (today + timedelta(days=(7 - today.weekday()))).strftime('%Y-%m-%d')),
        (r'다음\s*주\s*화요일', (today + timedelta(days=(8 - today.weekday()))).strftime('%Y-%m-%d')),
        (r'다음\s*주\s*수요일', (today + timedelta(days=(9 - today.weekday()))).strftime('%Y-%m-%d')),
        (r'다음\s*주\s*목요일', (today + timedelta(days=(10 - today.weekday()))).strftime('%Y-%m-%d')),
        (r'다음\s*주\s*금요일', (today + timedelta(days=(11 - today.weekday()))).strftime('%Y-%m-%d')),
        (r'(\d+)\s*일', lambda m: (today + timedelta(days=int(m.group(1)))).strftime('%Y-%m-%d')),
    ]
    
    for pattern, replacement in date_patterns:
        match = re.search(pattern, text)
        if match:
            if callable(replacement):
                result['due_date'] = replacement(match)
            else:
                result['due_date'] = replacement
            break
    
    # 거래 유형 추출
    if any(keyword in text for keyword in ['중도금', '중도 금']):
        result['type'] = '중도금'
    elif any(keyword in text for keyword in ['잔금', '잔 금']):
        result['type'] = '잔금'
    elif any(keyword in text for keyword in ['계약금', '계약 금']):
        result['type'] = '계약금'
    elif any(keyword in text for keyword in ['자재비', '자재 값']):
        result['type'] = '자재비'
    elif any(keyword in text for keyword in ['인건비', '일당', '노무비']):
        result['type'] = '인건비'
    
    # 카테고리 추출
    if any(keyword in text for keyword in ['미장', '미장공']):
        result['category'] = '미장'
    elif any(keyword in text for keyword in ['방수', '방수공']):
        result['category'] = '방수'
    elif any(keyword in text for keyword in ['조적', '조적공']):
        result['category'] = '조적'
    elif any(keyword in text for keyword in ['타일', '타일공']):
        result['category'] = '타일'
    elif any(keyword in text for keyword in ['인테리어', '인테리어공']):
        result['category'] = '인테리어'
    
    # 결제 방식 추출
    if any(keyword in text for keyword in ['현금', '현금으로']):
        result['payment_method'] = '현금'
    elif any(keyword in text for keyword in ['계좌', '이체', '송금']):
        result['payment_method'] = '계좌이체'
    elif any(keyword in text for keyword in ['카드', '체크카드', '신용카드']):
        result['payment_method'] = '카드'
    elif any(keyword in text for keyword in ['외상', '빚']):
        result['payment_method'] = '외상'
    
    return result

# 테스트
if __name__ == "__main__":
    test_cases = [
        "강남 아파트 타일공사 중도금 500만원 다음주 수요일에 받기로 했어",
        "북구청 방수 작업 끝나면 1000만원 잔금 현금으로 받을 거야",
        "김사장한테 인테리어 대금 300만원 15일에 계좌이체로 받아야 돼",
        "서초 빌라 미장 계약금 200만원 오늘 현금으로 받았어",
        "판교 오피스텔 조적공사 450만원 다음주 금요일에 외상으로 받기로 함"
    ]
    
    for text in test_cases:
        print(f"\n입력: {text}")
        result = analyze_text(text)
        print(f"분석 결과:")
        for key, value in result.items():
            if value:
                print(f"  {key}: {value}")
