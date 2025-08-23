import os
import requests
from dotenv import load_dotenv

# .env 로드
load_dotenv()
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def _rt(text: str):
    """Notion rich_text helper"""
    return {"rich_text": [{"text": {"content": text or ""}}]}

def save_record(data: dict) -> tuple[int, str]:
    """
    normalize_data()된 dict를 받아 Notion DB에 1행을 생성한다.
    필요한 DB 속성(컬럼):
      - 발주처(Who)  : Title
      - 금액(What)   : Rich text
      - 날짜(When)   : Date   (ISO: YYYY-MM-DD)
      - 현장(Where)  : Rich text
      - 목적(Why)    : Rich text
      - 결제방법(How): Rich text
    """
    if not NOTION_API_KEY or not NOTION_DB_ID:
        return 500, "NOTION_API_KEY 또는 NOTION_DB_ID가 설정되지 않았습니다."

    when_iso = data.get("when")  # normalize_data에서 ISO로 세팅됨(없으면 None/없음)
    # 날짜 속성은 date 타입 권장. 없으면 rich_text로 대체
    when_prop = {"date": {"start": when_iso}} if when_iso and when_iso != "없음" else _rt(data.get("when_pretty", ""))

    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "발주처(Who)": {"title": [{"text": {"content": data.get("who", "")}}]},
            "금액(What)": _rt(data.get("what", "")),
            "날짜(When)": when_prop,
            "현장(Where)": _rt(data.get("where", "")),
            "목적(Why)": _rt(data.get("why", "")),
            "결제방법(How)": _rt(data.get("how", "")),
        }
    }

    r = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)
    return r.status_code, r.text
