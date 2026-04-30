import imaplib
import email
import os
from email.header import decode_header
from config import IMAP_SERVER, DOWNLOAD_DIR


def connect_mail(email_addr: str, password: str):
    """Gmail IMAP 연결"""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(email_addr, password)
    return mail


def decode_str(s) -> str:
    """메일 헤더 디코딩 (한글 포함)"""
    if s is None:
        return ""
    result = ""
    for part, enc in decode_header(s):
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="ignore")
        else:
            result += str(part)
    return result


def fetch_emails(mail, max_count: int = 50) -> list[dict]:
    """
    받은편지함에서 메일 가져오기
    - 최신 max_count 건만 처리
    - PDF 첨부파일 자동 다운로드
    """
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    mail.select("inbox")

    _, msg_nums = mail.search(None, "ALL")
    all_nums = msg_nums[0].split()
    recent_nums = all_nums[::-1][:max_count]  # 최신순

    results = []
    for num in recent_nums:
        _, data = mail.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(data[0][1])

        subject = decode_str(msg["Subject"])
        sender  = decode_str(msg["From"])
        date    = msg.get("Date", "")
        body_text = ""
        pdfs = []

        for part in msg.walk():
            content_type = part.get_content_type()
            disposition  = str(part.get("Content-Disposition", ""))

            # 본문 텍스트 수집
            if content_type == "text/plain" and "attachment" not in disposition:
                try:
                    body_text = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except Exception:
                    pass

            # PDF 첨부파일 저장
            if "attachment" in disposition and part.get_filename():
                filename = decode_str(part.get_filename())
                if filename.lower().endswith(".pdf"):
                    filepath = os.path.join(DOWNLOAD_DIR, filename)
                    with open(filepath, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    pdfs.append(filepath)

        results.append({
            "subject":   subject,
            "sender":    sender,
            "date":      date,
            "body":      body_text,
            "pdf_paths": pdfs,
        })

    return results
