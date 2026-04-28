import re
from config import CATEGORIES, ACTION_KEYWORDS, DEADLINE_PATTERNS


# ──────────────────────────────────────────
# 1. 분류
# ──────────────────────────────────────────

def classify(text: str) -> tuple[str, float]:
    """
    키워드 빈도 기반 분류
    반환: (카테고리, 신뢰도 0~1)
    """
    scores = {cat: sum(text.count(kw) for kw in kws)
              for cat, kws in CATEGORIES.items()}
    total = sum(scores.values())
    if total == 0:
        return "기타", 0.0

    best = max(scores, key=scores.get)
    confidence = round(scores[best] / total, 2)
    return best, confidence


# ──────────────────────────────────────────
# 2. 액션 필요 여부
# ──────────────────────────────────────────

def needs_action(text: str) -> bool:
    """'나한테 뭔가 해달라는' 메일인지 판단"""
    return any(kw in text for kw in ACTION_KEYWORDS)


# ──────────────────────────────────────────
# 3. 기한 감지
# ──────────────────────────────────────────

def find_deadline(text: str) -> str | None:
    """텍스트에서 기한 표현 추출 (첫 번째 매치)"""
    for pattern in DEADLINE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            return m.group(0)
    return None


# ──────────────────────────────────────────
# 4. 주요 정보 추출 (정규표현식)
# ──────────────────────────────────────────

def extract_info(text: str) -> dict:
    emails  = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    dates   = re.findall(r'\d{4}[-./]\d{1,2}[-./]\d{1,2}', text)
    amounts = re.findall(r'\d{1,3}(?:,\d{3})*\s*원', text)
    phones  = re.findall(r'0\d{1,2}[-.\s]\d{3,4}[-.\s]\d{4}', text)
    return {
        "emails":  list(dict.fromkeys(emails)),   # 중복 제거, 순서 유지
        "dates":   list(dict.fromkeys(dates)),
        "amounts": list(dict.fromkeys(amounts)),
        "phones":  list(dict.fromkeys(phones)),
    }


# ──────────────────────────────────────────
# 5. 통합 분석 (메일 1건)
# ──────────────────────────────────────────

def analyze(email_data: dict, pdf_texts: dict) -> dict:
    """
    email_data: fetch_emails() 결과 1건
    pdf_texts:  extract_all() 결과 {파일명: 텍스트}
    """
    full_text = " ".join([
        email_data.get("subject", ""),
        email_data.get("body", ""),
        *pdf_texts.values(),
    ])

    category, confidence = classify(full_text)
    deadline = find_deadline(full_text)
    info = extract_info(full_text)

    # 요약: 본문 첫 2문장
    body = email_data.get("body", "").strip()
    sentences = [s.strip() for s in re.split(r'[.\n]', body) if len(s.strip()) > 5]
    summary = " / ".join(sentences[:2]) if sentences else "-"

    return {
        "제목":       email_data["subject"],
        "발신자":     email_data["sender"],
        "날짜":       email_data["date"],
        "분류":       category,
        "신뢰도":     confidence,
        "액션필요":   needs_action(full_text),
        "기한":       deadline or "-",
        "요약":       summary,
        "이메일":     ", ".join(info["emails"]),
        "금액":       ", ".join(info["amounts"]),
        "첨부PDF수":  len(email_data.get("pdf_paths", [])),
        "_full_text": full_text,   # 검색용 (UI에서만 사용)
    }
