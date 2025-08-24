# llm.py - 건설현장 실무 특화 버전
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
    pass

# DeepSeek API 설정
try:
    import streamlit as st
    DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY"))
except:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# DeepSeek 클라이언트 설정
if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1"
    )
else:
    deepseek_client = None

def analyze_text(text):
    """건설현장 실무 중심 텍스트 분석"""
    
    prompt = f"""
    건설현장 수금 관리 시스템입니다.
    아래 텍스트를 분석해서 JSON 형식으로 변환하세요.

    분석할 텍스트: "{text}"

    반환 형식:
    {{
        "site_name": "현장명 또는 거래처명",
        "work_type": "작업 종류",
        "amount": "금액 (숫자만)",
        "payment_type": "계약금|중도금|잔금|자재비|인건비|기타",
        "expected_date": "받을 날짜",
        "payment_method": "현금|계좌이체|카드|미정",
        "memo": "추가 메모사항"
    }}

    **분석 규칙:**
    1. site_name: "북구청", "강남 아파트", "김사장" 등 거래처/현장명
    2. work_type: "방수", "타일", "미장", "조적", "인테리어" 등
    3. amount: 숫자만 (예: "1000만원" → "10000000")
    4. payment_type: 텍스트에서 "잔금", "중도금" 등 찾기
    5. expected_date: "YYYY-MM-DD" 형식으로 변환
    6. 정보가 없으면 빈 문자열 ""
    
    반드시 유효한 JSON만 반환하세요.
    """
    
    if deepseek_client:
        try:
            response = deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "건설현장 수금 관리 데이터 분석 AI"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content or "{}")
            print(f"AI 분석 결과: {result}")
            return post_process(result, text)
            
        except Exception as e:
            print(f"AI 분석 오류: {e}")
            return rule_based_parse(text)
    else:
        return rule_based_parse(text)

def rule_based_parse(text):
    """규칙 기반 파싱 (AI 없이도 작동)"""
    result = {
        'site_name': '',
        'work_type': '',
        'amount': '',
        'payment_type': '',
        'expected_date': '',
        'payment_method': '',
        'memo': ''
    }
    
    # 1. 현장명/거래처 추출
    site_patterns = [
        (r'(\S+구청)', 1),
        (r'(\S+시청)', 1),
        (r'(\S+청사)', 1),
        (r'(\S+\s?아파트)', 1),
        (r'(\S+\s?현장)', 1),
        (r'(\S+\s?빌딩)', 1),
        (r'(\S+\s?오피스텔)', 1),
        (r'(\S+\s?빌라)', 1),
        (r'(\S+\s?주택)', 1),
        (r'(\S+건설)', 1),
        (r'(\S+건축)', 1),
        (r'(\S+시공)', 1),
        (r'(\S+인테리어)', 1),
        (r'(\S+사장)', 1),
    ]
    
    for pattern, group in site_patterns:
        match = re.search(pattern, text)
        if match:
            result['site_name'] = match.group(group).strip()
            break
    
    # 2. 작업 종류 추출
    work_keywords = {
        '방수': '방수공사',
        '미장': '미장공사',
        '조적': '조적공사',
        '타일': '타일공사',
        '인테리어': '인테리어',
        '도색': '도색작업',
        '페인트': '페인트작업',
        '전기': '전기공사',
        '설비': '설비공사',
        '철근': '철근작업',
        '도배': '도배작업',
        '장판': '장판작업',
        '샷시': '샷시공사',
        '유리': '유리공사',
        '목공': '목공작업',
        '철거': '철거작업',
        '청소': '청소작업'
    }
    
    for keyword, work_name in work_keywords.items():
        if keyword in text:
            result['work_type'] = work_name
            break
    
    # 작업이 안 나오면 text에서 "작업" 앞 단어 추출
    if not result['work_type']:
        work_match = re.search(r'(\S+)\s*작업', text)
        if work_match:
            result['work_type'] = f"{work_match.group(1)}작업"
    
    # 3. 금액 추출 (숫자로 변환)
    amount_patterns = [
        (r'(\d+)\s*억\s*(\d+)?\s*만?\s*원?', lambda m: 
            int(m.group(1)) * 100000000 + (int(m.group(2)) * 10000 if m.group(2) else 0)),
        (r'(\d+)\s*천\s*만\s*원?', lambda m: int(m.group(1)) * 10000000),
        (r'(\d+)\s*백\s*만\s*원?', lambda m: int(m.group(1)) * 1000000),
        (r'(\d+)\s*만\s*원', lambda m: int(m.group(1)) * 10000),
        (r'(\d+)\s*만원', lambda m: int(m.group(1)) * 10000),
        (r'(\d+)만', lambda m: int(m.group(1)) * 10000),
        (r'(\d{7,})\s*원', lambda m: int(m.group(1))),  # 7자리 이상 숫자
        (r'(\d+,\d+)\s*원', lambda m: int(m.group(1).replace(',', ''))),
    ]
    
    for pattern, converter in amount_patterns:
        match = re.search(pattern, text)
        if match:
            result['amount'] = str(converter(match))
            break
    
    # 4. 거래 유형 추출
    payment_types = {
        '계약금': '계약금',
        '착수금': '계약금',
        '선금': '계약금',
        '중도금': '중도금',
        '중도 금': '중도금',
        '잔금': '잔금',
        '잔 금': '잔금',
        '완료금': '잔금',
        '준공금': '잔금',
        '자재비': '자재비',
        '자재 비': '자재비',
        '자재값': '자재비',
        '자재 값': '자재비',
        '인건비': '인건비',
        '인건 비': '인건비',
        '노무비': '인건비',
        '일당': '인건비',
        '품값': '인건비',
        '품삯': '인건비'
    }
    
    for keyword, ptype in payment_types.items():
        if keyword in text:
            result['payment_type'] = ptype
            break
    
    if not result['payment_type']:
        result['payment_type'] = '기타'
    
    # 5. 예상 날짜 추출
    today = datetime.now()  # 시스템 날짜 자동 가져오기
    
    # 조건부 날짜 (작업 완료 후 등)
    if any(word in text for word in ['끝나면', '완료되면', '완료후', '완료 후', '끝나고']):
        result['expected_date'] = '작업 완료 후'
    # 다음주 + 요일 패턴
    elif '다음주' in text or '다음 주' in text:
        # 현재 요일 확인 (0=월요일, 6=일요일)
        current_weekday = today.weekday()
        
        # 다음주 시작(월요일)까지 일수 계산
        if current_weekday == 6:  # 일요일
            days_to_next_monday = 1
        else:
            days_to_next_monday = 7 - current_weekday
        
        next_monday = today + timedelta(days=days_to_next_monday)
        
        # 요일별 처리
        weekday_offsets = {
            '월요일': 0,
            '화요일': 1, 
            '수요일': 2,
            '목요일': 3,
            '금요일': 4,
            '토요일': 5,
            '일요일': 6
        }
        
        # 요일 찾기
        found_weekday = False
        for day_name, offset in weekday_offsets.items():
            if day_name in text:
                target_date = next_monday + timedelta(days=offset)
                result['expected_date'] = target_date.strftime('%Y-%m-%d')
                found_weekday = True
                break
        
        # 요일이 명시되지 않은 경우 다음주 월요일
        if not found_weekday:
            result['expected_date'] = next_monday.strftime('%Y-%m-%d')
    
    # 이번주 + 요일 패턴
    elif '이번주' in text or '이번 주' in text:
        weekday_map = {
            '월요일': 0, '화요일': 1, '수요일': 2, '목요일': 3,
            '금요일': 4, '토요일': 5, '일요일': 6
        }
        
        for day_name, day_num in weekday_map.items():
            if day_name in text:
                # 이번주의 특정 요일 계산
                days_ahead = day_num - today.weekday()
                if days_ahead <= 0:  # 이미 지난 경우
                    days_ahead += 7
                result['expected_date'] = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                break
    
    # 요일만 언급된 경우 (이번주로 간주)
    elif any(day in text for day in ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']):
        weekday_map = {
            '월요일': 0, '화요일': 1, '수요일': 2, '목요일': 3,
            '금요일': 4, '토요일': 5, '일요일': 6
        }
        
        for day_name, day_num in weekday_map.items():
            if day_name in text:
                days_ahead = day_num - today.weekday()
                if days_ahead <= 0:  # 이미 지났거나 오늘이면 다음주
                    days_ahead += 7
                result['expected_date'] = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                break
    
    # 기타 날짜 패턴들
    else:
        date_patterns = [
            (r'오늘', today.strftime('%Y-%m-%d')),
            (r'내일', (today + timedelta(days=1)).strftime('%Y-%m-%d')),
            (r'모레', (today + timedelta(days=2)).strftime('%Y-%m-%d')),
            (r'글피', (today + timedelta(days=3)).strftime('%Y-%m-%d')),
            (r'어제', (today - timedelta(days=1)).strftime('%Y-%m-%d')),
            (r'(\d+)일\s*후', lambda m: (today + timedelta(days=int(m.group(1)))).strftime('%Y-%m-%d')),
            (r'(\d+)일\s*뒤', lambda m: (today + timedelta(days=int(m.group(1)))).strftime('%Y-%m-%d')),
            (r'(\d+)일\s*전', lambda m: (today - timedelta(days=int(m.group(1)))).strftime('%Y-%m-%d')),
        ]
        
        for pattern, replacement in date_patterns:
            match = re.search(pattern, text)
            if match:
                if callable(replacement):
                    result['expected_date'] = replacement(match)
                else:
                    result['expected_date'] = replacement
                break
        
        # 구체적 날짜 패턴
        if not result.get('expected_date'):
            # 월/일 형식
            date_match = re.search(r'(\d{1,2})[월/]\s*(\d{1,2})', text)
            if date_match:
                month = int(date_match.group(1))
                day = int(date_match.group(2))
                year = today.year
                try:
                    target_date = datetime(year, month, day)
                    if target_date < today:
                        year += 1
                    result['expected_date'] = f"{year}-{month:02d}-{day:02d}"
                except:
                    pass
        
        # 이번주 + 요일 패턴
        elif '이번주' in text or '이번 주' in text:
            weekday_map = {
                '월요일': 0, '화요일': 1, '수요일': 2, '목요일': 3,
                '금요일': 4, '토요일': 5, '일요일': 6
            }
            
            for day_name, day_num in weekday_map.items():
                if day_name in text:
                    # 이번주의 특정 요일 계산
                    days_ahead = day_num - today.weekday()
                    if days_ahead <= 0:  # 이미 지난 경우
                        days_ahead += 7
                    result['expected_date'] = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                    break
        
        # 요일만 언급된 경우 (이번주로 간주)
        elif any(day in text for day in ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']):
            weekday_map = {
                '월요일': 0, '화요일': 1, '수요일': 2, '목요일': 3,
                '금요일': 4, '토요일': 5, '일요일': 6
            }
            
            for day_name, day_num in weekday_map.items():
                if day_name in text:
                    days_ahead = day_num - today.weekday()
                    if days_ahead <= 0:  # 이미 지났거나 오늘이면 다음주
                        days_ahead += 7
                    result['expected_date'] = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                    break
        
        # 기타 날짜 패턴들
        else:
            date_patterns = [
                (r'오늘', today.strftime('%Y-%m-%d')),
                (r'내일', (today + timedelta(days=1)).strftime('%Y-%m-%d')),
                (r'모레', (today + timedelta(days=2)).strftime('%Y-%m-%d')),
                (r'글피', (today + timedelta(days=3)).strftime('%Y-%m-%d')),
                (r'어제', (today - timedelta(days=1)).strftime('%Y-%m-%d')),
                (r'(\d+)일\s*후', lambda m: (today + timedelta(days=int(m.group(1)))).strftime('%Y-%m-%d')),
                (r'(\d+)일\s*뒤', lambda m: (today + timedelta(days=int(m.group(1)))).strftime('%Y-%m-%d')),
                (r'(\d+)일\s*전', lambda m: (today - timedelta(days=int(m.group(1)))).strftime('%Y-%m-%d')),
            ]
        
        for pattern, replacement in date_patterns:
            match = re.search(pattern, text)
            if match:
                if callable(replacement):
                    result['expected_date'] = replacement(match)
                else:
                    result['expected_date'] = replacement
                break
        
        # 구체적 날짜 패턴
        if not result['expected_date']:
            # 월/일 형식
            date_match = re.search(r'(\d{1,2})[월/]\s*(\d{1,2})', text)
            if date_match:
                month = int(date_match.group(1))
                day = int(date_match.group(2))
                year = today.year
                try:
                    target_date = datetime(year, month, day)
                    if target_date < today:
                        year += 1
                    result['expected_date'] = f"{year}-{month:02d}-{day:02d}"
                except:
                    pass
    
    # 6. 결제 방식 추출
    payment_methods = {
        '현금': '현금',
        '캐시': '현금',
        '계좌': '계좌이체',
        '이체': '계좌이체',
        '송금': '계좌이체',
        '입금': '계좌이체',
        '카드': '카드',
        '체크카드': '카드',
        '신용카드': '카드',
        '외상': '외상',
        '후불': '외상'
    }
    
    for keyword, method in payment_methods.items():
        if keyword in text:
            result['payment_method'] = method
            break
    
    if not result['payment_method']:
        result['payment_method'] = '미정'
    
    # 7. 전체 텍스트를 메모로
    result['memo'] = text
    
    return result

def post_process(result, original_text):
    """AI 결과 후처리 및 보정"""
    # amount가 문자열인 경우 숫자로 변환
    if 'amount' in result and result['amount']:
        amount_str = str(result['amount'])
        # 이미 숫자만 있으면 그대로
        if amount_str.isdigit():
            pass
        # "500만원" 형태면 변환
        elif '만원' in amount_str or '만' in amount_str:
            match = re.search(r'(\d+)', amount_str)
            if match:
                result['amount'] = str(int(match.group(1)) * 10000)
    
    # 날짜 형식 검증
    if 'expected_date' in result and result['expected_date']:
        if not re.match(r'\d{4}-\d{2}-\d{2}', result['expected_date']):
            # 상대적 날짜 표현 처리
            from services.utils import parse_korean_date
            parsed_date = parse_korean_date(result['expected_date'])
            if parsed_date:
                result['expected_date'] = parsed_date
    
    # 빈 필드 처리
    for key in ['site_name', 'work_type', 'amount', 'payment_type', 'expected_date', 'payment_method', 'memo']:
        if key not in result:
            result[key] = ''
    
    # 메모가 없으면 원본 텍스트 저장
    if not result.get('memo'):
        result['memo'] = original_text
    
    return result

def normalize_data(raw_data):
    """
    LLM 분석 결과를 Notion 저장용 형식으로 변환
    건설현장 필드 → 5W1H 매핑
    """
    # 금액 포맷팅
    amount_str = ""
    if raw_data.get('amount'):
        try:
            amount_num = int(raw_data['amount'])
            amount_str = f"{amount_num:,}원"
        except:
            amount_str = raw_data.get('amount', '')
    
    # 작업 내용 조합 (금액 제외)
    what_parts = []
    if raw_data.get('work_type'):
        what_parts.append(raw_data['work_type'])
    if raw_data.get('payment_type'):
        what_parts.append(f"({raw_data['payment_type']})")
    
    what_text = " ".join(what_parts) if what_parts else raw_data.get('memo', '')
    
    # 5W1H 형식으로 변환
    normalized = {
        'who': raw_data.get('site_name', ''),          # 현장명
        'what': what_text,                              # 작업내용
        'when': raw_data.get('expected_date', ''),      # 날짜
        'where': raw_data.get('site_name', ''),         # 위치
        'why': raw_data.get('payment_type', ''),        # 거래유형
        'how': amount_str,                              # 💰 금액 (변경됨!)
        
        # 추가 필드 (UI 표시용)
        'original_amount': raw_data.get('amount', ''),
        'work_type': raw_data.get('work_type', ''),
        'payment_method': raw_data.get('payment_method', ''),
        'memo': raw_data.get('memo', '')
    }
    
    return normalized

# 테스트
if __name__ == "__main__":
    test_cases = [
        "북구청 방수 작업 끝나면 1000만원 잔금",
        "강남 아파트 타일공사 중도금 500만원 다음주 수요일",
        "김사장 인테리어 계약금 300만원 내일 현금",
        "서초 빌라 미장 200만원 15일 계좌이체",
        "판교 오피스텔 조적공사 450만원 완료후 받기",
        "상가 전기공사 150만원 월말",
        "이번달 말까지 도배 인건비 80만원"
    ]
    
    print("=" * 60)
    for text in test_cases:
        print(f"\n📝 입력: {text}")
        result = analyze_text(text)
        print(f"🔍 분석 결과:")
        for key, value in result.items():
            if value:
                print(f"   {key}: {value}")
        
        print(f"\n📦 Notion 저장 형식:")
        normalized = normalize_data(result)
        print(f"   🏗️ 현장(who): {normalized['who']}")
        print(f"   📋 내용(what): {normalized['what']}")
        print(f"   📅 언제(when): {normalized['when']}")
        print(f"   📍 위치(where): {normalized['where']}")
        print(f"   ❓ 유형(why): {normalized['why']}")
        print(f"   💰 금액(how): {normalized['how']}")
        print("-" * 40)
