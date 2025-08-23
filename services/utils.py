# utils.py
from datetime import datetime, timedelta
import re

def parse_korean_date(date_str: str) -> str:
    """
    한국어 날짜 표현을 ISO 8601 형식(YYYY-MM-DD)으로 변환
    
    예시:
    - "오늘" → "2025-01-23"
    - "내일" → "2025-01-24"
    - "다음주 수요일" → "2025-01-29"
    - "2025년 2월 15일" → "2025-02-15"
    - "2/15" → "2025-02-15"
    """
    if not date_str:
        return ""
    
    date_str = date_str.strip()
    today = datetime.now()
    
    # ISO 형식이면 그대로 반환
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # 오늘/내일/모레
    if date_str == "오늘":
        return today.strftime("%Y-%m-%d")
    elif date_str == "내일":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    elif date_str == "모레":
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")
    elif date_str == "어제":
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 이번주/다음주 + 요일
    weekdays = {
        "월요일": 0, "화요일": 1, "수요일": 2, "목요일": 3,
        "금요일": 4, "토요일": 5, "일요일": 6
    }
    
    if "이번주" in date_str or "이번 주" in date_str:
        for day_name, day_num in weekdays.items():
            if day_name in date_str:
                # 이번 주의 특정 요일 계산
                days_ahead = day_num - today.weekday()
                if days_ahead < 0:  # 이미 지난 경우 다음 주로
                    days_ahead += 7
                return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    if "다음주" in date_str or "다음 주" in date_str:
        for day_name, day_num in weekdays.items():
            if day_name in date_str:
                # 다음 주의 특정 요일 계산
                days_until_next_monday = 7 - today.weekday()
                target_date = today + timedelta(days=days_until_next_monday)
                days_to_target = day_num
                return (target_date + timedelta(days=days_to_target)).strftime("%Y-%m-%d")
    
    # 요일만 있는 경우 (이번 주 또는 다음 주)
    for day_name, day_num in weekdays.items():
        if date_str == day_name:
            days_ahead = day_num - today.weekday()
            if days_ahead <= 0:  # 이미 지났거나 오늘이면 다음 주
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    # X일 후/뒤
    match = re.search(r'(\d+)일\s*(후|뒤)', date_str)
    if match:
        days = int(match.group(1))
        return (today + timedelta(days=days)).strftime("%Y-%m-%d")
    
    # 2025년 1월 23일 형식
    match = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 1월 23일 형식 (연도 없음 - 현재 연도 사용)
    match = re.search(r'(\d{1,2})월\s*(\d{1,2})일', date_str)
    if match:
        month, day = match.groups()
        year = today.year
        # 만약 날짜가 이미 지났다면 내년으로
        target_date = datetime(year, int(month), int(day))
        if target_date < today:
            year += 1
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 1/23 또는 01-23 형식
    match = re.search(r'(\d{1,2})[/-](\d{1,2})', date_str)
    if match:
        month, day = match.groups()
        year = today.year
        # 만약 날짜가 이미 지났다면 내년으로
        try:
            target_date = datetime(year, int(month), int(day))
            if target_date < today:
                year += 1
        except:
            pass
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 2025-01-23 형식 (이미 ISO지만 검증)
    match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 변환 실패 시 빈 문자열 반환 (노션에서 date 필드는 빈 값 허용)
    return ""


def normalize_amount(amount_str: str) -> str:
    """
    금액 표현을 정규화
    
    예시:
    - "1000만원" → "10,000,000원"
    - "500만" → "5,000,000원"
    - "3천만원" → "30,000,000원"
    - "15억" → "1,500,000,000원"
    - "5000000" → "5,000,000원"
    """
    if not amount_str:
        return amount_str
    
    # 숫자와 단위 추출
    amount_str = str(amount_str).strip()
    
    # 이미 포맷된 경우 (콤마 포함) 그대로 반환
    if ',' in amount_str and '원' in amount_str:
        return amount_str
    
    total = 0
    
    # 억 단위 처리
    if '억' in amount_str:
        match = re.search(r'(\d+(?:\.\d+)?)\s*억', amount_str)
        if match:
            num = float(match.group(1))
            total = int(num * 100000000)
            
            # 만원 단위가 추가로 있는지 확인
            match_man = re.search(r'억\s*(\d+(?:\.\d+)?)\s*만', amount_str)
            if match_man:
                man_num = float(match_man.group(1))
                total += int(man_num * 10000)
    # 천만 단위 처리
    elif '천만' in amount_str:
        match = re.search(r'(\d+(?:\.\d+)?)\s*천만', amount_str)
        if match:
            num = float(match.group(1))
            total = int(num * 10000000)
        else:
            total = 10000000
    # 백만 단위 처리
    elif '백만' in amount_str:
        match = re.search(r'(\d+(?:\.\d+)?)\s*백만', amount_str)
        if match:
            num = float(match.group(1))
            total = int(num * 1000000)
        else:
            total = 1000000
    # 만 단위 처리
    elif '만' in amount_str:
        match = re.search(r'(\d+(?:\.\d+)?)\s*만', amount_str)
        if match:
            num = float(match.group(1))
            total = int(num * 10000)
        else:
            total = 10000
    # 천 단위 처리
    elif '천' in amount_str:
        match = re.search(r'(\d+(?:\.\d+)?)\s*천', amount_str)
        if match:
            num = float(match.group(1))
            total = int(num * 1000)
        else:
            total = 1000
    # 순수 숫자만 있는 경우
    else:
        # 콤마 제거하고 숫자만 추출
        clean_num = re.sub(r'[^\d]', '', amount_str)
        if clean_num:
            # 6자리 이상이면 그대로 사용 (이미 완전한 금액)
            if len(clean_num) >= 6:
                total = int(clean_num)
            # 4자리 이하면 만원 단위로 간주
            elif len(clean_num) <= 4:
                total = int(clean_num) * 10000
            else:
                total = int(clean_num)
        else:
            return amount_str
    
    # 천 단위 콤마 추가
    formatted = "{:,}원".format(total)
    return formatted


def normalize_data(raw_data: dict) -> dict:
    """
    LLM 분석 결과를 정제하여 노션 저장용 데이터로 변환
    
    - when: 한국어 날짜 → ISO 8601 형식
    - what: 금액이 포함된 경우 정규화
    - 나머지 필드는 그대로 유지
    """
    normalized = raw_data.copy()
    
    # 날짜 변환
    if 'when' in normalized and normalized['when']:
        iso_date = parse_korean_date(normalized['when'])
        if iso_date:
            normalized['when'] = iso_date
            normalized['when_display'] = raw_data['when']  # 원래 표현 보관
        else:
            # 변환 실패 시 when 필드 제거 (노션에서 에러 방지)
            normalized['when_display'] = raw_data['when']
            normalized['when'] = ""
    
    # 금액 정규화 (what 필드에 금액이 있는 경우)
    if 'what' in normalized and normalized['what']:
        what_text = normalized['what']
        
        # 금액 관련 키워드가 있으면 정규화
        if any(keyword in what_text for keyword in ['원', '만', '천', '억', '백만']):
            normalized['what_display'] = what_text  # 원래 표현 보관
            
            # 금액 부분만 추출하여 정규화
            amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:만|천만|백만|억)\s*원?', what_text)
            if amount_match:
                # 전체 매칭된 부분
                full_match = amount_match.group(0)
                # 정규화된 금액
                normalized_amount = normalize_amount(full_match)
                # 원본 텍스트에서 금액 부분을 정규화된 것으로 교체
                normalized['what'] = what_text.replace(full_match, normalized_amount)
            else:
                # 숫자만 있는 경우도 처리
                num_match = re.search(r'(\d+)\s*원?', what_text)
                if num_match:
                    full_match = num_match.group(0)
                    normalized_amount = normalize_amount(full_match)
                    normalized['what'] = what_text.replace(full_match, normalized_amount)
    
    return normalized


# 테스트 코드
if __name__ == "__main__":
    # 날짜 테스트
    test_dates = [
        "오늘",
        "내일",
        "모레",
        "다음주 수요일",
        "이번주 금요일",
        "2025년 2월 15일",
        "3월 10일",
        "3/15",
        "10일 후",
        "수요일",
    ]
    
    print("=== 날짜 변환 테스트 ===")
    for date_str in test_dates:
        result = parse_korean_date(date_str)
        print(f"{date_str:15} → {result}")
    
    print("\n=== 금액 변환 테스트 ===")
    test_amounts = [
        "1000만원",
        "500만",
        "3천만원",
        "15억",
        "2억 3천만원",
        "5000원",
        "타일공사 500만원",
        "1000",
        "5000000",
    ]
    
    for amount in test_amounts:
        result = normalize_amount(amount)
        print(f"{amount:20} → {result}")