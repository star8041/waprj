"""
업무 메일 자동 분류 시스템
실행: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import os

from email_fetcher import connect_mail, fetch_emails
from pdf_processor import extract_all
from classifier import analyze

# ─────────────────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="업무 메일 분류기",
    page_icon="📧",
    layout="wide",
)

st.markdown("""
<style>
    .metric-card {
        background: #f8fafc;
        border-radius: 12px;
        padding: 16px;
        border-left: 4px solid #3b82f6;
    }
    .urgent { border-left-color: #ef4444; background: #fef2f2; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# 세션 상태 초기화
# ─────────────────────────────────────────────────────────
if "analyzed" not in st.session_state:
    st.session_state.analyzed = []   # 분석 결과 리스트
if "df" not in st.session_state:
    st.session_state.df = None


# ─────────────────────────────────────────────────────────
# 사이드바 - 로그인 & 불러오기
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📧 메일 분류기")
    st.caption("Gmail 앱 비밀번호로 접속")

    email_input    = st.text_input("Gmail 주소", placeholder="you@gmail.com")
    password_input = st.text_input("앱 비밀번호", type="password",
                                   help="Google 계정 → 보안 → 앱 비밀번호 생성")
    max_count      = st.slider("최근 메일 수", 10, 100, 50, step=10)
    fetch_btn      = st.button("📥 메일 불러오기", type="primary", use_container_width=True)

    st.divider()
    st.caption("앱 비밀번호 발급: [Google 계정 설정](https://myaccount.google.com/apppasswords)")


# ─────────────────────────────────────────────────────────
# 메일 수집 & 분석
# ─────────────────────────────────────────────────────────
if fetch_btn:
    if not email_input or not password_input:
        st.sidebar.error("이메일과 비밀번호를 입력하세요.")
    else:
        progress = st.progress(0, text="메일함 접속 중...")
        try:
            mail = connect_mail(email_input, password_input)
            progress.progress(20, text="메일 목록 불러오는 중...")

            raw_emails = fetch_emails(mail, max_count=max_count)
            mail.logout()

            analyzed = []
            for i, em in enumerate(raw_emails):
                progress.progress(
                    20 + int(80 * i / len(raw_emails)),
                    text=f"분석 중... ({i+1}/{len(raw_emails)})"
                )
                pdf_texts = extract_all(em["pdf_paths"])
                result = analyze(em, pdf_texts)
                analyzed.append(result)

            st.session_state.analyzed = analyzed
            st.session_state.df = pd.DataFrame([
                {k: v for k, v in r.items() if k != "_full_text"}
                for r in analyzed
            ])
            progress.progress(100, text="완료!")
            st.success(f"✅ {len(analyzed)}건 분석 완료")

        except Exception as e:
            progress.empty()
            st.sidebar.error(f"오류: {e}")


# ─────────────────────────────────────────────────────────
# 메인 대시보드
# ─────────────────────────────────────────────────────────
if st.session_state.df is not None:
    df = st.session_state.df
    analyzed = st.session_state.analyzed

    # ── 요약 카드 ──────────────────────────────────────────
    st.subheader("📊 현황 요약")
    c1, c2, c3, c4 = st.columns(4)

    action_count   = int(df["액션필요"].sum())
    deadline_count = int((df["기한"] != "-").sum())
    pdf_count      = int(df["첨부PDF수"].sum())

    c1.metric("🔴 액션 필요", f"{action_count}건",
              help="내가 확인/처리/회신해야 하는 메일")
    c2.metric("📧 전체 메일", f"{len(df)}건")
    c3.metric("⏰ 기한 있음", f"{deadline_count}건")
    c4.metric("📎 PDF 첨부", f"{pdf_count}건")

    st.divider()

    # ── 탭 ────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📋 전체 목록", "🔴 액션 필요", "🔍 내용 검색"])

    # ── 탭1: 전체 목록 ────────────────────────────────────
    with tab1:
        col_a, col_b = st.columns([2, 1])
        with col_a:
            cat_filter = st.multiselect(
                "분류 필터",
                ["업무협조", "보고서", "회의록", "공지", "기타"],
                default=["업무협조", "보고서", "회의록", "공지", "기타"],
            )
        with col_b:
            only_action = st.checkbox("액션 필요만 보기")

        show_df = df[df["분류"].isin(cat_filter)].copy()
        if only_action:
            show_df = show_df[show_df["액션필요"] == True]

        # 표시용 가공
        show_df["액션"] = show_df["액션필요"].apply(lambda x: "🔴 필요" if x else "✅")
        show_df["신뢰도"] = show_df["신뢰도"].apply(lambda x: f"{int(x*100)}%")

        display_cols = ["제목", "발신자", "분류", "신뢰도", "액션", "기한", "요약"]
        st.dataframe(
            show_df[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "요약": st.column_config.TextColumn(width="large"),
            }
        )

        # CSV 다운로드
        csv_data = show_df[display_cols].to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "📥 CSV로 저장",
            data=csv_data,
            file_name="mail_results.csv",
            mime="text/csv",
        )

    # ── 탭2: 액션 필요 ────────────────────────────────────
    with tab2:
        action_items = [r for r in analyzed if r["액션필요"]]

        if not action_items:
            st.info("액션이 필요한 메일이 없습니다. 🎉")
        else:
            st.caption(f"총 {len(action_items)}건 — 지금 처리해야 할 메일들")
            for item in action_items:
                deadline_badge = f"⏰ {item['기한']}" if item["기한"] != "-" else ""
                with st.expander(f"🔴 {item['제목']}  {deadline_badge}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**발신자:** {item['발신자']}")
                        st.write(f"**날짜:** {item['날짜']}")
                        st.write(f"**분류:** {item['분류']}")
                    with col2:
                        if item["금액"]:
                            st.write(f"**관련 금액:** {item['금액']}")
                        if item["이메일"]:
                            st.write(f"**연락처 이메일:** {item['이메일']}")
                    if item["요약"] != "-":
                        st.info(f"💬 {item['요약']}")

    # ── 탭3: 내용 검색 ────────────────────────────────────
    with tab3:
        st.caption("제목, 본문, PDF 내용까지 전부 검색합니다")
        query = st.text_input("🔍 검색어", placeholder="예: 매출 분석, 시스템 점검, 홍길동...")

        if query:
            hits = [r for r in analyzed if query in r["_full_text"]]
            if hits:
                st.success(f"'{query}' 검색 결과: {len(hits)}건")
                for item in hits:
                    with st.expander(f"📧 {item['제목']} [{item['분류']}]"):
                        st.write(f"**발신자:** {item['발신자']} | **날짜:** {item['날짜']}")
                        # 검색어 주변 미리보기
                        idx = item["_full_text"].find(query)
                        if idx >= 0:
                            snippet = item["_full_text"][max(0, idx-60): idx+120]
                            highlighted = snippet.replace(query, f"**`{query}`**")
                            st.markdown(f"> ...{highlighted}...")
            else:
                st.warning(f"'{query}'에 대한 결과가 없습니다.")

# ─────────────────────────────────────────────────────────
# 비어있을 때 가이드
# ─────────────────────────────────────────────────────────
else:
    st.title("📧 업무 메일 자동 분류 시스템")
    st.markdown("""
    왼쪽에서 **Gmail 정보를 입력**하고 메일을 불러오면:

    | 기능 | 설명 |
    |------|------|
    | 🏷️ **자동 분류** | 업무협조 / 보고서 / 회의록 / 공지 |
    | 🔴 **액션 필요 감지** | 내가 확인·처리해야 할 메일만 모아보기 |
    | ⏰ **기한 감지** | "금주 내", "3일 내" 등 자동 추출 |
    | 🔍 **전문 검색** | PDF 내용까지 포함해서 키워드 검색 |
    | 📥 **CSV 저장** | 결과 한 번에 내보내기 |
    """)

    st.info("💡 Gmail 앱 비밀번호가 필요합니다. [발급 방법 →](https://support.google.com/accounts/answer/185833)")
