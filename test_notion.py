# test_notion.py
from services.notion import ping_database, save_record
import json

# 1. 연결 테스트
print("=== 1. DB 연결 테스트 ===")
success, message = ping_database()
print(f"결과: {success}")
print(f"메시지: {message}\n")

# 2. 데이터 저장 테스트
print("=== 2. 데이터 저장 테스트 ===")
test_data = {
    "who": "테스트 사용자",
    "what": "API 테스트 중",
    "when": "2025-01-23",  # ISO 형식
    "where": "VSCode",
    "why": "노션 연동 디버깅",
    "how": "Python 스크립트로"
}

status, result = save_record(test_data)
print(f"상태 코드: {status}")
print(f"결과: {result}")

# 3. 환경변수 확인 (보안상 일부만 출력)
print("\n=== 3. 환경변수 확인 ===")
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("NOTION_API_KEY")
db_id = os.getenv("NOTION_DB_ID")

print(f"API Key 설정: {'있음' if api_key else '없음'} (길이: {len(api_key) if api_key else 0})")
print(f"DB ID 설정: {'있음' if db_id else '없음'} (길이: {len(db_id) if db_id else 0})")

if api_key:
    print(f"API Key 시작: {api_key[:10]}...")
if db_id:
    print(f"DB ID: {db_id}")

# 4. 상세 디버깅 (필요시)
print("\n=== 4. 상세 요청 정보 (디버깅용) ===")
if not success:
    print("DB 연결 실패 - API 키와 DB ID를 확인하세요")
else:
    # 실제 요청 데이터 확인을 위한 추가 테스트
    import requests
    
    HEADERS = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    
    # DB 메타데이터 가져오기
    r = requests.get(f"https://api.notion.com/v1/databases/{db_id}", headers=HEADERS)
    if r.status_code == 200:
        db_info = r.json()
        print("DB 속성들:")
        for prop_name, prop_info in db_info.get("properties", {}).items():
            print(f"  - {prop_name}: {prop_info.get('type')}")
    else:
        print(f"DB 정보 가져오기 실패: {r.status_code}")
        print(f"에러: {r.text[:500]}")  # 처음 500자만 출력