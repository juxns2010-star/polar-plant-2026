import io
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────────────────────────────
# 한글 폰트 + 커스텀 UI CSS
# ─────────────────────────────────────────────────────────────────────
st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

html, body, [class*="css"] {
   font-family: 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
}

/* ── 페이지 상단 배너 ─────────────────────────────────────────── */
.banner {
   background: linear-gradient(135deg, #0d4f4f 0%, #1d3557 50%, #2d6a4f 100%);
   border-radius: 16px;
   padding: 20px 24px;
   color: #ffffff;
   margin-bottom: 18px;
   box-shadow: 0 4px 20px rgba(13, 79, 79, 0.25);
}
.banner h1 {
   font-size: 1.45em;
   font-weight: 700;
   margin: 0 0 6px 0;
   letter-spacing: -0.3px;
}
.banner .subtitle {
   font-size: 0.92em;
   font-weight: 300;
   opacity: 0.88;
   margin: 0;
}

/* ── 섹션 헤더 ────────────────────────────────────────────────── */
.section-title {
   font-size: 1.15em;
   font-weight: 600;
   color: #0d4f4f;
   padding: 10px 0 4px 0;
   border-bottom: 2px solid #2d6a4f;
   margin-bottom: 10px;
   letter-spacing: -0.2px;
}
.section-sub {
   font-size: 0.85em;
   color: #5a6c6c;
   font-weight: 400;
   margin-top: -6px;
   margin-bottom: 10px;
}

/* ── info / warning 박스 ──────────────────────────────────────── */
.banner-info {
   background: #e8f4f8;
   border-left: 4px solid #2980b9;
   border-radius: 6px;
   padding: 10px 14px;
   margin: 8px 0;
   font-size: 0.9em;
   color: #1a4a5e;
}
.banner-warn {
   background: #fef9e7;
   border-left: 4px solid #e0a030;
   border-radius: 6px;
   padding: 10px 14px;
   margin: 8px 0;
   font-size: 0.9em;
   color: #5a4010;
}

/* ── 요약 카드 박스 ───────────────────────────────────────────── */
.card-box {
   background: #f7faf9;
   border: 1px solid #c8ddd2;
   border-radius: 10px;
   padding: 10px 14px;
   margin: 4px 0;
   text-align: center;
}
.card-box .card-label {
   font-size: 0.78em;
   color: #5a6c6c;
   font-weight: 400;
   margin-bottom: 3px;
}
.card-box .card-value {
   font-size: 1.15em;
   font-weight: 700;
   color: #0d4f4f;
}
.card-box .card-delta {
   font-size: 0.72em;
   color: #7a8a8a;
   margin-top: 2px;
}

/* ── 사이드바 스타일 ───────────────────────────────────────────── */
section[data-testid="stSidebar"] {
   background: linear-gradient(180deg, #f0f5f3 0%, #ffffff 100%);
   border-right: 2px solid #c8ddd2;
}
.sidebar-logo {
   background: linear-gradient(135deg, #0d4f4f 0%, #2d6a4f 100%);
   border-radius: 10px;
   padding: 12px 14px;
   margin-bottom: 14px;
   color: #ffffff;
}
.sidebar-logo p {
   margin: 0;
   font-size: 0.88em;
   font-weight: 400;
   opacity: 0.9;
}

/* ── 컬럼 박스 ────────────────────────────────────────────────── */
.col-card {
   background: #f7faf9;
   border: 1px solid #d4e4d8;
   border-radius: 10px;
   padding: 10px 12px;
   height: 100%;
}

/* ── 태그 뱃지 ────────────────────────────────────────────────── */
.tag-badge {
   display: inline-block;
   background: #e07a5f;
   color: #ffffff;
   font-size: 0.7em;
   font-weight: 600;
   padding: 2px 8px;
   border-radius: 20px;
   letter-spacing: 0.3px;
}
.tag-badge.blue { background: #2980b9; }
.tag-badge.green { background: #27ae60; }
.tag-badge.orange { background: #e67e22; }
.tag-badge.purple { background: #8e44ad; }

/* ── 다운로드 버튼 강조 ──────────────────────────────────────── */
.stButton > button[data-baseweb="download"] {
   background: #0d4f4f;
   color: #ffffff;
   border-radius: 8px;
   font-weight: 600;
}
.stButton > button[data-baseweb="download"]:hover {
   background: #1a6b5e;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# 페이지 상단 배너
# ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="banner">
  <h1>🌱 극지식물 생육 차이 핵심 요인 분석 대시보드</h1>
  <p class="subtitle">
    길이보다 <strong style="color:#a8e6cf;">'잎 수'</strong>가 생중량을 결정한다 —
    같은 스마트팜 환경에서 자란 개체 사이의 큰 생육 차이를 함께 파헤쳐 봅시다
  </p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# 열 이름 표준화 (std_cols) — 기존과 완전히 동일
# ─────────────────────────────────────────────────────────────────────
def std_cols(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rename = {}
    for c in df.columns:
        k = c.lower().replace(" ", "")
        if k in ("time", "categories", "시간", "날짜", "datetime", "date"):
            rename[c] = "time"
        elif k in ("temperature", "온도"):
            rename[c] = "temperature"
        elif k in ("humidity", "습도"):
            rename[c] = "humidity"
        elif k == "ph":
            rename[c] = "ph"
        elif k == "ec":
            rename[c] = "ec"
        elif "생중량" in k:
            rename[c] = "생중량"
        elif "잎" in k:
            rename[c] = "잎 수"
        elif "지상부" in k and "길이" in k:
            rename[c] = "지상부 길이"
        elif "지하부" in k and "길이" in k:
            rename[c] = "지하부 길이"
        elif "지상부" in k and ("질량" in k or "무게" in k):
            rename[c] = "지상부 질량"
        elif "지하부" in k and ("질량" in k or "무게" in k):
            rename[c] = "지하부 질량"
        elif "개체" in k:
            rename[c] = "개체번호"
    df = df.rename(columns=rename)
    for c in df.columns:
        if c in ("time", "개체번호"):
            continue
        if not pd.api.types.is_numeric_dtype(df[c]):
            num = pd.to_numeric(
                df[c].astype(str).str.replace(",", "")
                .str.extract(r"(-?\d+\.?\d*)")[0], errors="coerce"
            )
            if num.notna().mean() >= 0.5:
                df[c] = num
    if "생중량" not in df.columns and {"지상부 질량", "지하부 질량"} <= set(df.columns):
        df["생중량"] = df["지상부 질량"] + df["지하부 질량"]
    if "time" in df.columns:
        t = df["time"].astype(str).str.strip()
        parsed = pd.to_datetime(t, errors="coerce", format="mixed")
        bad = parsed.isna() & t.str.match(r"^\d{8}_\d{1,2}$")
        if bad.any():
            parts = t[bad].str.split("_", expand=True)
            parsed[bad] = (
                pd.to_datetime(parts[0], format="%Y%m%d")
                + pd.to_timedelta(parts[1].astype(int), unit="h")
            )
        df["time"] = parsed
    return df


# ─────────────────────────────────────────────────────────────────────
# CSV 읽기 (인코딩 이중 시도) — 기존과 동일
# ─────────────────────────────────────────────────────────────────────
@st.cache_data
def read_csv(file):
    data = file.getvalue()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(io.BytesIO(data), encoding=enc)
        except Exception:
            pass
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────
# 학교명 추출 — 기존과 동일
# ─────────────────────────────────────────────────────────────────────
def school_name(filename):
    if not filename:
        return "우리 학교"
    base = os.path.splitext(filename)[0]
    for sep in ("_", "."):
        if sep in base:
            candidate = base.split(sep)[0]
            if len(candidate) >= 2:
                return candidate
    return base[:6] if len(base) >= 2 else base


# ─────────────────────────────────────────────────────────────────────
# CSV 다운로드 도우미 — 기존과 동일
# ─────────────────────────────────────────────────────────────────────
def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


# ─────────────────────────────────────────────────────────────────────
# 공통: 추세선 있는 산점도 — 기존과 동일
# ─────────────────────────────────────────────────────────────────────
def scatter_with_fit(x, y, xlabel, ylabel, title):
    xy = pd.DataFrame({xlabel: x, ylabel: y}).dropna()
    if len(xy) < 2:
        return None
    xvals = xy.iloc[:, 0].values
    yvals = xy.iloc[:, 1].values
    r = np.corrcoef(xvals, yvals)[0, 1]
    slope, intercept = np.polyfit(xvals, yvals, 1)
    fit_x = np.linspace(xvals.min(), xvals.max(), 100)
    fit_y = slope * fit_x + intercept
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xvals, y=yvals, mode="markers",
        marker=dict(size=8, color="#27ae60", opacity=0.75),
        hovertemplate=f"<b>{xlabel}</b>: %{{x:.1f}}<br><b>{ylabel}</b>: %{{y:.2f}}<extra></extra>",
        name="데이터",
    ))
    fig.add_trace(go.Scatter(
        x=fit_x, y=fit_y, mode="lines",
        line=dict(color="#e07a5f", width=2.5, dash="dash"),
        name=f"추세선  r = {r:.3f}",
        hoverinfo="skip",
    ))
    fig.update_layout(
        title=dict(text=f"{title}    r = {r:.3f}", x=0.5, font=dict(size=13, color="#0d4f4f")),
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        template="plotly_white",
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
        height=340,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="극지식물 생육 차이 분석 대시보드", layout="wide")

# ─────────────────────────────────────────────────────────────────────
# ── 사이드바 ────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
      <p style="font-size:1.05em; font-weight:600; margin-bottom:2px;">🌿 데이터 업로드</p>
      <p>극지식물 생육 분석 도구</p>
    </div>
    """, unsafe_allow_html=True)

    st.header("📁 CSV 파일")
    env_file = st.file_uploader("🌡️ 환경 데이터 CSV", type="csv")
    growth_file = st.file_uploader("🌱 생육 결과 데이터 CSV", type="csv")

    # 업로드 상태 배지
    if env_file and growth_file:
        st.markdown('<span class="tag-badge green">양 파일 업로드 완료</span>', unsafe_allow_html=True)
    elif env_file or growth_file:
        st.markdown('<span class="tag-badge blue">1개 파일 업로드됨</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="tag-badge">파일 대기 중</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🌱 생육 측정 항목")
    growth_cols_raw = []
    if growth_file is not None:
        gtmp = read_csv(growth_file)
        gtmp = std_cols(gtmp)
        candidates = [
            "잎 수", "지상부 길이", "지하부 길이",
            "생중량", "지상부 질량", "지하부 질량",
        ]
        growth_cols_raw = [c for c in candidates if c in gtmp.columns]

    selected_growth = st.multiselect(
        "분포·CV 비교에 사용할 항목",
        growth_cols_raw,
        default=[c for c in growth_cols_raw if c in ("잎 수", "지상부 길이", "지하부 길이", "생중량")],
    )

    if growth_cols_raw:
        st.success(f"감지됨: {', '.join(growth_cols_raw)}")
    else:
        st.info("생육 CSV를 올리면 항목이 자동 감지돼요 📊")

    st.markdown("---")
    env_name = school_name(env_file.name if env_file else None)
    growth_name = school_name(growth_file.name if growth_file else None)
    st.caption(f"🏫 환경: **{env_name}**  ·  생육: **{growth_name}**"
                if (env_file or growth_file) else "아직 파일이 없어요.")

    st.markdown("---")
    st.caption("💡 팁: 파일명 앞부분이 학교명으로 자동 인식돼요.")
    st.caption("📌 utf-8-sig → cp949 순서로 읽어서 인코딩 오류를 방지해요.")
    st.caption("⚠️ 열 이름이 달라도 std_cols가 자동으로 Standardization해요.")


# ─────────────────────────────────────────────────────────────────────
# ── 데이터 로딩 ────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────
env_df = pd.DataFrame()
growth_df = pd.DataFrame()

if env_file is not None:
    with st.spinner("🌡️ 환경 데이터 읽는 중…"):
        env_df = std_cols(read_csv(env_file))
if growth_file is not None:
    with st.spinner("🌱 생육 데이터 읽는 중…"):
        growth_df = std_cols(read_csv(growth_file))

st.sidebar.markdown("---")
if env_file or growth_file:
    st.sidebar.success("데이터 로딩 완료 ✅")


# ═══════════════════════════════════════════════════════════════════════
# ── 탭 1: 스마트팜 환경 및 개체별 생육 분포 ───────────────────────
# ═══════════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs([
    "🌡️ 스마트팜 환경 및 개체별 생육 분포",
    "🔗 생육 변수 간 상관관계 및 가설 검증",
    "🎯 생중량 상·하위 그룹 비교 및 예측 시뮬레이터",
])

with tab1:
    try:
        if env_file is None and growth_file is None:
            st.markdown("""
            <div class="banner-info">
              <strong>☝️ 아직 파일이 없어요.</strong><br>
              사이드바에서 <em>환경 CSV</em>와 <em>생육 CSV</em>를 각각 올려주세요.
              업로드 즉시 대시보드가 활성화돼요 🚀
            </div>
            """, unsafe_allow_html=True)
        else:
            env_ready = not env_df.empty
            growth_ready = not growth_df.empty

            # ── 환경 데이터 섹션 ──────────────────────────────────────
            if env_ready:
                st.markdown('<div class="section-title">🌡️ 스마트팜 환경 지표 요약</div>', unsafe_allow_html=True)

                env_cols_avail = [c for c in ["temperature", "humidity", "ph", "ec"] if c in env_df.columns]

                if env_cols_avail:
                    env_means = {}
                    env_stds = {}
                    env_mins = {}
                    env_maxs = {}
                    for c in env_cols_avail:
                        s = env_df[c].dropna()
                        env_means[c] = s.mean() if len(s) > 0 else float("nan")
                        env_stds[c] = s.std() if len(s) > 0 else float("nan")
                        env_mins[c] = s.min() if len(s) > 0 else float("nan")
                        env_maxs[c] = s.max() if len(s) > 0 else float("nan")

                    # 요약 카드 그리드
                    c1, c2, c3, c4 = st.columns(4)
                    for col, cname, label, unit, color in [
                        (c1, "temperature", "평균 온도", "°C", "#e74c3c"),
                        (c2, "humidity", "평균 습도", "%", "#3498db"),
                        (c3, "ec", "평균 EC", "mS/cm", "#f39c12"),
                        (c4, "ph", "평균 pH", "—", "#27ae60"),
                    ]:
                        if cname in env_cols_avail:
                            m = env_means[cname]
                            sd = env_stds[cname]
                            mn = env_mins[cname]
                            mx = env_maxs[cname]
                            col.markdown(f"""
                            <div class="col-card">
                              <div class="card-label">{label}</div>
                              <div class="card-value" style="color:{color}">
                                {m:.1f}{unit}
                              </div>
                              <div class="card-delta">
                                ±{sd:.1f}  ·  범위: {mn:.1f} ~ {mx:.1f}{unit if unit != '—' else ''}
                              </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            col.markdown("""
                            <div class="col-card">
                              <div class="card-label">데이터 없음</div>
                            </div>
                            """, unsafe_allow_html=True)

                    # 시계열 그래프
                    st.markdown('<div class="section-title">📅 날짜별 환경 시계열</div>', unsafe_allow_html=True)
                    if env_cols_avail:
                        n_env = len(env_cols_avail)
                        n_rows = (n_env + 1) // 2
                        fig_env = make_subplots(
                            rows=n_rows, cols=2,
                            subplot_titles=env_cols_avail,
                            vertical_spacing=0.12,
                        )
                        env_colors = {
                            "temperature": "#e74c3c",
                            "humidity": "#3498db",
                            "ph": "#27ae60",
                            "ec": "#f39c12",
                        }
                        for j, cname in enumerate(env_cols_avail):
                            s = env_df[["time", cname]].dropna()
                            if s.empty:
                                continue
                            row = j // 2 + 1
                            col = j % 2 + 1
                            fig_env.add_trace(
                                go.Scatter(
                                    x=s["time"], y=s[cname],
                                    mode="lines",
                                    name=cname,
                                    line=dict(color=env_colors.get(cname, "#1f77b4"), width=1.8),
                                    hovertemplate=(
                                        f"<b>{cname}</b><br>"
                                        f"%{{x|%Y-%m-%d %H:%M}}<br>값: %{{y:.2f}}<extra></extra>"
                                    ),
                                ),
                                row=row, col=col,
                            )
                        fig_env.update_layout(
                            title=dict(text="📈 환경 지표 시계열", x=0.5,
                                       font=dict(size=13, color="#0d4f4f")),
                            template="plotly_white",
                            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                            height=240 + 150 * (n_rows - 1),
                            margin=dict(l=40, r=20, t=40, b=28),
                        )
                        st.plotly_chart(fig_env, width="stretch")
                    else:
                        st.info("⚠️ 환경 CSV에 온도·습도·EC·pH 중 인식할 수 있는 열이 없어요.")
                else:
                    st.info("⚠️ 환경 CSV에 인식할 수 있는 열(온도, 습도, EC, pH)이 하나도 없어요.")

            # ── 개체별 생중량 막대그래프 ───────────────────────────────
            if growth_ready:
                st.markdown('<div class="section-title">🌱 개체별 생중량 분포</div>', unsafe_allow_html=True)
                if "생중량" in growth_df.columns:
                    g_sorted = growth_df.sort_values("생중량", ascending=False).reset_index(drop=True)
                    n = len(g_sorted)
                    if n > 0:
                        top_n = max(1, n // 4)
                        bottom_n = max(1, n // 4)
                        colors = []
                        for i in range(n):
                            if i < top_n:
                                colors.append("#e74c3c")
                            elif i >= n - bottom_n:
                                colors.append("#27ae60")
                            else:
                                colors.append("#b0b8b0")
                        fig_bar = go.Figure()
                        fig_bar.add_trace(go.Bar(
                            x=[str(v) for v in g_sorted["개체번호"].values],
                            y=g_sorted["생중량"].values,
                            marker_color=colors,
                            hovertemplate=(
                                "<b>개체 %{x}</b><br>생중량: %{y:.2f} g<extra></extra>"
                            ),
                        ))
                        fig_bar.add_annotation(
                            x=top_n - 0.5, y=g_sorted["생중량"].iloc[top_n - 1],
                            text="⬆ 상위 25%", showarrow=False,
                            font=dict(size=11, color="#e74c3c", weight="bold"),
                            yshift=8,
                        )
                        fig_bar.add_annotation(
                            x=n - bottom_n - 0.5, y=g_sorted["생중량"].iloc[n - bottom_n],
                            text="⬇ 하위 25%", showarrow=False,
                            font=dict(size=11, color="#27ae60", weight="bold"),
                            yshift=8,
                        )
                        fig_bar.update_layout(
                            title=dict(text="🌱 개체별 생중량 (상위 빨강 · 하위 초록)",
                                       x=0.5, font=dict(size=13, color="#0d4f4f")),
                            template="plotly_white",
                            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                            xaxis_title="개체",
                            yaxis_title="생중량 (g)",
                            height=360,
                            margin=dict(l=40, r=20, t=50, b=40),
                        )
                        st.plotly_chart(fig_bar, width="stretch")
                    else:
                        st.info("⚠️ 생중량 값이 있는 개체가 없어요.")
                else:
                    st.info("⚠️ 생육 CSV에 '생중량' 열이 없어요. (지상부+지하부 질량으로 합성되었을 수 있어요.)")

            # ── 생육 측정 항목 분포 & CV 비교 ─────────────────────────
            if growth_ready and selected_growth:
                st.markdown('<div class="section-title">📋 생육 측정 항목별 분포 및 변동계수(CV)</div>', unsafe_allow_html=True)
                dist_rows = []
                for sname in selected_growth:
                    if sname not in growth_df.columns:
                        continue
                    s = growth_df[sname].dropna()
                    if len(s) < 2:
                        st.info(f"⚠️ '{sname}': 값이 충분하지 않아요.")
                        continue
                    mean_v = s.mean()
                    std_v = s.std()
                    cv_v = (std_v / mean_v * 100) if mean_v != 0 else float("nan")
                    unit = ""
                    if sname == "잎 수":
                        unit = "장"
                    elif sname in ("지상부 길이", "지하부 길이"):
                        unit = "mm"
                    elif sname in ("생중량", "지상부 질량", "지하부 질량"):
                        unit = "g"
                    dist_rows.append({
                        "측정 항목": f"{sname} ({unit})",
                        "개체 수": len(s),
                        "평균": round(mean_v, 2),
                        "표준편차 (SD)": round(std_v, 2),
                        "변동계수 (CV)": f"{cv_v:.1f}%" if not np.isnan(cv_v) else "—",
                        "최솟값": round(s.min(), 2),
                        "최댓값": round(s.max(), 2),
                    })
                if dist_rows:
                    df_dist = pd.DataFrame(dist_rows)
                    st.caption(
                        "💡 변동계수(CV) = (표준편차 ÷ 평균) × 100%. "
                        "값이 클수록 개체 간 차이가 크다는 뜻이에요. 평균이 0이면 CV는 표시하지 않아요."
                    )
                    st.dataframe(df_dist, width="stretch")
                    st.download_button(
                        "📥 CV 비교 표 다운로드 (CSV)",
                        csv_bytes(df_dist),
                        "생육_CV_비교표.csv",
                        "text/csv",
                        key="tab1_cv_dl",
                    )
            elif growth_ready:
                st.info("☝️ 사이드바에서 분포·CV 비교에 사용할 생육 항목을 골라주세요.")

    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")


# ═══════════════════════════════════════════════════════════════════════
# ── 탭 2: 상관관계 및 가설 검증 ────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════
with tab2:
    try:
        if growth_file is None or growth_df.empty:
            st.markdown("""
            <div class="banner-info">
              <strong>☝️ 생육 CSV가 필요해요.</strong><br>
              사이드바에서 생육 결과 데이터 CSV를 올려주세요.
              업로드하면 산점도·상관관계가 바로 표시돼요 🔍
            </div>
            """, unsafe_allow_html=True)
        else:
            pairs = [
                ("지상부 길이", "지하부 길이", "지상부 길이 vs 지하부 길이", "#3498db"),
                ("지상부 길이", "생중량", "지상부 길이 vs 생중량", "#e67e22"),
                ("지하부 길이", "생중량", "지하부 길이 vs 생중량", "#8e44ad"),
                ("잎 수", "생중량", "잎 수 vs 생중량", "#27ae60"),
            ]
            available_pairs = [p for p in pairs if p[0] in growth_df.columns and p[1] in growth_df.columns]

            if not available_pairs:
                st.info("⚠️ 생육 CSV에 산점도에 필요한 열(길이·잎 수·생중량)이 없어요.")
            else:
                st.markdown('<div class="section-title">📊 생육 변수 간 상관관계 비교</div>', unsafe_allow_html=True)
                st.markdown('<div class="section-sub">💡 r: -1(완전 반대) ~ +1(완전 같은 방향). 0에 가까울수록 관계가 약해요.</div>', unsafe_allow_html=True)

                n_rows = (len(available_pairs) + 1) // 2
                fig_scatter = make_subplots(
                    rows=n_rows, cols=2,
                    subplot_titles=[p[2] for p in available_pairs],
                    vertical_spacing=0.14,
                )
                for j, (xcol, ycol, title, color) in enumerate(available_pairs):
                    xy = growth_df[[xcol, ycol]].dropna()
                    if len(xy) < 2:
                        continue
                    xvals = xy.iloc[:, 0].values
                    yvals = xy.iloc[:, 1].values
                    r_val = np.corrcoef(xvals, yvals)[0, 1]
                    slope, intercept = np.polyfit(xvals, yvals, 1)
                    fit_x = np.linspace(xvals.min(), xvals.max(), 100)
                    fit_y = slope * fit_x + intercept
                    row = j // 2 + 1
                    col = j % 2 + 1
                    fig_scatter.add_trace(go.Scatter(
                        x=xvals, y=yvals, mode="markers",
                        marker=dict(size=9, color=color, opacity=0.8, line=dict(width=0.5, color="#ffffff")),
                        hovertemplate=(
                            f"<b>{xcol}</b>: %{{x:.1f}}<br>"
                            f"<b>{ycol}</b>: %{{y:.2f}}<extra></extra>"
                        ),
                        name=title,
                    ), row=row, col=col)
                    fig_scatter.add_trace(go.Scatter(
                        x=fit_x, y=fit_y, mode="lines",
                        line=dict(color="#e07a5f", width=2.5, dash="dash"),
                        name=f"r = {r_val:.3f}",
                        hoverinfo="skip",
                    ), row=row, col=col)
                fig_scatter.update_layout(
                    title=dict(text="📈 생육 변수 간 상관관계 (빨강 점선 = 추세선, r 값 표시)",
                               x=0.5, font=dict(size=13, color="#0d4f4f")),
                    template="plotly_white",
                    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                    height=280 + 170 * (n_rows - 1),
                    margin=dict(l=40, r=20, t=50, b=40),
                )
                st.plotly_chart(fig_scatter, width="stretch")

                # 가설 카드
                st.markdown('<div class="section-title">🔍 세 가지 가설 검토</div>', unsafe_allow_html=True)
                st.markdown("""
                | # | 가설 | 실제 데이터에서 확인 방법 |
                |---|------|--------------------------|
                | ① | **길이 지표끼리는 강하게 연관된다**<br>지상부 길이와 지하부 길이는 함께 자란다 | 첫 번째 산점도에서 r 값을 확인하세요. r이 0.7 이상이면 강한 관계예요 |
                | ② | **길이만으로는 생중량을 충분히 설명하기 어렵다**<br>r ≈ 0.2~0.3 수준 | 두 번째·세 번째 산점도의 r 값이 낮다면 이 가설이 지지돼요 |
                | ③ | **'잎 수'는 생중량을 가장 잘 설명한다**<br>r이 가장 높고 상·하위 그룹을 뚜렷이 구분 | 네 번째 산점도 r이 다른 지표보다 높으면 핵심 지표예요 |
                """.strip())
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")


# ═══════════════════════════════════════════════════════════════════════
# ── 탭 3: 상·하위 그룹 비교 및 예측 시뮬레이터 ────────────────────
# ═══════════════════════════════════════════════════════════════════════
with tab3:
    try:
        if growth_file is None or growth_df.empty:
            st.markdown("""
            <div class="banner-info">
              <strong>☝️ 생육 CSV가 필요해요.</strong><br>
              사이드바에서 생육 결과 데이터 CSV를 올려주세요.
              그룹 비교와 예측 시뮬레이터가 활성화돼요 🎯
            </div>
            """, unsafe_allow_html=True)
        else:
            if "생중량" not in growth_df.columns:
                st.info("⚠️ 생육 CSV에 '생중량' 열이 없어 그룹 비교를 진행하지 못해요.")
            else:
                g = growth_df[["개체번호", "생중량", "잎 수", "지상부 길이", "지하부 길이"]].copy()
                g = g.dropna(subset=["생중량"])
                if len(g) < 4:
                    st.info("⚠️ 생중량 값이 있는 개체가 너무 적어(상·하위 각 25% = 최소 2개) 그룹을 나눌 수 없어요.")
                else:
                    q75 = g["생중량"].quantile(0.75)
                    q25 = g["생중량"].quantile(0.25)
                    high = g[g["생중량"] >= q75].copy()
                    low = g[g["생중량"] <= q25].copy()

                    compare_items = []
                    for item, unit, col_name in [
                        ("잎 수", "장", "잎 수"),
                        ("지상부 길이", "mm", "지상부 길이"),
                        ("지하부 길이", "mm", "지하부 길이"),
                    ]:
                        if col_name not in g.columns:
                            continue
                        h_mean = high[col_name].dropna().mean() if not high[col_name].dropna().empty else float("nan")
                        l_mean = low[col_name].dropna().mean() if not low[col_name].dropna().empty else float("nan")
                        if np.isnan(h_mean) and np.isnan(l_mean):
                            continue
                        compare_items.append((item, unit, h_mean, l_mean))

                    if compare_items:
                        # 그룹 비교 그래프
                        st.markdown('<div class="section-title">📈 생중량 상·하위 그룹 평균 비교</div>', unsafe_allow_html=True)
                        fig_cmp = go.Figure()
                        x_labels = [f"{it[0]}\n({it[1]})" for it in compare_items]
                        h_vals = [it[2] for it in compare_items]
                        l_vals = [it[3] for it in compare_items]
                        fig_cmp.add_trace(go.Bar(
                            x=x_labels, y=h_vals,
                            name=f"상위 25% (n={len(high)})",
                            marker_color="#e74c3c",
                            text=[f"{v:.1f}" for v in h_vals],
                            textposition="outside",
                            textfont=dict(size=11, color="#e74c3c"),
                        ))
                        fig_cmp.add_trace(go.Bar(
                            x=x_labels, y=l_vals,
                            name=f"하위 25% (n={len(low)})",
                            marker_color="#27ae60",
                            text=[f"{v:.1f}" for v in l_vals],
                            textposition="outside",
                            textfont=dict(size=11, color="#27ae60"),
                        ))
                        fig_cmp.update_layout(
                            title=dict(text="📊 상·하위 그룹 측정 항목별 평균 비교",
                                       x=0.5, font=dict(size=13, color="#0d4f4f")),
                            barmode="group",
                            template="plotly_white",
                            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                            xaxis_title="측정 항목",
                            yaxis_title="평균값",
                            height=380,
                            margin=dict(l=40, r=20, t=50, b=40),
                        )
                        st.plotly_chart(fig_cmp, width="stretch")

                        df_cmp_rows = []
                        for it in compare_items:
                            df_cmp_rows.append({
                                "측정 항목": f"{it[0]} ({it[1]})",
                                "상위 25% 평균": f"{it[2]:.2f}",
                                "하위 25% 평균": f"{it[3]:.2f}",
                                "차이 (상위 − 하위)": f"{it[2] - it[3]:.2f}",
                            })
                        df_cmp_table = pd.DataFrame(df_cmp_rows)
                        st.dataframe(df_cmp_table, width="stretch")
                        st.download_button(
                            "📥 그룹 비교 표 다운로드 (CSV)",
                            csv_bytes(df_cmp_table),
                            "상하위_그룹_비교.csv",
                            "text/csv",
                            key="tab3_group_dl",
                        )

                    # ── 예측 시뮬레이터 ──────────────────────────────────
                    st.markdown('<div class="section-title" style="margin-top:20px;">🔮 간이 생중량 예측 시뮬레이터</div>', unsafe_allow_html=True)
                    st.markdown('<div class="section-sub">🍃 잎 수와 📏 지상부 길이를 슬라이더로 입력하면 회귀식으로 예상 생중량을 계산해요.</div>', unsafe_allow_html=True)

                    has_leaf = "잎 수" in g.columns and not g["잎 수"].dropna().empty
                    has_abv = "지상부 길이" in g.columns and not g["지상부 길이"].dropna().empty
                    has_biomass = "생중량" in g.columns and not g["생중량"].dropna().empty

                    if has_leaf and has_abv and has_biomass:
                        lm = g[["잎 수", "지상부 길이", "생중량"]].dropna()
                        if len(lm) >= 5:
                            X = lm[["잎 수", "지상부 길이"]].values
                            y = lm["생중량"].values
                            X_design = np.column_stack([np.ones(len(X)), X])
                            beta = np.linalg.lstsq(X_design, y, rcond=None)[0]
                            intercept_m, beta_leaf, beta_abv = beta

                            leaf_r = np.corrcoef(lm["잎 수"], lm["생중량"])[0, 1]
                            abv_r = np.corrcoef(lm["지상부 길이"], lm["생중량"])[0, 1]

                            leaf_max = max(int(lm["잎 수"].max()), 10)
                            abv_max = max(int(lm["지상부 길이"].max()), 10)

                            s1, s2 = st.columns(2)
                            with s1:
                                leaf_input = st.slider(
                                    "🍃 잎 수 (장)",
                                    min_value=0,
                                    max_value=leaf_max,
                                    value=min(int(lm["잎 수"].median()), leaf_max),
                                    step=1,
                                    key="leaf_slider",
                                )
                            with s2:
                                abv_input = st.slider(
                                    "📏 지상부 길이 (mm)",
                                    min_value=0,
                                    max_value=abv_max,
                                    value=min(int(lm["지상부 길이"].median()), abv_max),
                                    step=1,
                                    key="abv_slider",
                                )

                            pred_biomass = max(0, intercept_m + beta_leaf * leaf_input + beta_abv * abv_input)

                            st.markdown("---")
                            m1, m2, m3 = st.columns(3)
                            m1.markdown(f"""
                            <div class="col-card">
                              <div class="card-label">🍃 입력: 잎 수</div>
                              <div class="card-value">{leaf_input} 장</div>
                            </div>
                            """, unsafe_allow_html=True)
                            m2.markdown(f"""
                            <div class="col-card">
                              <div class="card-label">📏 입력: 지상부 길이</div>
                              <div class="card-value">{abv_input} mm</div>
                            </div>
                            """, unsafe_allow_html=True)
                            m3.markdown(f"""
                            <div class="col-card" style="border:2px solid #e07a5f;">
                              <div class="card-label" style="color:#e07a5f;">🎯 예상 생중량</div>
                              <div class="card-value" style="color:#e07a5f;">{pred_biomass:.2f} g</div>
                              <div class="card-delta">
                                잎 수 r = {leaf_r:.3f} · 길이 r = {abv_r:.3f}
                              </div>
                            </div>
                            """, unsafe_allow_html=True)

                            st.info(
                                f"💡 회귀식: <strong>예상 생중량(g) = {intercept_m:.3f} + ({beta_leaf:.4f}) × 잎 수 + ({beta_abv:.4f}) × 지상부 길이</strong><br>"
                                f"→ 이 데이터에서는 <strong>잎 수</strong>가 생중량을 설명하는 데 더 큰 역할을 해요 (r = {leaf_r:.3f})."
                            )
                            st.caption(
                                "⚠️ 이 예측식은 해당 학교 데이터에만 맞춘 간이 모델이에요. "
                                "과학적으로는 개체 수를 늘리고 여러 환경에서 반복 측정하는 후속 실험이 필요해요."
                            )
                        else:
                            st.info("⚠️ 회귀식을 만들기에 데이터가 충분하지 않아요.")
                    else:
                        st.info("⚠️ 예측 시뮬레이터를 사용하려면 '잎 수', '지상부 길이', '생중량' 열이 모두 필요해요.")

                    # ── 데이터 한계점 & 후속 실험 ────────────────────────
                    st.markdown('<div class="section-title" style="margin-top:20px;">📌 데이터 한계점 및 후속 실험 제안</div>', unsafe_allow_html=True)
                    st.markdown("""
                    | 구분 | 내용 |
                    |------|------|
                    | **데이터 한계** | 생중량 차이가 약 30배에 달할 정도로 개체 간 편차가 크며, 길이 지표(지상부·지하부 길이)와 생중량 사이의 상관계수가 낮아 길이만으로는 생중량을 충분히 예측하기 어려워요. |
                    | **핵심 발견** | <strong>'잎 수'</strong>가 생중량과 가장 높은 상관관계를 보이며, 생중량 상위·하위 그룹을 가장 뚜렷하게 구분해요. 즉, 길이보다 <strong>잎의 수</strong>가 생중량 차이의 핵심 지표예요. |
                    | **후속 실험 ①** | 개체 수를 현재보다 늘리고(최소 90개체 이상), 동일 환경에서 반복 재배하여 잎 수-생중량 관계의 안정성을 확인해요. |
                    | **후속 실험 ②** | 온도·습도·EC·pH 조건을 조금씩 바꾼 여러 스마트팜 구획을 만들어, 환경 조건이 잎 수와 생중량 관계에 미치는 영향을 비교해요. |
                    | **후속 실험 ③** | 잎 면적, 잎 두께, 엽록소 함량 등 추가 형질을 측정해 생중량을 더 정밀하게 설명하는 복합 지표를 개발해요. |
                    """.strip())
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")
