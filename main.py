import io
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ──────────────────────────────────────────────
#  한글 폰트 CSS
# ──────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
#  CSV 읽기 (인코딩 이중 시도)
# ──────────────────────────────────────────────
@st.cache_data
def read_csv_with_caching(file):
    if file is None:
        return pd.DataFrame()
    data = file.getvalue()
    for enc in ("utf-8-sig", "cp949"):
        try:
            df = pd.read_csv(io.BytesIO(data), encoding=enc)
            return df
        except Exception:
            pass
    return pd.DataFrame()

# ──────────────────────────────────────────────
#  열 이름 표준화 (어떤 학교 CSV든 안전)
# ──────────────────────────────────────────────
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
                .str.extract(r"(-?\d+\.?\d*)")[0],
                errors="coerce",
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

# ──────────────────────────────────────────────
#  다운로드 도우미
# ──────────────────────────────────────────────
def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")

# ──────────────────────────────────────────────
#  공통 그래프 스타일
# ──────────────────────────────────────────────
def plotly_font(fig):
    fig.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

# ──────────────────────────────────────────────
#  사이드바: 업로드
# ──────────────────────────────────────────────
st.sidebar.title("📂 데이터 업로드")
env_file   = st.sidebar.file_uploader("환경 CSV", type="csv")
growth_file = st.sidebar.file_uploader("생육 결과 CSV", type="csv")
growth_cols = st.sidebar.multiselect(
    "생육 측정 항목 선택",
    ["잎 수", "지상부 길이", "지하부 길이", "지상부 질량", "지하부 질량", "생중량"],
    default=["잎 수", "지상부 길이", "지하부 길이", "생중량"],
)
st.sidebar.markdown("---")
st.sidebar.info("📌 CSV를 업로드하면 대시보드가 자동으로 채워집니다.")
st.sidebar.markdown("학교명은 업로드한 파일명에서 자동 감지됩니다.")

# ──────────────────────────────────────────────
#  데이터 로딩
# ──────────────────────────────────────────────
with st.spinner("📡 데이터를 불러오는 중…"):
    env_raw   = read_csv_with_caching(env_file)
    growth_raw = read_csv_with_caching(growth_file)
    env_df    = std_cols(env_raw)    if not env_raw.empty    else pd.DataFrame()
    growth_df = std_cols(growth_raw) if not growth_raw.empty else pd.DataFrame()

# ──────────────────────────────────────────────
#  학교명 감지
# ──────────────────────────────────────────────
def school_name(filename):
    if not filename:
        return "알 수 없음"
    base = os.path.basename(filename)
    # 앞의 '_환경'|'_생육' 등 접미사를 떼어 학교명 추정
    for suffix in ("_환경데이터", "_생육결과데이터", "환경", "생육", "_환경", "_생육"):
        if suffix in base:
            return base.replace(suffix, "").replace(".csv", "").strip()
    return base.replace(".csv", "").strip()

school_env   = school_name(env_file.name)    if env_file    else None
school_growth = school_name(growth_file.name) if growth_file else None
school_label = school_env or school_growth or "업로드된 파일"

st.set_page_config(page_title="극지식물 생육 대시보드", layout="wide")

# ──────────────────────────────────────────────
#  탭
# ──────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ================================================================
#  Tab 1 — 실험 개요
# ================================================================
with tab1:
    try:
        st.header(f"🌱 {school_label} 극지식물 개체별 생육 차이 분석")
        st.markdown("---")

        # ── 연구 배경 및 목적 ──
        st.subheader("🔬 연구 배경 및 목적")
        st.markdown(
            "**극지식물**은 척박한 환경에서도 살아남는 강인한 식물입니다.\n"
            "같은 학교, 같은 조건에서 키운 개체들 사이에도 생육 차이가 존재합니다.\n\n"
            "**이 대시보드의 목적**\n"
            "- 개체별로 얼마나 차이가 나는지 숫자로 확인\n"
            "- 평균·표준편차·변동계수(CV)로 분포의 특징을 파악\n"
            "  - *평균*: 모든 값을 더해 개수로 나눈 대표값\n"
            "  - *표준편차*: 값이 평균에서 얼마나 퍼져 있는지 나타내는 지표\n"
            "  - *변동계수(CV)*: 표준편차를 평균으로 나눈 값, 단위가 다른 그룹끼리 비교할 때 유용\n"
            "- 잎 수·지상부 길이와 생중량의 관계를 산점도와 상관계수로 확인\n"
            "  - *상관계수*: -1에서 1 사이 값, 1에 가까울수록 한 값이 커질 때 다른 값도 커지는 경향이 강함\n"
            "- 생중량 상위 25%와 하위 25% 개체를 비교해 잘 자란 개체의 특징을 탐색",
        )

        if growth_df.empty:
            st.info("📊 생육 결과 CSV를 업로드하면 이 탭의 내용이 채워집니다.")
        else:
            st.markdown("---")
            st.subheader("📋 데이터 요약")

            # 측정 기간
            time_col = "time" if "time" in env_df.columns else None
            if time_col and not env_df[time_col].isna().all():
                t_min = env_df[time_col].min().strftime("%Y-%m-%d")
                t_max = env_df[time_col].max().strftime("%Y-%m-%d")
            else:
                t_min, t_max = "확인 불가", "확인 불가"

            summary_rows = []
            summary_rows.append({
                "항목": "총 개체 수",
                "값": f"{len(growth_df):,}개체",
            })
            summary_rows.append({
                "항목": "측정 기간 (환경)",
                "값": f"{t_min} ~ {t_max}",
            })
            summary_rows.append({
                "항목": "생육 측정 항목",
                "값": ", ".join(g for g in growth_cols if g in growth_df.columns)
                             or "선택한 항목이 없습니다",
            })
            st.table(pd.DataFrame(summary_rows))

            st.markdown("---")
            st.subheader("📊 주요 지표 카드")

            c1, c2, c3, c4 = st.columns(4)

            total = len(growth_df)
            c1.metric("총 개체 수", f"{total}개체")

            if "temperature" in env_df.columns:
                tavg = env_df["temperature"].dropna().mean()
                if pd.notna(tavg):
                    c2.metric("평균 온도", f"{tavg:.1f}℃")
                else:
                    c2.metric("평균 온도", "데이터 없음")
            else:
                c2.metric("평균 온도", "측정 열 없음")

            if "humidity" in env_df.columns:
                havg = env_df["humidity"].dropna().mean()
                if pd.notna(havg):
                    c3.metric("평균 습도", f"{havg:.1f}%")
                else:
                    c3.metric("평균 습도", "데이터 없음")
            else:
                c3.metric("평균 습도", "측정 열 없음")

            if "생중량" in growth_df.columns:
                gavg = growth_df["생중량"].dropna().mean()
                if pd.notna(gavg):
                    c4.metric("평균 생중량", f"{gavg:.2f}g")
                else:
                    c4.metric("평균 생중량", "데이터 없음")
            else:
                c4.metric("평균 생중량", "측정 열 없음")

    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")

# ================================================================
#  Tab 2 — 환경 데이터
# ================================================================
with tab2:
    try:
        if env_df.empty:
            st.info("🌡️ 환경 CSV를 업로드하면 이 탭의 내용이 채워집니다.")
        else:
            env_cols = [c for c in ["temperature", "humidity", "ph", "ec"]
                        if c in env_df.columns]

            if not env_cols:
                st.info("⚠️ 환경 CSV에서 인식할 수 있는 측정 열이 없습니다. "
                        "열 이름이 `temperature / 습도 / PH / EC` 중 하나인지 확인하세요.")
            else:
                st.subheader("🌡️ 환경 데이터 요약")

                # 요약 표
                summary_data = []
                for col_disp, col_key in [
                    ("온도 (℃)", "temperature"),
                    ("습도 (%)", "humidity"),
                    ("pH", "ph"),
                    ("EC (mS/cm)", "ec"),
                ]:
                    if col_key in env_df.columns:
                        s = env_df[col_key].dropna()
                        if len(s) >= 2:
                            summary_data.append({
                                "측정 항목": col_disp,
                                "평균": round(s.mean(), 2),
                                "최소": round(s.min(), 2),
                                "최대": round(s.max(), 2),
                            })
                if summary_data:
                    st.table(pd.DataFrame(summary_data))
                else:
                    st.info("표시할 환경 수치가 부족합니다.")

                st.markdown("---")

                # 시계열: 날짜별 일별 평균
                st.subheader("📈 날짜별 환경 변화 (일별 평균)")
                time_col = "time" if "time" in env_df.columns else None
                if time_col and env_df[time_col].notna().any():
                    daily = (
                        env_df.dropna(subset=[time_col])
                        .copy()
                    )
                    daily["date"] = daily[time_col].dt.date
                    grp = daily.groupby("date")
                    daily_summary = grp[env_cols].mean().reset_index()

                    if not daily_summary.empty:
                        # 온도 + 습도 한 plot
                        has_temp = "temperature" in env_cols
                        has_hum  = "humidity"  in env_cols
                        has_ph   = "ph"        in env_cols
                        has_ec   = "ec"        in env_cols

                        if has_temp or has_hum:
                            fig = make_subplots(
                                rows=1, cols=1,
                                subplot_titles="날짜별 온도·습도 변화",
                            )
                            if has_temp:
                                fig.add_trace(
                                    go.Scatter(
                                        x=daily_summary["date"],
                                        y=daily_summary["temperature"],
                                        mode="lines+markers",
                                        name="온도 (℃)",
                                        line=dict(color="#e74c3c", width=2),
                                    ),
                                    row=1, col=1,
                                )
                            if has_hum:
                                fig.add_trace(
                                    go.Scatter(
                                        x=daily_summary["date"],
                                        y=daily_summary["humidity"],
                                        mode="lines+markers",
                                        name="습도 (%)",
                                        line=dict(color="#3498db", width=2),
                                    ),
                                    row=1, col=1,
                                )
                            fig.update_xaxes(title_text="날짜")
                            fig.update_yaxes(title_text="온도 (℃) / 습도 (%)")
                            plotly_font(fig)
                            st.plotly_chart(fig, width="stretch")

                        if has_ph or has_ec:
                            fig2 = make_subplots(
                                rows=1, cols=1,
                                subplot_titles="날짜별 pH·EC 변화",
                            )
                            if has_ph:
                                fig2.add_trace(
                                    go.Scatter(
                                        x=daily_summary["date"],
                                        y=daily_summary["ph"],
                                        mode="lines+markers",
                                        name="pH",
                                        line=dict(color="#27ae60", width=2),
                                    ),
                                    row=1, col=1,
                                )
                            if has_ec:
                                fig2.add_trace(
                                    go.Scatter(
                                        x=daily_summary["date"],
                                        y=daily_summary["ec"],
                                        mode="lines+markers",
                                        name="EC (mS/cm)",
                                        line=dict(color="#8e44ad", width=2),
                                    ),
                                    row=1, col=1,
                                )
                            fig2.update_xaxes(title_text="날짜")
                            fig2.update_yaxes(title_text="pH / EC (mS/cm)")
                            plotly_font(fig2)
                            st.plotly_chart(fig2, width="stretch")
                    else:
                        st.info("일별 집계에 사용할 데이터가 충분하지 않습니다.")
                else:
                    st.info("시간 열이 없거나 유효한 날짜가 없어서 시계열을 그리지 못했습니다.")

                with st.expander("📄 환경 데이터 원본 테이블 + CSV 다운로드"):
                    st.dataframe(env_df, width="stretch")
                    st.download_button(
                        label="📥 환경 CSV 다운로드",
                        data=csv_bytes(env_df),
                        file_name=f"{school_env}_환경_정제.csv" if school_env else "환경_정제.csv",
                        mime="text/csv",
                    )
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")

# ================================================================
#  Tab 3 — 생육 결과
# ================================================================
with tab3:
    try:
        if growth_df.empty:
            st.info("📊 생육 결과 CSV를 업로드하면 이 탭의 내용이 채워집니다.")
        else:
            growth_cols_avail = [c for c in growth_cols if c in growth_df.columns]

            st.header("📊 생육 결과 분석")

            # ── 핵심 결과 카드 ──
            if "생중량" in growth_df.columns:
                g = growth_df["생중량"].dropna()
                if len(g) >= 2:
                    gmean = g.mean()
                    gmax_idx = g.idxmax()
                    gmin_idx = g.idxmin()
                    # 개체번호는 원본 growth_df에서 그대로 읽음
                    max_id = growth_df.loc[gmax_idx, "개체번호"]
                    min_id = growth_df.loc[gmin_idx, "개체번호"]
                    st.subheader("🥇 핵심 결과")
                    kc1, kc2, kc3 = st.columns(3)
                    kc1.metric("평균 생중량", f"{gmean:.2f}g")
                    kc2.metric("최대 생중량", f"{g.max():.2f}g  (개체 {max_id})")
                    kc3.metric("최소 생중량", f"{g.min():.2f}g  (개체 {min_id})")
                else:
                    st.info("생중량 데이터를 계산할 만큼 충분하지 않습니다.")
            else:
                st.info("⚠️ 생육 CSV에 '생중량' 열이 없습니다. "
                        "지상부 질량 + 지하부 질량으로 자동 계산되었습니다.")

            st.markdown("---")

            # ── 개체별 생육 비교 (막대 그래프) ──
            st.subheader("📊 개체별 생육 비교 (막대 그래프)")

            plot_targets = []
            label_map = {
                "생중량":     "생중량 (g)",
                "잎 수":      "잎 수 (장)",
                "지상부 길이":"지상부 길이 (mm)",
                "지하부 길이":"지하부 길이 (mm)",
                "지상부 질량":"지상부 질량 (g)",
                "지하부 질량":"지하부 질량 (g)",
            }
            for col_key in ["생중량", "잎 수", "지상부 길이", "지하부 길이"]:
                if col_key in growth_df.columns:
                    plot_targets.append((col_key, label_map[col_key]))

            if not plot_targets:
                st.info("표시할 생육 측정 항목이 없습니다. 사이드바에서 항목을 선택하거나 CSV를 확인하세요.")
            else:
                rows = len(plot_targets)
                fig_bar = make_subplots(
                    rows=rows, cols=1,
                    subplot_titles=[f"개체별 {lbl}" for _, lbl in plot_targets],
                    vertical_spacing=0.12,
                )
                colors_use = ["#2ecc71", "#3498db", "#e67e22", "#9b59b6"]

                for i, (col_key, lbl) in enumerate(plot_targets, start=1):
                    s = growth_df.set_index("개체번호")[col_key].dropna().sort_values(ascending=False)
                    if len(s) < 2:
                        continue
                    # 상위 25%, 하위 25% 기준
                    n = len(s)
                    q75 = s.quantile(0.75)
                    q25 = s.quantile(0.25)
                    bar_colors = []
                    for idx_val, val in s.items():
                        if val >= q75:
                            bar_colors.append("#27ae60")   # 상위
                        elif val <= q25:
                            bar_colors.append("#e74c3c")   # 하위
                        else:
                            bar_colors.append(colors_use[i % 4])
                    fig_bar.add_trace(
                        go.Bar(
                            x=s.index.astype(str),
                            y=s.values,
                            name=lbl,
                            marker_color=bar_colors,
                            hovertemplate=f"{lbl}: %{{y:.1f}}<extra>{s.index[-1]}</extra>",
                        ),
                        row=i, col=1,
                    )
                    fig_bar.update_yaxes(title_text=lbl, row=i, col=1)
                    fig_bar.update_xaxes(
                        title_text="개체번호",
                        tickangle=45,
                        row=i, col=1,
                    )

                plotly_font(fig_bar)
                st.plotly_chart(fig_bar, width="stretch")
                st.caption("🟢 초록 = 생중량 상위 25%   🔴 빨강 = 하위 25%")

            st.markdown("---")

            # ── 생중량 분포 (박스플롯) ──
            if "생중량" in growth_df.columns:
                g = growth_df["생중량"].dropna()
                if len(g) >= 3:
                    st.subheader("📦 생중량 분포 (박스플롯)")
                    fig_box = go.Figure()
                    fig_box.add_trace(
                        go.Box(
                            y=g.values,
                            name="생중량",
                            fillcolor="#3498db",
                            boxpoints="outliers",
                            marker=dict(color="#2c3e50", size=6),
                        )
                    )
                    q1, med, q3 = np.percentile(g, [25, 50, 75])
                    fig_box.add_annotation(
                        x=0.5, y=med,
                        text=f"중앙값: {med:.2f}g",
                        showarrow=True,
                        arrowhead=2,
                        ax=0, ay=-30,
                        font=dict(size=11),
                    )
                    fig_box.update_layout(
                        yaxis_title="생중량 (g)",
                        height=300,
                    )
                    plotly_font(fig_box)
                    st.plotly_chart(fig_box, width="stretch")

                    # 통계 요약
                    s = growth_df["생중량"].dropna()
                    if len(s) >= 2:
                        mean_v  = s.mean()
                        std_v   = s.std(ddof=1)
                        cv_v    = (std_v / mean_v) if mean_v > 0 else float("nan")
                        stat_rows = [{
                            "통계량": "평균",
                            "값": f"{mean_v:.2f}g",
                        }, {
                            "통계량": "표준편차",
                            "값": f"{std_v:.2f}g",
                        }, {
                            "통계량": "변동계수 (CV)",
                            "값": f"{cv_v:.3f} ({cv_v*100:.1f}%)",
                        }, {
                            "통계량": "범위",
                            "값": f"{s.min():.2f} ~ {s.max():.2f}g",
                        }]
                        st.table(pd.DataFrame(stat_rows))
                        st.caption(
                            "*표준편차*: 값이 평균에서 얼마나 퍼져 있는지 나타내는 지표입니다.\n"
                            "*CV(변동계수)*: 표준편차를 평균으로 나눈 값으로, 단위가 다른 그룹끼리 비교할 때 유용합니다.",
                        )
                else:
                    st.info("생중량 분포를 그리기에는 데이터가 부족합니다.")
            else:
                st.info("⚠️ 생중량 열이 없어서 분포 그래프를 표시할 수 없습니다.")

            st.markdown("---")

            # ── 상관관계 분석 (산점도 + 추세선) ──
            st.subheader("🔗 상관관계 분석 (산점도 + 추세선)")
            corr_pairs = []
            for x_key in ["잎 수", "지상부 길이"]:
                if x_key in growth_df.columns and "생중량" in growth_df.columns:
                    corr_pairs.append((x_key, "생중량",
                                       f"{label_map[x_key]} vs 생중량"))

            if not corr_pairs:
                st.info("상관계수를 계산할 측정 항목 조합이 없습니다.")
            else:
                for x_key, y_key, title in corr_pairs:
                    tmp = growth_df[[x_key, y_key]].dropna()
                    if len(tmp) < 2:
                        st.info(f"'{x_key}'와 '생중량' 데이터가 충분하지 않아 산점도를 그리지 못했습니다.")
                        continue

                    x_arr = tmp[x_key].values
                    y_arr = tmp[y_key].values
                    r, p = np.polyfit(x_arr, y_arr, 1)  # 기울기 r, 절편 p
                    y_line = r * x_arr + p

                    # 피어슨 상관계수
                    valid = tmp.dropna()
                    if len(valid) >= 3:
                        pearson_r = np.corrcoef(valid[x_key], valid[y_key])[0, 1]
                    else:
                        pearson_r = float("nan")

                    fig_sc = go.Figure()
                    fig_sc.add_trace(
                        go.Scatter(
                            x=x_arr,
                            y=y_arr,
                            mode="markers",
                            marker=dict(
                                size=8,
                                color="#3498db",
                                line=dict(width=1, color="#2c3e50"),
                            ),
                            name="개체 데이터",
                            hovertemplate=f"{x_key}: %{{x:.1f}}<br>{y_key}: %{{y:.2f}}<extra></extra>",
                        )
                    )
                    fig_sc.add_trace(
                        go.Scatter(
                            x=x_arr,
                            y=y_line,
                            mode="lines",
                            name=f"추세선 (r={pearson_r:.3f})",
                            line=dict(color="#e74c3c", dash="dash", width=2),
                        )
                    )
                    fig_sc.update_layout(
                        title=f"{title}  (상관계수 r = {pearson_r:.3f})",
                        xaxis_title=label_map[x_key],
                        yaxis_title="생중량 (g)",
                        height=380,
                    )
                    plotly_font(fig_sc)
                    st.plotly_chart(fig_sc, width="stretch")

                    if np.isnan(pearson_r):
                        st.info("상관계수를 계산할 데이터가 충분하지 않습니다.")
                    else:
                        strength = (
                            "매우 강한 양의 상관" if pearson_r >= 0.7 else
                            "중간 정도의 양의 상관" if pearson_r >= 0.4 else
                            "약한 관계" if pearson_r >= 0 else
                            "약한 음의 관계" if pearson_r >= -0.4 else
                            "중간 정도의 음의 상관" if pearson_r >= -0.7 else
                            "매우 강한 음의 상관"
                        )
                        st.markdown(
                            f"**{x_key} vs 생중량**\n"
                            f"- 피어슨 상관계수 r = **{pearson_r:.3f}**\n"
                            f"- 해석: {strength}\n"
                            f"- *상관계수 r*은 -1에서 1 사이 값으로, 1에 가까울수록 한 값이 커질 때 "
                            f"다른 값도 함께 커지는 경향이 강함을 뜻합니다.",
                        )

            with st.expander("📄 생육 데이터 원본 + CSV 다운로드"):
                st.dataframe(growth_df, width="stretch")
                st.download_button(
                    label="📥 생육 CSV 다운로드",
                    data=csv_bytes(growth_df),
                    file_name=f"{school_growth}_생육_정제.csv" if school_growth else "생육_정제.csv",
                    mime="text/csv",
                )
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")
