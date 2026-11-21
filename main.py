import io
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── 한글 폰트 (Streamlit CSS) ──────────────────────────────────────────
st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
   font-family: 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ── 열 이름 표준화 (std_cols) ──────────────────────────────────────────
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


# ── CSV 읽기 (인코딩 이중 시도) ───────────────────────────────────────
@st.cache_data
def read_csv(file):
    data = file.getvalue()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(io.BytesIO(data), encoding=enc)
        except Exception:
            pass
    return pd.DataFrame()


# ── 학교명 추출 ───────────────────────────────────────────────────────
def school_name(filename):
    if not filename:
        return "우리 학교"
    base = os.path.splitext(filename)[0]
    # 첫 번째 '_' 또는 '.' 앞까지가 학교명 후보
    for sep in ("_", "."):
        if sep in base:
            candidate = base.split(sep)[0]
            if len(candidate) >= 2:
                return candidate
    return base[:6] if len(base) >= 2 else base


# ── 공통: 추세선 있는 산점도 ──────────────────────────────────────────
def scatter_with_fit(x, y, xlabel, ylabel, title, color="#1f77b4"):
    xy = pd.DataFrame({xlabel: x, ylabel: y}).dropna()
    if len(xy) < 2:
        st.info(f"⚠️ '{title}': 데이터가 충분하지 않아 그래프를 그리지 못했어요.")
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
        marker=dict(size=8, color=color, opacity=0.75),
        hovertemplate=f"<b>%{xlabel}</b>: %{{x:.1f}}<br><b>%{ylabel}</b>: %{{y:.2f}}<extra></extra>",
        name="데이터",
    ))
    fig.add_trace(go.Scatter(
        x=fit_x, y=fit_y, mode="lines",
        line=dict(color="red", width=2, dash="dash"),
        name=f"추세선 (r = {r:.3f})",
        hoverinfo="skip",
    ))
    fig.update_layout(
        title=dict(text=f"{title}  (r = {r:.3f})", x=0.5, font=dict(size=14)),
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        template="plotly_white",
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
        height=360,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


# ── CSV 다운로드 도우미 ────────────────────────────────────────────────
def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


# ═══════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="극지식물 생육 차이 분석 대시보드", layout="wide")

st.title("극지식물 생육 차이 핵심 요인 분석 대시보드: 길이보다 '잎 수'가 생중량을 결정한다")

st.caption(
    "같은 스마트팜 환경에서 자란 극지식물 개체들 사이에 나타나는 큰 생육 차이와 "
    "그 차이를 만드는 핵심 요인을 함께 살펴봅시다. 📊"
)

# ── 사이드바: 파일 업로드 ───────────────────────────────────────────────
st.sidebar.header("📁 데이터 업로드")
env_file = st.sidebar.file_uploader("🌡️ 환경 데이터 CSV", type="csv")
growth_file = st.sidebar.file_uploader("🌱 생육 결과 데이터 CSV", type="csv")

st.sidebar.markdown("---")
st.sidebar.subheader("🌱 생육 측정 항목 선택")
growth_cols_raw = []
if growth_file is not None:
    gtmp = read_csv(growth_file)
    gtmp = std_cols(gtmp)
    candidates = [
        "잎 수", "지상부 길이", "지하부 길이",
        "생중량", "지상부 질량", "지하부 질량",
    ]
    growth_cols_raw = [
        c for c in candidates if c in gtmp.columns
    ]

selected_growth = st.sidebar.multiselect(
    "분포·변동계수(CV) 비교에 사용할 항목",
    growth_cols_raw,
    default=[c for c in growth_cols_raw if c in ("잎 수", "지상부 길이", "지하부 길이", "생중량")],
)

if growth_cols_raw:
    st.sidebar.success(f"감지된 생육 항목: {', '.join(growth_cols_raw)}")
else:
    st.sidebar.info("생육 CSV를 올리면 측정 항목이 자동 감지돼요.")

env_name = school_name(env_file.name if env_file else None)
growth_name = school_name(growth_file.name if growth_file else None)

# ── 데이터 로딩 ( spinner ) ───────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.caption("로딩 중…")

env_df = pd.DataFrame()
growth_df = pd.DataFrame()

if env_file is not None:
    with st.spinner("환경 데이터 읽는 중…"):
        env_df = std_cols(read_csv(env_file))
if growth_file is not None:
    with st.spinner("생육 데이터 읽는 중…"):
        growth_df = std_cols(read_csv(growth_file))

st.sidebar.markdown("---")
st.sidebar.caption(
    f"환경: {env_name} · 생육: {growth_name}"
    if env_file or growth_file else "아직 파일이 업로드되지 않았어요."
)

# ═══════════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "📊 스마트팜 환경 및 개체별 생육 분포",
    "🔗 생육 변수 간 상관관계 및 가설 검증",
    "🎯 생중량 상·하위 그룹 비교 및 예측 시뮬레이터",
])

# ─────────────────────────────────────────────────────────────────────
# 탭 1: 환경 및 개체별 생육 분포
# ─────────────────────────────────────────────────────────────────────
with tabs[0]:
    try:
        # ── 파일 안내 ────────────────────────────────────────────────
        if env_file is None and growth_file is None:
            st.info("☝️ 사이드바에서 환경 CSV와 생육 CSV를 각각 올려주세요.")
        else:
            env_ready = not env_df.empty
            growth_ready = not growth_df.empty

            # ── 환경 시계열 그래프 ────────────────────────────────────
            if env_ready:
                env_cols_display = [
                    c for c in ["temperature", "humidity", "ph", "ec"]
                    if c in env_df.columns
                ]
                if env_cols_display:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(
                            "평균 온도",
                            f"{env_df['temperature'].dropna().mean():.1f} °C"
                            if "temperature" in env_df.columns else "—",
                        )
                    with col2:
                        st.metric(
                            "평균 습도",
                            f"{env_df['humidity'].dropna().mean():.1f} %"
                            if "humidity" in env_df.columns else "—",
                        )
                    with col3:
                        st.metric(
                            "평균 EC",
                            f"{env_df['ec'].dropna().mean():.2f} mS/cm"
                            if "ec" in env_df.columns else "—",
                        )
                    with col4:
                        st.metric(
                            "평균 pH",
                            f"{env_df['ph'].dropna().mean():.1f}"
                            if "ph" in env_df.columns else "—",
                        )

                    ecols = st.columns(min(len(env_cols_display), 3))
                    for idx, cname in enumerate(env_cols_display):
                        s = env_df[cname].dropna()
                        if len(s) == 0:
                            continue
                        card = ecols[idx % len(ecols)]
                        card.metric(
                            f"{cname} 요약",
                            f"평균 {s.mean():.2f} · SD {s.std():.2f}",
                            delta=f"범위: {s.min():.2f} ~ {s.max():.2f}",
                        )

                    # 시계열 서브플롯
                    n_env = len(env_cols_display)
                    if n_env > 0:
                        n_rows = (n_env + 1) // 2
                        fig_env = make_subplots(
                            rows=n_rows, cols=2,
                            subplot_titles=env_cols_display,
                            vertical_spacing=0.12,
                        )
                        for j, cname in enumerate(env_cols_display):
                            s = env_df[["time", cname]].dropna()
                            if s.empty:
                                continue
                            row = j // 2 + 1
                            col = j % 2 + 1
                            color = {
                                "temperature": "#e74c3c",
                                "humidity": "#3498db",
                                "ph": "#27ae60",
                                "ec": "#f39c12",
                            }.get(cname, "#1f77b4")
                            fig_env.add_trace(
                                go.Scatter(
                                    x=s["time"], y=s[cname],
                                    mode="lines", name=cname,
                                    line=dict(color=color, width=1.5),
                                    hovertemplate=(
                                        f"<b>{cname}</b><br>%{{x|%Y-%m-%d %H:%M}}<br>"
                                        f"값: %{{y:.2f}}<extra></extra>"
                                    ),
                                ),
                                row=row, col=col,
                            )
                        fig_env.update_layout(
                            title="📅 날짜별 환경 지표 시계열",
                            template="plotly_white",
                            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                            height=260 + 160 * (n_rows - 1),
                            margin=dict(l=40, r=20, t=40, b=30),
                        )
                        st.plotly_chart(fig_env, width="stretch")
                else:
                    st.info("⚠️ 환경 CSV에 인식할 수 있는 열(온도, 습도, EC, pH)이 없어요.")

            # ── 개체별 생중량 막대그래프 ───────────────────────────────
            if growth_ready and "생중량" in growth_df.columns:
                g_sorted = growth_df.sort_values("생중량", ascending=False).reset_index(drop=True)
                n = len(g_sorted)
                if n > 0:
                    top_n = max(1, n // 4)
                    bottom_n = max(1, n // 4)
                    colors = []
                    for i in range(n):
                        if i < top_n:
                            colors.append("#e74c3c")       # 상위: 빨강
                        elif i >= n - bottom_n:
                            colors.append("#27ae60")       # 하위: 초록
                        else:
                            colors.append("#95a5a6")       # 중간: 회색
                    fig_bar = go.Figure()
                    fig_bar.add_trace(go.Bar(
                        x=[str(v) for v in g_sorted["개체번호"].values],
                        y=g_sorted["생중량"].values,
                        marker_color=colors,
                        hovertemplate=(
                            "<b>개체 %{x}</b><br>생중량: %{y:.2f} g<extra></extra>"
                        ),
                    ))
                    # 상위·하위 레이블 주석
                    if top_n > 0:
                        fig_bar.add_annotation(
                            x=top_n - 0.5, y=g_sorted["생중량"].iloc[top_n - 1],
                            text="⬆ 상위", showarrow=False,
                            font=dict(size=11, color="#e74c3c"),
                            yshift=5,
                        )
                    if bottom_n > 0:
                        fig_bar.add_annotation(
                            x=n - bottom_n - 0.5, y=g_sorted["생중량"].iloc[n - bottom_n],
                            text="⬇ 하위", showarrow=False,
                            font=dict(size=11, color="#27ae60"),
                            yshift=5,
                        )
                    fig_bar.update_layout(
                        title="🌱 개체별 생중량 분포 (상위 25% 빨강 · 하위 25% 초록)",
                        template="plotly_white",
                        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                        xaxis_title="개체",
                        yaxis_title="생중량 (g)",
                        height=360,
                        margin=dict(l=40, r=20, t=50, b=40),
                    )
                    st.plotly_chart(fig_bar, width="stretch")
                else:
                    st.info("⚠️ 생육 데이터에 생중량 값이 없어요.")
            elif growth_ready:
                st.info("⚠️ 생육 CSV에 '생중량' 열이 없어요. (지상부 질량 + 지하부 질량으로 자동 계산되었을 수 있어요.)")

            # ── 생육 측정 항목 분포 & CV 비교 표 ──────────────────────
            if growth_ready and selected_growth:
                dist_tables = []
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
                    dist_tables.append(
                        {
                            "측정 항목": f"{sname} ({unit})",
                            "개체 수": f"{len(s)}개",
                            "평균": f"{mean_v:.2f}",
                            "표준편차 (SD)": f"{std_v:.2f}",
                            "변동계수 (CV)": f"{cv_v:.1f}%",
                            "최솟값": f"{s.min():.2f}",
                            "최댓값": f"{s.max():.2f}",
                        }
                    )
                if dist_tables:
                    df_dist = pd.DataFrame(dist_tables)
                    st.subheader("📋 생육 측정 항목별 분포 및 변동계수(CV) 비교")
                    st.caption(
                        "💡 변동계수(CV) = (표준편차 ÷ 평균) × 100%. "
                        "값이 클수록 개체 간 차이가 크다는 뜻이에요. 평균이 0이면 CV는 표시하지 않아요."
                    )
                    st.dataframe(df_dist, width="stretch", use_container_width=False)
                    st.download_button(
                        "📥 CV 비교 표 다운로드 (CSV)",
                        csv_bytes(df_dist),
                        "생육_CV_비교표.csv",
                        "text/csv",
                        key="tab1_cv_download",
                    )
            elif growth_ready:
                st.info("☝️ 사이드바에서 분포·CV 비교에 사용할 생육 항목을 골라주세요.")

    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")

# ─────────────────────────────────────────────────────────────────────
# 탭 2: 상관관계 및 가설 검증
# ─────────────────────────────────────────────────────────────────────
with tabs[1]:
    try:
        if growth_file is None or growth_df.empty:
            st.info("☝️ 사이드바에서 생육 CSV를 올려주세요. 상관관계 그래프를 볼 수 있어요.")
        else:
            # 필요한 열 확인
            needed_pairs = [
                ("지상부 길이", "지하부 길이", "지상부 길이 vs 지하부 길이", "#3498db"),
                ("지상부 길이", "생중량", "지상부 길이 vs 생중량", "#e67e22"),
                ("지하부 길이", "생중량", "지하부 길이 vs 생중량", "#8e44ad"),
                ("잎 수", "생중량", "잎 수 vs 생중량", "#27ae60"),
            ]
            available_pairs = [
                p for p in needed_pairs
                if p[0] in growth_df.columns and p[1] in growth_df.columns
            ]
            if not available_pairs:
                st.info("⚠️ 생육 CSV에 산점도에 필요한 열(길이·잎 수·생중량)이 없어요.")
            else:
                st.caption(
                    "💡 상관계수 r: -1(완전 반대) ~ +1(완전 같은 방향). "
                    "0에 가까울수록 두 값 사이에 뚜렷한 관계가 없다는 뜻이에요."
                )
                n_cols = 2
                n_rows = (len(available_pairs) + 1) // 2
                fig_scatter = make_subplots(
                    rows=n_rows, cols=n_cols,
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
                    fig_scatter.add_trace(
                        go.Scatter(
                            x=xvals, y=yvals,
                            mode="markers",
                            marker=dict(size=8, color=color, opacity=0.75),
                            hovertemplate=(
                                f"<b>{xcol}</b>: %{{x:.1f}}<br>"
                                f"<b>{ycol}</b>: %{{y:.2f}}<extra></extra>"
                            ),
                            name=title,
                        ),
                        row=row, col=col,
                    )
                    fig_scatter.add_trace(
                        go.Scatter(
                            x=fit_x, y=fit_y,
                            mode="lines",
                            line=dict(color="red", width=2, dash="dash"),
                            name=f"r = {r_val:.3f}",
                            hoverinfo="skip",
                        ),
                        row=row, col=col,
                    )
                fig_scatter.update_layout(
                    title="📊 생육 변수 간 상관관계 비교 (빨간 점선 = 추세선)",
                    template="plotly_white",
                    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                    height=300 + 180 * (n_rows - 1),
                    margin=dict(l=40, r=20, t=50, b=40),
                )
                st.plotly_chart(fig_scatter, width="stretch")

                # 가설 정리 카드
                st.subheader("🔍 세 가지 가설 검토")
                st.markdown("""
                | 가설 | 기대 | 실제 데이터에서의 확인 |
                |------|------|------------------------|
                | ① 길이 지표끼리는 강하게 연관된다 | 지상부 길이와 지하부 길이는 함께 자란다 | 산점도에서 r 값을 직접 확인하세요 |
                | ② 길이만으로는 생중량을 충분히 설명하기 어렵다 | r ≈ 0.2~0.3 수준 |지상부·지하부 길이 vs 생중량 r 값이 낮다면 이 가설이 지지돼요 |
                | ③ '잎 수'는 생중량을 가장 잘 설명한다 | r이 가장 높고 상·하위 그룹을 뚜렷이 구분 | 잎 수 vs 생중량 r이 다른 지표보다 높으면 핵심 지표예요 |
                """.strip())

    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")

# ─────────────────────────────────────────────────────────────────────
# 탭 3: 상·하위 그룹 비교 및 예측 시뮬레이터
# ─────────────────────────────────────────────────────────────────────
with tabs[2]:
    try:
        if growth_file is None or growth_df.empty:
            st.info("☝️ 사이드바에서 생육 CSV를 올려주세요. 그룹 비교와 예측 시뮬레이터가 활성화돼요.")
        else:
            # 생중량이 있어야 그룹 비교 가능
            if "생중량" not in growth_df.columns:
                st.info("⚠️ 생육 CSV에 '생중량' 열이 없어 그룹 비교를 진행하지 못해요.")
            else:
                g = growth_df[["개체번호", "생중량", "잎 수", "지상부 길이", "지하부 길이"]].copy()
                g = g.dropna(subset=["생중량"])
                if len(g) < 4:
                    st.info("⚠️ 생중량 값이 있는 개체가 너무 적어(상·하위 각 25% = 최소 2개 필요) 그룹을 나눌 수 없어요.")
                else:
                    # 상위 25% / 하위 25% 임계값
                    q75 = g["생중량"].quantile(0.75)
                    q25 = g["생중량"].quantile(0.25)
                    high = g[g["생중량"] >= q75].copy()
                    low = g[g["생중량"] <= q25].copy()

                    # 상·하위 그룹 평균 비교 막대그래프
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
                        fig_cmp = go.Figure()
                        x_labels = [f"{it[0]}\n({it[1]})" for it in compare_items]
                        h_vals = [it[2] for it in compare_items]
                        l_vals = [it[3] for it in compare_items]
                        fig_cmp.add_trace(go.Bar(
                            x=x_labels, y=h_vals,
                            name=f"생중량 상위 25% (n={len(high)})",
                            marker_color="#e74c3c",
                            text=[f"{v:.1f}" for v in h_vals],
                            textposition="outside",
                        ))
                        fig_cmp.add_trace(go.Bar(
                            x=x_labels, y=l_vals,
                            name=f"생중량 하위 25% (n={len(low)})",
                            marker_color="#27ae60",
                            text=[f"{v:.1f}" for v in l_vals],
                            textposition="outside",
                        ))
                        fig_cmp.update_layout(
                            title="📈 생중량 상·하위 그룹의 측정 항목별 평균 비교",
                            barmode="group",
                            template="plotly_white",
                            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                            xaxis_title="측정 항목",
                            yaxis_title="평균값",
                            height=380,
                            margin=dict(l=40, r=20, t=50, b=40),
                        )
                        st.plotly_chart(fig_cmp, width="stretch")

                        # 그룹별 요약 통계
                        st.subheader("📋 상·하위 그룹 측정 항목별 평균")
                        rows_tbl = []
                        for it in compare_items:
                            rows_tbl.append({
                                "측정 항목": f"{it[0]} ({it[1]})",
                                "상위 25% 평균": f"{it[2]:.2f}",
                                "하위 25% 평균": f"{it[3]:.2f}",
                                "차이 (상위 − 하위)": f"{it[2] - it[3]:.2f}",
                            })
                        df_cmp_table = pd.DataFrame(rows_tbl)
                        st.dataframe(df_cmp_table, width="stretch", use_container_width=False)
                        st.download_button(
                            "📥 그룹 비교 표 다운로드 (CSV)",
                            csv_bytes(df_cmp_table),
                            "상하위_그룹_비교.csv",
                            "text/csv",
                            key="tab3_group_download",
                        )

                    # ── 예측 시뮬레이터 ──────────────────────────────────
                    st.markdown("---")
                    st.subheader("🔮 간이 생중량 예측 시뮬레이터")
                    st.caption(
                        "'잎 수'와 '지상부 길이'를 슬라이더로 입력하면, "
                        "실제 데이터에 맞춘 회귀식으로 예상 생중량을 계산해 줘요. "
                        "(실제 생중량과는 개체별 차이가 있을 수 있어요!)"
                    )

                    has_leaf = "잎 수" in g.columns and not g["잎 수"].dropna().empty
                    has_abv = "지상부 길이" in g.columns and not g["지상부 길이"].dropna().empty
                    has_biomass = "생중량" in g.columns and not g["생중량"].dropna().empty

                    if has_leaf and has_abv and has_biomass:
                        lm = g[["잎 수", "지상부 길이", "생중량"]].dropna()
                        if len(lm) >= 5:
                            # 다중 회귀: 생중량 ~ 잎 수 + 지상부 길이
                            X = lm[["잎 수", "지상부 길이"]].values
                            y = lm["생중량"].values
                            X_design = np.column_stack([np.ones(len(X)), X])
                            beta = np.linalg.lstsq(X_design, y, rcond=None)[0]
                            intercept_m, beta_leaf, beta_abv = beta

                            # 개별 단순 회귀도 표시
                            leaf_r = np.corrcoef(lm["잎 수"], lm["생중량"])[0, 1]
                            abv_r = np.corrcoef(lm["지상부 길이"], lm["생중량"])[0, 1]

                            leaf_max = int(lm["잎 수"].max())
                            abv_max = int(lm["지상부 길이"].max())

                            c1, c2 = st.columns(2)
                            with c1:
                                leaf_input = st.slider(
                                    "🍃 잎 수 (장)",
                                    min_value=0,
                                    max_value=max(leaf_max, 10),
                                    value=min(int(lm["잎 수"].median()), leaf_max),
                                    step=1,
                                )
                            with c2:
                                abv_input = st.slider(
                                    "📏 지상부 길이 (mm)",
                                    min_value=0,
                                    max_value=max(abv_max, 10),
                                    value=min(int(lm["지상부 길이"].median()), abv_max),
                                    step=1,
                                )

                            pred_biomass = max(0, intercept_m + beta_leaf * leaf_input + beta_abv * abv_input)

                            st.markdown("---")
                            p1, p2, p3 = st.columns(3)
                            p1.metric("입력: 잎 수", f"{leaf_input} 장")
                            p2.metric("입력: 지상부 길이", f"{abv_input} mm")
                            p3.metric(
                                "🎯 예상 생중량",
                                f"{pred_biomass:.2f} g",
                                delta=f"잎 수 r = {leaf_r:.3f} · 길이 r = {abv_r:.3f}",
                            )

                            st.info(
                                f"💡 회귀식: 예상 생중량(g) = {intercept_m:.3f}"
                                f" + ({beta_leaf:.4f}) × 잎 수 + ({beta_abv:.4f}) × 지상부 길이\n"
                                f"→ 이 데이터에서는 **잎 수**가 생중량을 설명하는 데 더 큰 역할을 해요 (r = {leaf_r:.3f})."
                            )

                            # 회귀 유의성 정보
                            st.caption(
                                "⚠️ 이 예측식은 해당 학교 데이터에만 맞춘 간이 모델이에요. "
                                "개체 수가 적거나 환경이 다른 학교에서는 결과가 다를 수 있어요. "
                                "과학적으로는 개체 수를 늘리고 여러 환경에서 반복 측정하는 후속 실험이 필요해요."
                            )
                        else:
                            st.info("⚠️ 회귀식을 만들기에 데이터가 충분하지 않아요.")
                    else:
                        st.info("⚠️ 예측 시뮬레이터를 사용하려면 '잎 수', '지상부 길이', '생중량' 열이 모두 필요해요.")

                    # ── 데이터 한계점 & 후속 실험 제안 ───────────────────
                    st.markdown("---")
                    st.subheader("📌 데이터 한계점 및 후속 실험 제안")
                    st.markdown("""
                    | 구분 | 내용 |
                    |------|------|
                    | **데이터 한계** | 생중량 차이가 약 30배에 달할 정도로 개체 간 편차가 크며, 길이 지표(지상부·지하부 길이)와 생중량 사이의 상관계수가 낮아 길이만으로는 생중량을 충분히 예측하기 어려워요. |
                    | **핵심 발견** | '잎 수'가 생중량과 가장 높은 상관관계를 보이며, 생중량 상위·하위 그룹을 가장 뚜렷하게 구분해요. 즉, 길이보다 잎의 수가 생중량 차이의 핵심 지표예요. |
                    | **후속 실험 ①** | 개체 수를 현재보다 늘리고(최소 90개체 이상), 동일 환경에서 반복 재배하여 잎 수-생중량 관계의 안정성을 확인해요. |
                    | **후속 실험 ②** | 온도·습도·EC·pH 조건을 조금씩 바꾼 여러 스마트팜 구획을 만들어, 환경 조건이 잎 수와 생중량 관계에 미치는 영향을 비교해요. |
                    | **후속 실험 ③** | 잎 면적, 잎 두께, 엽록소 함량 등 추가 형질을 측정해 생중량을 더 정밀하게 설명하는 복합 지표를 개발해요. |
                    """.strip())
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")
