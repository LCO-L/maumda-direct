import os
import requests

# Streamlit Cloud 호환
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Streamlit Cloud에서는 secrets 사용

# 환경변수 가져오기 (Streamlit Cloud와 로컬 모두 지원)
try:
    import streamlit as st
    NOTION_API_KEY = st.secrets.get("NOTION_API_KEY", os.getenv("NOTION_API_KEY"))
    NOTION_DB_ID = st.secrets.get("NOTION_DB_ID", os.getenv("NOTION_DB_ID"))
except:
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_DB_ID = os.getenv("NOTION_DB_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def _rt(text: str):
    """Rich text 헬퍼"""
    return {"rich_text": [{"text": {"content": text or ""}}]}

def ping_database() -> tuple[bool, str]:
    """DB 연결/권한/ID 확인용"""
    r = requests.get(f"https://api.notion.com/v1/databases/{NOTION_DB_ID}", headers=HEADERS)
    if r.status_code >= 300:
        return False, f"{r.status_code} {r.text}"
    j = r.json()
    title = "".join([t.get("plain_text","") for t in j.get("title",[])]) or "(제목 없음)"
    return True, f"OK: '{title}' (id={NOTION_DB_ID})"

def save_record(data: dict) -> tuple[int, str]:
    """
    현재 DB 스키마(who title / what rich_text / when date / where rich_text / why rich_text / how rich_text)에 맞춰 저장.
    성공: (HTTP 2xx, page_url) / 실패: (status, error_text)
    """
    if not NOTION_API_KEY or not NOTION_DB_ID:
        return 500, "NOTION_API_KEY 또는 NOTION_DB_ID 미설정"

    # 최소 타이틀 보장
    who_text = (data.get("who") or "").strip() or (data.get("where") or "").strip() or "새 기록"

    # 날짜: ISO(YYYY-MM-DD) 기대. 없으면 rich_text 대체 저장 가능하도록 처리
    when_iso = (data.get("when") or "").strip()
    when_prop = {"date": {"start": when_iso}} if when_iso else None

    properties = {
        # 🔸 who = title
        "who": {"title": [{"text": {"content": who_text}}]},
        # 🔸 what/where/why/how = rich_text
        "what": _rt(data.get("what", "")),
        "where": _rt(data.get("where", "")),
        "why": _rt(data.get("why", "")),
        "how": _rt(data.get("how", "")),
    }
    # 🔸 when = date (값이 없으면 아예 속성을 빼서 검증 에러 방지)
    if when_prop:
        properties["when"] = when_prop

    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": properties,
    }

    r = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)

    # 응답 처리
    try:
        j = r.json()
    except Exception:
        return r.status_code, r.text

    if 200 <= r.status_code < 300:
        return r.status_code, j.get("url") or j.get("id") or str(j)

    # 실패면 Notion 메시지 노출
    return r.status_code, j.get("message") or j.get("details") or str(j)
