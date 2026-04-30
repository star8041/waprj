import pdfplumber


def extract_text(filepath: str) -> str:
    """PDF 한 파일에서 전체 텍스트 추출"""
    text = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        text = f"[PDF 추출 실패: {e}]"
    return text.strip()


def extract_all(pdf_paths: list[str]) -> dict[str, str]:
    """여러 PDF 처리 → {파일명: 텍스트} 딕셔너리 반환"""
    import os
    return {
        os.path.basename(path): extract_text(path)
        for path in pdf_paths
    }
