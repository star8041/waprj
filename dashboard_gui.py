import streamlit as st
import pandas as pd
from datetime import date, datetime
import io
import platform
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ── 한글 폰트 설정 ────────────────────────────────────────────────────────────
def _set_korean_font():
    system = platform.system()
    if system == "Windows":
        candidates = ["Malgun Gothic", "맑은 고딕"]
    elif system == "Darwin":
        candidates = ["AppleGothic", "Apple SD Gothic Neo"]
    else:
        candidates = ["NanumGothic", "NanumBarunGothic", "UnDotum"]

    available = {f.name for f in fm.fontManager.ttflist}
    for font in candidates:
        if font in available:
            plt.rcParams["font.family"] = font
            plt.rcParams["axes.unicode_minus"] = False
            return
    # fallback: 첫 번째로 찾은 한글 지원 폰트
    for f in fm.fontManager.ttflist:
        if any(k in f.name for k in ["Gothic", "Nanum", "Malgun", "Apple", "Dotum"]):
            plt.rcParams["font.family"] = f.name
            plt.rcParams["axes.unicode_minus"] = False
            return

_set_korean_font()

# ── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="메일 분석 대시보드",
    page_icon="📬",
    layout="wide",
)

# ── 스타일 ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetric"] { background:#f8f9fa; border-radius:10px; padding:1rem; }
[data-testid="stMetricLabel"] { font-size:13px !important; }
.badge {
    display:inline-block; padding:2px 10px; border-radius:999px;
    font-size:12px; font-weight:500;
}
.badge-업무협조 { background:#E6F1FB; color:#0C447C; }
.badge-보고서   { background:#EAF3DE; color:#27500A; }
.badge-회의록   { background:#FAEEDA; color:#633806; }
.badge-공지     { background:#EEEDFE; color:#3C3489; }
.badge-기타     { background:#F1EFE8; color:#444441; }
.action-yes { color:#A32D2D; font-weight:600; }
.action-no  { color:#3B6D11; }
</style>
""", unsafe_allow_html=True)

# ── 기본 데이터 ──────────────────────────────────────────────────────────────
DEFAULT_CSV = """제목,발신자,분류,회신 필요 여부,기한
[보고서] 4월 서비스 데이터 분석 종합 보고서 초안입니다.,민석 <mhnkms8041@gmail.com>,보고서,회신 필요,2026-05-02
일정 변경 공지입니다.,민석 <mhnkms8041@gmail.com>,공지,회신 불필요,
참석자분들께 회의록 배포해드립니다.,민석 <mhnkms8041@gmail.com>,회의록,회신 불필요,
회의 결과 보고드립니다.,민석 <mhnkms8041@gmail.com>,보고서,회신 필요,2026-05-10
안내받은 바에 따라 협조 요청드립니다.,민석 <mhnkms8041@gmail.com>,업무협조,회신 불필요,2026-05-05
[업무협조] 데이터 검증 요청,윤여옥 <dudhrdl123@gmail.com>,업무협조,회신 필요,2026-05-03
Fwd: [업무협조] !! 기습메일 !! 중요한 내용입니다 필독바람,민석 <mhnkms8041@gmail.com>,업무협조,회신 불필요,2026-05-05
[업무협조] !! 기습메일 !! 중요한 내용입니다 필독바람,민석 <mhnkms8041@gmail.com>,업무협조,회신 불필요,
[유료화 안내] 노벨라 요금제 정책 & 10월 한 달 무료 제공,노벨라 <hello@mail.novela.so>,공지,회신 필요,2026-11-01
Gemini 앱의 중요한 업데이트,Google Gemini <google-gemini-noreply@google.com>,업무협조,회신 불필요,
[노벨라] 노벨라의 부분 유료화 안내 말씀을 전해드립니다.,노벨라 <hello@mail.novela.so>,업무협조,회신 필요,2026-08-12
Gemini에 오신 것을 환영합니다,Google Gemini <google-gemini-noreply@google.com>,공지,회신 필요,
노벨라 리뉴얼 안내 - 주요 변경 사항 한눈에 보기,노벨라 <hello@mail.novela.so>,공지,회신 필요,
노벨라 리뉴얼 D-5 오픈 일정 및 서비스 점검 안내,노벨라 <hello@mail.novela.so>,업무협조,회신 불필요,
6월 10일 서비스 장애에 대한 안내,OpenAI <noreply@tm.openai.com>,업무협조,회신 불필요,2026-06-10
노벨라 리뉴얼 안내: 6월 30일 새롭게 태어납니다.,노벨라 <hello@mail.novela.so>,업무협조,회신 불필요,
Android 기기에서 Google 설정을 완료하세요.,Google <no-reply@google.com>,공지,회신 불필요,
[계정 설정 안내] Google 파트너 사이트 이용자 활동 정보 관리,Google <ads-account-noreply@google.com>,업무협조,회신 불필요,
Android 기기에서 Google 설정을 완료하세요. (2),Google <no-reply@google.com>,공지,회신 불필요,
Finish setting up your new Google Account on your Galaxy A42 5G,Google <no-reply@google.com>,공지,회신 불필요,
"""

CAT_COLORS = {
    "업무협조": "#378ADD",
    "보고서":   "#639922",
    "회의록":   "#BA7517",
    "공지":     "#7F77DD",
    "기타":     "#888780",
}

TODAY = date.today()

# ── 데이터 파싱 ──────────────────────────────────────────────────────────────
def parse_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    required = {"제목", "발신자", "분류", "회신 필요 여부"}
    missing = required - set(df.columns)
    if missing:
        st.error(f"CSV에 필수 열이 없습니다: {missing}")
        st.stop()
    if "기한" not in df.columns:
        df["기한"] = pd.NaT
    df["기한"] = pd.to_datetime(df["기한"], errors="coerce")
    df["분류"] = df["분류"].fillna("기타")
    df["회신 필요 여부"] = df["회신 필요 여부"].fillna("회신 불필요")
    df["발신자_짧게"] = df["발신자"].str.replace(r"\s*<[^>]+>", "", regex=True).str.strip()
    df["마감임박"] = df["기한"].apply(
        lambda d: isinstance(d, (pd.Timestamp, datetime)) and
                  not pd.isnull(d) and 0 <= (d.date() - TODAY).days <= 7
    )
    return df

# ── 사이드바 ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📬 메일 대시보드")
    st.caption("CSV 파일을 업로드하면 분석이 시작됩니다.")

    uploaded = st.file_uploader("CSV 파일 업로드", type=["csv"])
    if uploaded:
        raw_df = pd.read_csv(uploaded)
        df = parse_df(raw_df)
    else:
        df = None

    st.divider()
    st.caption(f"오늘: {TODAY.strftime('%Y년 %m월 %d일')}")

# ── 메인 콘텐츠 ──────────────────────────────────────────────────────────────
st.title("📊 현황 요약")

if df is None:
    # CSV 미업로드 상태: 메트릭 빈 값 + 빈 테이블만 표시
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체 메일", "-")
    c2.metric("회신 필요", "-")
    c3.metric("기한 있음",  "-")
    c4.metric("마감 임박",  "-")

    st.divider()
    st.subheader("메일 목록")
    st.markdown("""
<table style="width:100%;border-collapse:collapse;font-size:13px;">
  <thead>
    <tr style="border-bottom:1.5px solid #ddd;color:#888;font-size:12px;">
      <th style="text-align:left;padding:8px 6px;width:42%">제목</th>
      <th style="text-align:left;padding:8px 6px;width:22%">발신자</th>
      <th style="text-align:left;padding:8px 6px;width:12%">분류</th>
      <th style="text-align:left;padding:8px 6px;width:12%">회신 필요 여부</th>
      <th style="text-align:left;padding:8px 6px;width:8%">기한</th>
    </tr>
  </thead>
  <tbody>
    <tr><td colspan="5" style="text-align:center;padding:2rem;color:#aaa;font-size:13px;">
      CSV 파일을 업로드하면 메일 목록이 표시됩니다.
    </td></tr>
  </tbody>
</table>""", unsafe_allow_html=True)
    st.stop()

# ── 현황 요약 메트릭 ──────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("전체 메일",  f"{len(df)}건")
c2.metric("회신 필요",  f"{int((df['회신 필요 여부']=='회신 필요').sum())}건",
          delta="확인 필요", delta_color="inverse")
c3.metric("기한 있음",  f"{int(df['기한'].notna().sum())}건")
c4.metric("마감 임박",  f"{int(df['마감임박'].sum())}건",
          delta="7일 이내" if df['마감임박'].sum() else None,
          delta_color="inverse")

st.divider()

# ── 분류별 현황 차트 ───────────────────────────────────────────────────────────
st.subheader("분류별 현황")

col_chart, col_action = st.columns([3, 2])

with col_chart:
    cat_counts = df.groupby("분류").size().reset_index(name="건수")
    cats_ordered = cat_counts.sort_values("건수", ascending=False)

    fig, ax = plt.subplots(figsize=(6, 3.2))
    bar_colors = [CAT_COLORS.get(c, "#888780") for c in cats_ordered["분류"]]
    bars = ax.barh(cats_ordered["분류"], cats_ordered["건수"],
                   color=bar_colors, height=0.55, edgecolor="white")
    for bar, val in zip(bars, cats_ordered["건수"]):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                f"{val}건", va="center", ha="left", fontsize=11)
    ax.set_xlabel("메일 수", fontsize=10)
    ax.invert_yaxis()
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(left=False, labelsize=11)
    ax.set_xlim(0, cats_ordered["건수"].max() + 3)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

with col_action:
    st.markdown("##### 회신 필요 현황")
    action_by_cat = (
        df[df["회신 필요 여부"] == "회신 필요"]
        .groupby("분류")
        .size()
        .reset_index(name="회신필요")
        .sort_values("회신필요", ascending=False)
    )
    if action_by_cat.empty:
        st.success("회신 필요 메일이 없습니다!")
    else:
        for _, row in action_by_cat.iterrows():
            pct = int(row["회신필요"] / len(df) * 100)
            st.markdown(
                f'<span class="badge badge-{row["분류"]}">{row["분류"]}</span> '
                f'&nbsp; **{row["회신필요"]}건** <span style="color:#888;font-size:12px">({pct}%)</span>',
                unsafe_allow_html=True,
            )
            st.progress(pct / 100)

st.divider()

# ── 메일 목록 테이블 ───────────────────────────────────────────────────────────
st.subheader(f"메일 목록  ·  {len(df)}건")

# ── 1행: 키워드 검색 + 정렬 기준 ─────────────────────────────────────────────
col_search, col_sort = st.columns([3, 1])
search   = col_search.text_input("제목/발신자로 검색", placeholder="키워드를 입력하세요...")
sort_col = col_sort.selectbox("정렬 기준", ["기한", "분류", "회신 필요 여부", "제목"])

# ── 2행: 카테고리 선택 ────────────────────────────────────────────────────────
all_cats = sorted(df["분류"].unique().tolist())
selected_cats = []
cat_check_cols = st.columns([1] * len(all_cats) + [4])  # 나머지 공간 여백
for i, cat in enumerate(all_cats):
    cnt = int((df["분류"] == cat).sum())
    if cat_check_cols[i].checkbox(f"{cat} ({cnt}건)", value=True, key=f"cat_{cat}"):
        selected_cats.append(cat)

# ── 3행: 토글 두 개 ───────────────────────────────────────────────────────────
col_t1, col_t2, _ = st.columns([1,1,6])
action_only = col_t1.toggle("회신 필요한 메일만 보기", value=False)
near_only   = col_t2.toggle("마감 임박만 보기 (7일)", value=False)

# 필터 적용
filtered = df[df["분류"].isin(selected_cats)]
if action_only:
    filtered = filtered[filtered["회신 필요 여부"] == "회신 필요"]
if near_only:
    filtered = filtered[filtered["마감임박"] == True]
if search:
    mask = (
        filtered["제목"].str.contains(search, case=False, na=False) |
        filtered["발신자"].str.contains(search, case=False, na=False)
    )
    filtered = filtered[mask]
filtered = filtered.sort_values(sort_col, ascending=(sort_col == "기한"), na_position="last")

st.caption(f"필터 결과: {len(filtered)}건")

def render_row(row):
    deadline = row["기한"]
    if pd.isnull(deadline):
        dl_str, dl_style = "-", ""
    else:
        dl_str = deadline.strftime("%m/%d")
        dl_style = "color:#A32D2D;font-weight:600;" if row["마감임박"] else ""
    action_style = "action-yes" if row["회신 필요 여부"] == "회신 필요" else "action-no"
    action_icon  = "● 필요" if row["회신 필요 여부"] == "회신 필요" else "✓"
    return (
        f'<tr>'
        f'<td style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{row["제목"]}</td>'
        f'<td style="color:#555;font-size:12px">{row["발신자_짧게"]}</td>'
        f'<td><span class="badge badge-{row["분류"]}">{row["분류"]}</span></td>'
        f'<td><span class="{action_style}">{action_icon}</span></td>'
        f'<td style="{dl_style}">{dl_str}</td>'
        f'</tr>'
    )

table_html = """
<table style="width:100%;border-collapse:collapse;font-size:13px;">
  <thead>
    <tr style="border-bottom:1.5px solid #ddd;color:#888;font-size:12px;">
      <th style="text-align:left;padding:8px 6px;width:42%">제목</th>
      <th style="text-align:left;padding:8px 6px;width:22%">발신자</th>
      <th style="text-align:left;padding:8px 6px;width:12%">분류</th>
      <th style="text-align:left;padding:8px 6px;width:12%">회신 필요 여부</th>
      <th style="text-align:left;padding:8px 6px;width:8%">기한</th>
    </tr>
  </thead>
  <tbody>
"""
for _, row in filtered.iterrows():
    table_html += render_row(row)
table_html += "</tbody></table>"
st.markdown(table_html, unsafe_allow_html=True)

st.divider()

# ── CSV 다운로드 ───────────────────────────────────────────────────────────────
dl_df = filtered[["제목", "발신자", "분류", "회신 필요 여부", "기한"]].copy()
dl_df["기한"] = dl_df["기한"].dt.strftime("%Y-%m-%d").fillna("-")
st.download_button(
    "📥 현재 목록 CSV로 저장",
    data=dl_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="filtered_emails.csv",
    mime="text/csv",
)
