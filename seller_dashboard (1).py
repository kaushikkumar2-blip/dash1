"""
Seller Performance Dashboard — Streamlit App (2 pages)
=======================================================
Page 1 : Overall Metric — Seller-wise breach performance (table-first, coloured)
Page 2 : Daily Trends — Daily breach tables, rankings, trend selector

Run with:
    streamlit run "seller_dashboard (1).py"

Requirements:
    pip install streamlit plotly pandas numpy
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Seller Breach Performance",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
/* Extra top padding so page tabs (Overall metric / Daily metric) don't overlap the white header bar */
.block-container { padding: 2.25rem 2rem 2rem 2rem; }

.kpi-card {
    background: white; border-radius: 10px; padding: 0.75rem 1rem;
    border: 1px solid #E4E7EC; border-top: 3px solid #1D4ED8;
    margin-bottom: 4px;
}
.kpi-card.green  { border-top-color: #15803D; }
.kpi-card.orange { border-top-color: #EA580C; }
.kpi-card.red    { border-top-color: #B91C1C; }
.kpi-card.purple { border-top-color: #6D28D9; }

.kpi-label { font-size: 0.65rem; font-weight: 600; color: #98A2B3;
             letter-spacing: 0.07em; text-transform: uppercase; margin-bottom: 4px; }
.kpi-value { font-size: 1.35rem; font-weight: 700; color: #101828;
             line-height: 1; font-family: 'IBM Plex Mono', monospace; }
.kpi-sub   { font-size: 0.68rem; color: #98A2B3; margin-top: 2px; }

.delta-up   { background: #DCFCE7; color: #15803D; border-radius: 4px;
              padding: 2px 6px; font-size: 0.75rem; font-weight: 600; }
.delta-down { background: #FEE2E2; color: #B91C1C; border-radius: 4px;
              padding: 2px 6px; font-size: 0.75rem; font-weight: 600; }
.delta-flat { background: #F1F5F9; color: #64748B; border-radius: 4px;
              padding: 2px 6px; font-size: 0.75rem; font-weight: 600; }

/* Table styling */
.dataframe thead th { background: #1E3A5F !important; color: #fff !important; font-weight: 600 !important; }
.dataframe tbody tr:nth-child(even) { background: #F8FAFC !important; }
.dataframe tbody tr:hover { background: #EFF6FF !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
METRIC_CONFIG = {
    "ZRTO %":   {"thresh": 1.5,  "risk": True,  "decimals": 2, "color": "#B91C1C"},
    "FAC %":    {"thresh": 70.0, "risk": False, "decimals": 1, "color": "#6D28D9"},
    "Breach %": {"thresh": 10.0, "risk": True,  "decimals": 1, "color": "#EA580C"},
    "Conv %":   {"thresh": 65.0, "risk": False, "decimals": 1, "color": "#1D4ED8"},
}
PALETTE = ["#1D4ED8", "#EA580C", "#15803D", "#6D28D9", "#0891B2"]


def _hex_to_rgba(hex_str: str, alpha: float = 0.08) -> str:
    """Convert 6-digit hex to rgba string for Plotly (does not accept 8-digit hex)."""
    h = hex_str.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING & METRIC HELPERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_raw(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["payment_type_norm"] = (
        df["payment_type"].str.upper().map({"COD": "COD", "PREPAID": "Prepaid"})
    )
    df["reporting_date"] = df["reporting_date"].astype(str)
    return df


def safe_div(num, den, scale=100):
    return (num / den * scale) if den else 0


def calculate_summary_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    tv  = df["PHin"].sum()
    cod = df[df["payment_type_norm"] == "COD"]
    pp  = df[df["payment_type_norm"] == "Prepaid"]
    cv, pv = cod["PHin"].sum(), pp["PHin"].sum()
    td  = df["conv_num"].sum()
    pd_ = pp["conv_num"].sum()
    cd  = cod["conv_num"].sum()
    fn  = df["First_attempt_delivered"].sum()
    fd  = df["fac_deno"].sum()
    bn  = df["Breach_Num"].sum()
    bd  = df["Breach_Den"].sum()
    zn  = df["zero_attempt_num"].sum()
    return {
        "Volume":               tv,
        "COD Volume":           cv,
        "Prepaid Volume":       pv,
        "Delivered":            td,
        "COD Share %":          safe_div(cv, tv),
        "Prepaid Share %":      safe_div(pv, tv),
        "Overall Conversion %": safe_div(td, tv),
        "Prepaid Conversion %": safe_div(pd_, pv),
        "COD Conversion %":     safe_div(cd, cv),
        "FAC %":                safe_div(fn, fd),
        "Breach %":             safe_div(bn, bd),
        "ZRTO %":               safe_div(zn, tv),
    }


@st.cache_data
def build_seller_table(df: pd.DataFrame) -> pd.DataFrame:
    agg = df.groupby("seller_type").agg(
        PHin=("PHin", "sum"),
        conv_num=("conv_num", "sum"),
        First_attempt_delivered=("First_attempt_delivered", "sum"),
        fac_deno=("fac_deno", "sum"),
        Breach_Num=("Breach_Num", "sum"),
        Breach_Den=("Breach_Den", "sum"),
        zero_attempt_num=("zero_attempt_num", "sum"),
    ).reset_index()

    cod = (
        df[df["payment_type_norm"] == "COD"]
        .groupby("seller_type")
        .agg(cod_vol=("PHin", "sum"), cod_conv=("conv_num", "sum"))
        .reset_index()
    )
    pp = (
        df[df["payment_type_norm"] == "Prepaid"]
        .groupby("seller_type")
        .agg(pp_vol=("PHin", "sum"), pp_conv=("conv_num", "sum"))
        .reset_index()
    )

    r = (
        agg
        .merge(cod, on="seller_type", how="left")
        .merge(pp,  on="seller_type", how="left")
        .fillna(0)
    )
    nan = float("nan")

    r["Overall Conversion %"] = (r["conv_num"]               / r["PHin"].replace(0, nan) * 100).round(2)
    r["COD Conversion %"]     = (r["cod_conv"]               / r["cod_vol"].replace(0, nan) * 100).round(2)
    r["Prepaid Conversion %"] = (r["pp_conv"]                / r["pp_vol"].replace(0, nan) * 100).round(2)
    r["FAC %"]                = (r["First_attempt_delivered"] / r["fac_deno"].replace(0, nan) * 100).round(2)
    r["Breach %"]             = (r["Breach_Num"]             / r["Breach_Den"].replace(0, nan) * 100).round(2)
    r["ZRTO %"]               = (r["zero_attempt_num"]        / r["PHin"].replace(0, nan) * 100).round(2)
    r["COD Share %"]          = (r["cod_vol"]                / r["PHin"].replace(0, nan) * 100).round(2)
    r["Prepaid Share %"]      = (r["pp_vol"]                 / r["PHin"].replace(0, nan) * 100).round(2)

    return r.fillna(0).sort_values("PHin", ascending=False)


@st.cache_data
def build_daily_table(df: pd.DataFrame) -> pd.DataFrame:
    daily = df.groupby(["reporting_date", "seller_type"]).agg(
        PHin=("PHin", "sum"),
        conv_num=("conv_num", "sum"),
        zero_attempt_num=("zero_attempt_num", "sum"),
        First_attempt_delivered=("First_attempt_delivered", "sum"),
        fac_deno=("fac_deno", "sum"),
        Breach_Num=("Breach_Num", "sum"),
        Breach_Den=("Breach_Den", "sum"),
    ).reset_index()

    nan = float("nan")
    daily["ZRTO %"]   = (daily["zero_attempt_num"]        / daily["PHin"].replace(0, nan) * 100).round(2)
    daily["FAC %"]    = (daily["First_attempt_delivered"] / daily["fac_deno"].replace(0, nan) * 100).round(2)
    daily["Breach %"] = (daily["Breach_Num"]              / daily["Breach_Den"].replace(0, nan) * 100).round(2)
    daily["Conv %"]   = (daily["conv_num"]                / daily["PHin"].replace(0, nan) * 100).round(2)

    return daily.fillna(0).sort_values("reporting_date")


def fmt_date(s: str) -> str:
    return f"{s[4:6]}/{s[6:8]}" if len(s) == 8 else s


# ── Table colour helpers (risk = lower is better, e.g. Breach %, ZRTO %)
def _color_breach(v):
    if pd.isna(v) or v == 0: return "background-color:#F1F5F9;color:#475569;"
    if v <= 5: return "background-color:#DCFCE7;color:#166534;font-weight:600;"
    if v <= 10: return "background-color:#FEF9C3;color:#854D0E;font-weight:600;"
    return "background-color:#FEE2E2;color:#991B1B;font-weight:700;"


def _color_zrto(v):
    if pd.isna(v) or v == 0: return "background-color:#F1F5F9;color:#475569;"
    if v <= 1.5: return "background-color:#DCFCE7;color:#166534;font-weight:600;"
    if v <= 3: return "background-color:#FEF9C3;color:#854D0E;font-weight:600;"
    return "background-color:#FEE2E2;color:#991B1B;font-weight:700;"


def _color_conv_fac(v):
    if pd.isna(v): return ""
    if v >= 70: return "background-color:#DCFCE7;color:#166534;font-weight:600;"
    if v >= 50: return "background-color:#FEF9C3;color:#854D0E;font-weight:600;"
    return "background-color:#FEE2E2;color:#991B1B;font-weight:600;"


def _color_volume(v):
    if pd.isna(v) or v == 0: return "background-color:#F8FAFC;color:#64748B;"
    return "background-color:#E0F2FE;color:#0369A1;font-weight:500;"


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📦 Seller Dashboard")
    st.divider()
    data_path = st.text_input("CSV file path", value="7febf8a8c08b66c779f7b45bf5b9a826.csv")
    st.divider()
    st.markdown("### Global Filters")

try:
    raw_df = load_raw(data_path)
except FileNotFoundError:
    st.error(f"File not found: `{data_path}`. Update the path in the sidebar.")
    st.stop()

seller_list = sorted(raw_df["seller_type"].unique())

with st.sidebar:
    selected_sellers = st.multiselect("Seller Types", options=seller_list, default=seller_list)
    payment_filter   = st.radio("Payment Type", ["All", "COD", "Prepaid"], index=0)
    min_vol          = st.slider(
        "Min Volume (PHin)", 0,
        max(1, int(raw_df["PHin"].sum() // max(len(seller_list), 1))),
        0, step=100,
    )
    st.divider()
    st.markdown(
        f"<span style='font-size:0.75rem;color:#98A2B3;'>"
        f"{len(seller_list)} sellers · "
        f"{raw_df['reporting_date'].nunique()} days</span>",
        unsafe_allow_html=True,
    )

# Apply global filters
filtered_df = raw_df[raw_df["seller_type"].isin(selected_sellers)]
if payment_filter != "All":
    filtered_df = filtered_df[filtered_df["payment_type_norm"] == payment_filter]

seller_table = build_seller_table(filtered_df)
seller_table = seller_table[seller_table["PHin"] >= min_vol]
daily_df     = build_daily_table(filtered_df)
overall      = calculate_summary_metrics(filtered_df)

dates   = sorted(daily_df["reporting_date"].unique())
sellers = sorted(daily_df["seller_type"].unique())

# ─────────────────────────────────────────────────────────────────────────────
# PAGE NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────
page = st.radio(
    "Page",
    ["📊 Overall Metric", "📈 Daily Trends"],
    horizontal=True,
    label_visibility="collapsed",
)
st.divider()


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE 1 — OVERALL METRIC (SELLER-WISE BREACH PERFORMANCE)
# ═════════════════════════════════════════════════════════════════════════════
if page == "📊 Overall Metric":

    # Date range filter (calendar-like dropdown) for breach report
    date_strs = sorted(filtered_df["reporting_date"].unique())
    try:
        min_d = datetime.strptime(min(date_strs), "%Y%m%d").date()
        max_d = datetime.strptime(max(date_strs), "%Y%m%d").date()
    except (ValueError, TypeError):
        min_d = max_d = datetime.now().date()

    st.caption("Select date range for the report")
    col_cal1, col_cal2 = st.columns(2)
    with col_cal1:
        start_date = st.date_input("From", value=min_d, min_value=min_d, max_value=max_d, key="breach_start")
    with col_cal2:
        end_date = st.date_input("To", value=max_d, min_value=min_d, max_value=max_d, key="breach_end")
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    date_filtered_df = filtered_df[
        (filtered_df["reporting_date"] >= start_str) & (filtered_df["reporting_date"] <= end_str)
    ]
    seller_table = build_seller_table(date_filtered_df)
    seller_table = seller_table[seller_table["PHin"] >= min_vol]
    overall = calculate_summary_metrics(date_filtered_df)

    st.markdown(
        f"<div style='font-size:0.82rem;color:#64748B;margin-bottom:12px;'>"
        f"Showing <b>{len(seller_table)}</b> seller types · "
        f"Volume ≥ {min_vol:,} · Payment: {payment_filter} · "
        f"Date range: {start_date} to {end_date}</div>",
        unsafe_allow_html=True,
    )

    # ── Compact KPI Row ───────────────────────────────────────────────────────
    kpi_cols = st.columns(5)
    kpis = [
        ("Total Volume", f"{int(overall.get('Volume', 0)):,}", "PHin", ""),
        ("Breach %",     f"{overall.get('Breach %', 0):.1f}%", "SLA breach rate", "red"),
        ("ZRTO %",       f"{overall.get('ZRTO %', 0):.2f}%",  "Zero-attempt", "red"),
        ("FAC %",        f"{overall.get('FAC %', 0):.1f}%",   "1st attempt", "orange"),
        ("Conv %",       f"{overall.get('Overall Conversion %', 0):.1f}%", "Conversion", "green"),
    ]
    for col, (label, val, sub, cls) in zip(kpi_cols, kpis):
        with col:
            st.markdown(
                f'<div class="kpi-card {cls}">'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{val}</div>'
                f'<div class="kpi-sub">{sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Main: Seller-wise detailed breach performance table ───────────────────
    st.markdown("### 📋 Seller-wise Breach Performance Report")
    st.caption(
        "**Colour legend:** 🟢 Green = good (Breach % ≤5%, ZRTO % ≤1.5%, Conv/FAC ≥70%) · "
        "🟡 Amber = caution · 🔴 Red = alert. Sort by any column."
    )

    search = st.text_input(
        "Search seller", placeholder="🔍 Search seller type…", label_visibility="collapsed", key="search_breach"
    )

    breach_report_cols = [
        "seller_type", "PHin", "conv_num", "Breach_Num", "Breach_Den",
        "Breach %", "FAC %", "ZRTO %",
        "Overall Conversion %", "COD Conversion %", "Prepaid Conversion %",
        "COD Share %", "Prepaid Share %",
    ]
    breach_report = seller_table[breach_report_cols].rename(columns={
        "seller_type": "Seller",
        "PHin": "Volume",
        "conv_num": "Delivered",
        "Breach_Num": "Breach #",
        "Breach_Den": "Breach Den",
    })
    if search:
        breach_report = breach_report[breach_report["Seller"].str.upper().str.contains(search.upper())]

    styled_breach = (
        breach_report.style
        .map(_color_breach, subset=["Breach %"])
        .map(_color_zrto, subset=["ZRTO %"])
        .map(_color_conv_fac, subset=["FAC %", "Overall Conversion %", "COD Conversion %", "Prepaid Conversion %"])
        .map(_color_volume, subset=["Volume", "Delivered", "Breach #", "Breach Den"])
        .format({
            "Volume": "{:,.0f}",
            "Delivered": "{:,.0f}",
            "Breach #": "{:,.0f}",
            "Breach Den": "{:,.0f}",
            "Breach %": "{:.1f}%",
            "FAC %": "{:.1f}%",
            "ZRTO %": "{:.2f}%",
            "Overall Conversion %": "{:.1f}%",
            "COD Conversion %": "{:.1f}%",
            "Prepaid Conversion %": "{:.1f}%",
            "COD Share %": "{:.1f}%",
            "Prepaid Share %": "{:.1f}%",
        })
    )
    st.dataframe(styled_breach, use_container_width=True, height=420)

    st.divider()

    # ── Top / Worst breach tables (table-only, no charts) ─────────────────────
    st.markdown("### ⚠️ Breach focus — Best vs Worst sellers")
    min_vol_rank = 500
    rank_df = seller_table[seller_table["PHin"] >= min_vol_rank].copy()
    rank_df = rank_df[rank_df["Breach_Den"] > 0].sort_values("Breach %", ascending=True)

    col_best, col_worst = st.columns(2)

    with col_best:
        st.markdown("#### 🟢 Best 10 — Lowest Breach %")
        best_breach = rank_df.head(10)[["seller_type", "PHin", "Breach_Num", "Breach_Den", "Breach %", "FAC %", "ZRTO %"]]
        best_breach = best_breach.rename(columns={"seller_type": "Seller", "PHin": "Volume"})
        styled_best = (
            best_breach.style
            .map(_color_breach, subset=["Breach %"])
            .map(_color_zrto, subset=["ZRTO %"])
            .map(_color_conv_fac, subset=["FAC %"])
            .map(_color_volume, subset=["Volume", "Breach_Num", "Breach_Den"])
            .format({"Volume": "{:,.0f}", "Breach_Num": "{:,.0f}", "Breach_Den": "{:,.0f}", "Breach %": "{:.1f}%", "FAC %": "{:.1f}%", "ZRTO %": "{:.2f}%"})
        )
        st.dataframe(styled_best, use_container_width=True, height=320)

    with col_worst:
        st.markdown("#### 🔴 Worst 10 — Highest Breach %")
        worst_breach = rank_df.tail(10).iloc[::-1][["seller_type", "PHin", "Breach_Num", "Breach_Den", "Breach %", "FAC %", "ZRTO %"]]
        worst_breach = worst_breach.rename(columns={"seller_type": "Seller", "PHin": "Volume"})
        styled_worst = (
            worst_breach.style
            .map(_color_breach, subset=["Breach %"])
            .map(_color_zrto, subset=["ZRTO %"])
            .map(_color_conv_fac, subset=["FAC %"])
            .map(_color_volume, subset=["Volume", "Breach_Num", "Breach_Den"])
            .format({"Volume": "{:,.0f}", "Breach_Num": "{:,.0f}", "Breach_Den": "{:,.0f}", "Breach %": "{:.1f}%", "FAC %": "{:.1f}%", "ZRTO %": "{:.2f}%"})
        )
        st.dataframe(styled_worst, use_container_width=True, height=320)

    st.divider()
    st.markdown("#### 📊 ZRTO % — Sellers needing attention (table)")
    zrto_alert = seller_table[seller_table["PHin"] >= min_vol_rank].sort_values("ZRTO %", ascending=False).head(15)
    zrto_disp = zrto_alert[["seller_type", "PHin", "zero_attempt_num", "ZRTO %", "Breach %", "FAC %"]].rename(
        columns={"seller_type": "Seller", "PHin": "Volume", "zero_attempt_num": "ZRTO #"}
    )
    styled_zrto = (
        zrto_disp.style
        .map(_color_zrto, subset=["ZRTO %"])
        .map(_color_breach, subset=["Breach %"])
        .map(_color_conv_fac, subset=["FAC %"])
        .map(_color_volume, subset=["Volume", "ZRTO #"])
        .format({"Volume": "{:,.0f}", "ZRTO #": "{:,.0f}", "ZRTO %": "{:.2f}%", "Breach %": "{:.1f}%", "FAC %": "{:.1f}%"})
    )
    st.dataframe(styled_zrto, use_container_width=True, height=340)


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE 2 — DAILY TRENDS
# ═════════════════════════════════════════════════════════════════════════════
else:
    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 1 — Daily Seller Count: rows = metrics, columns = dates/weeks/months, cell = N↑, M↓
    # ─────────────────────────────────────────────────────────────────────────
    compare_mode = st.radio(
        "Compare",
        ["Day wise compare", "Weekly compare", "Monthly compare"],
        horizontal=True,
        label_visibility="collapsed",
        key="daily_compare_mode",
    )

    st.markdown("#### 📅 Daily Seller Count")
    if compare_mode == "Day wise compare":
        st.caption("↑ improved vs previous day · ↓ declined. First date has no prior day.")
    elif compare_mode == "Weekly compare":
        st.caption("↑ improved vs previous week · ↓ declined. First week has no prior week.")
    else:
        st.caption("↑ improved vs previous month · ↓ declined. First month has no prior month.")

    _metric_to_col = {"Volume": "PHin", "Delivered": "conv_num"}
    row_metrics = ["ZRTO %", "FAC %", "Breach %", "Conv %"]
    risk_flags = [True, False, True, False]
    nan = float("nan")

    if compare_mode == "Day wise compare":
        def _improved_declined_for_metric(m, is_risk_metric):
            col = _metric_to_col.get(m, m)
            row_cells = []
            for i, dt in enumerate(dates):
                if i == 0:
                    row_cells.append("—")
                    continue
                prev_dt = dates[i - 1]
                curr = daily_df[daily_df["reporting_date"] == dt][["seller_type", col]].rename(columns={col: "v"})
                prev = daily_df[daily_df["reporting_date"] == prev_dt][["seller_type", col]].rename(columns={col: "v_prev"})
                merged = curr.merge(prev, on="seller_type", how="inner")
                if is_risk_metric:
                    improved = (merged["v"] < merged["v_prev"]).sum()
                    declined = (merged["v"] > merged["v_prev"]).sum()
                else:
                    improved = (merged["v"] > merged["v_prev"]).sum()
                    declined = (merged["v"] < merged["v_prev"]).sum()
                improved, declined = int(improved), int(declined)
                parts = [f"{improved}↑"] if improved > 0 else []
                if declined > 0:
                    parts.append(f"{declined}↓")
                row_cells.append(", ".join(parts) if parts else "—")
            return row_cells

        period_labels = [fmt_date(d) for d in dates]
        table_data = {m: _improved_declined_for_metric(m, risk) for m, risk in zip(row_metrics, risk_flags)}
    else:
        # Weekly or Monthly: build period-level aggregates per seller, then improved/declined vs previous period
        daily_df_copy = daily_df.copy()
        daily_df_copy["_dt"] = daily_df_copy["reporting_date"].apply(
            lambda s: datetime.strptime(str(s), "%Y%m%d") if len(str(s)) == 8 else datetime.now()
        )
        if compare_mode == "Weekly compare":
            daily_df_copy["_period"] = daily_df_copy["_dt"].apply(lambda d: d.strftime("%Y-W%W"))
        else:
            daily_df_copy["_period"] = daily_df_copy["_dt"].apply(lambda d: d.strftime("%Y-%m"))

        period_agg = (
            daily_df_copy
            .groupby(["_period", "seller_type"])
            .agg(
                PHin=("PHin", "sum"),
                conv_num=("conv_num", "sum"),
                zero_attempt_num=("zero_attempt_num", "sum"),
                First_attempt_delivered=("First_attempt_delivered", "sum"),
                fac_deno=("fac_deno", "sum"),
                Breach_Num=("Breach_Num", "sum"),
                Breach_Den=("Breach_Den", "sum"),
            )
            .reset_index()
        )
        period_agg["ZRTO %"] = (period_agg["zero_attempt_num"] / period_agg["PHin"].replace(0, nan) * 100).round(2)
        period_agg["FAC %"] = (period_agg["First_attempt_delivered"] / period_agg["fac_deno"].replace(0, nan) * 100).round(2)
        period_agg["Breach %"] = (period_agg["Breach_Num"] / period_agg["Breach_Den"].replace(0, nan) * 100).round(2)
        period_agg["Conv %"] = (period_agg["conv_num"] / period_agg["PHin"].replace(0, nan) * 100).round(2)
        period_agg = period_agg.fillna(0)
        periods = sorted(period_agg["_period"].unique())

        def _improved_declined_period(m, is_risk_metric):
            col = _metric_to_col.get(m, m)
            row_cells = []
            for i, period in enumerate(periods):
                if i == 0:
                    row_cells.append("—")
                    continue
                prev_period = periods[i - 1]
                curr = period_agg[period_agg["_period"] == period][["seller_type", col]].rename(columns={col: "v"})
                prev = period_agg[period_agg["_period"] == prev_period][["seller_type", col]].rename(columns={col: "v_prev"})
                merged = curr.merge(prev, on="seller_type", how="inner")
                if is_risk_metric:
                    improved = (merged["v"] < merged["v_prev"]).sum()
                    declined = (merged["v"] > merged["v_prev"]).sum()
                else:
                    improved = (merged["v"] > merged["v_prev"]).sum()
                    declined = (merged["v"] < merged["v_prev"]).sum()
                improved, declined = int(improved), int(declined)
                parts = [f"{improved}↑"] if improved > 0 else []
                if declined > 0:
                    parts.append(f"{declined}↓")
                row_cells.append(", ".join(parts) if parts else "—")
            return row_cells

        period_labels = periods
        table_data = {m: _improved_declined_period(m, risk) for m, risk in zip(row_metrics, risk_flags)}

    count_df = pd.DataFrame(table_data, index=period_labels).T
    count_df.index.name = "Metric"
    count_df = count_df.reset_index()

    st.dataframe(count_df, use_container_width=True, height=180)

    st.divider()

    st.markdown(
        f"<div style='font-size:0.82rem;color:#64748B;margin-bottom:12px;'>"
        f"{len(dates)} days · {len(sellers)} sellers · select a metric to explore all panels</div>",
        unsafe_allow_html=True,
    )
    metric  = st.radio(
        "Active Metric",
        list(METRIC_CONFIG.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )
    cfg     = METRIC_CONFIG[metric]
    thresh  = cfg["thresh"]
    is_risk = cfg["risk"]
    dec     = cfg["decimals"]

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 2 — Best & Worst rankings (tables with colours)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(f"#### 🏆 Best & Worst Sellers — {metric}")
    st.caption("Overall period · min volume 1,000 PHin")

    rank_agg = daily_df.groupby("seller_type").agg(
        PHin=("PHin", "sum"),
        zero_attempt_num=("zero_attempt_num", "sum"),
        First_attempt_delivered=("First_attempt_delivered", "sum"),
        fac_deno=("fac_deno", "sum"),
        Breach_Num=("Breach_Num", "sum"),
        Breach_Den=("Breach_Den", "sum"),
        conv_num=("conv_num", "sum"),
    ).reset_index()
    rank_agg = rank_agg[rank_agg["PHin"] >= 1000].copy()

    nan = float("nan")
    rank_agg["ZRTO %"]   = (rank_agg["zero_attempt_num"]        / rank_agg["PHin"].replace(0, nan) * 100).round(2)
    rank_agg["FAC %"]    = (rank_agg["First_attempt_delivered"] / rank_agg["fac_deno"].replace(0, nan) * 100).round(2)
    rank_agg["Breach %"] = (rank_agg["Breach_Num"]              / rank_agg["Breach_Den"].replace(0, nan) * 100).round(2)
    rank_agg["Conv %"]   = (rank_agg["conv_num"]                / rank_agg["PHin"].replace(0, nan) * 100).round(2)
    rank_agg = rank_agg.fillna(0)

    sorted_rank   = rank_agg.sort_values(metric, ascending=is_risk)
    # Build display columns with no duplicates (metric may be "Breach %", "FAC %", etc.)
    _pct_cols = [c for c in ["Breach %", "FAC %", "ZRTO %", "Conv %"] if c != metric]
    _display_cols = ["seller_type", "PHin", metric] + _pct_cols
    best_sellers  = sorted_rank.head(10)[_display_cols].copy()
    worst_sellers = sorted_rank.tail(10).iloc[::-1][_display_cols].copy()

    def _color_metric_val(v, risk=is_risk):
        if pd.isna(v): return ""
        if risk:  # lower is better
            if v <= (thresh * 0.5): return "background-color:#DCFCE7;color:#166534;font-weight:600;"
            if v <= thresh: return "background-color:#FEF9C3;color:#854D0E;font-weight:600;"
            return "background-color:#FEE2E2;color:#991B1B;font-weight:700;"
        else:  # higher is better
            if v >= thresh * 1.2: return "background-color:#DCFCE7;color:#166534;font-weight:600;"
            if v >= thresh: return "background-color:#FEF9C3;color:#854D0E;font-weight:600;"
            return "background-color:#FEE2E2;color:#991B1B;font-weight:600;"

    col_best, col_worst = st.columns(2)
    with col_best:
        best_label = f"🟢 Best 10 — {'Lowest' if is_risk else 'Highest'} {metric}"
        best_sellers = best_sellers.rename(columns={"seller_type": "Seller", "PHin": "Volume"})
        st.markdown(f"**{best_label}**")
        st_data_best = (
            best_sellers.style
            .map(_color_metric_val, subset=[metric])
            .map(_color_breach, subset=["Breach %"])
            .map(_color_zrto, subset=["ZRTO %"])
            .map(_color_conv_fac, subset=["FAC %", "Conv %"])
            .map(_color_volume, subset=["Volume"])
            .format({"Volume": "{:,.0f}", metric: f"{{:.{dec}f}}%", "Breach %": "{:.1f}%", "FAC %": "{:.1f}%", "ZRTO %": "{:.2f}%", "Conv %": "{:.1f}%"})
        )
        st.dataframe(st_data_best, use_container_width=True, height=320)

    with col_worst:
        worst_label = f"🔴 Worst 10 — {'Highest' if is_risk else 'Lowest'} {metric}"
        worst_sellers = worst_sellers.rename(columns={"seller_type": "Seller", "PHin": "Volume"})
        st.markdown(f"**{worst_label}**")
        st_data_worst = (
            worst_sellers.style
            .map(_color_metric_val, subset=[metric])
            .map(_color_breach, subset=["Breach %"])
            .map(_color_zrto, subset=["ZRTO %"])
            .map(_color_conv_fac, subset=["FAC %", "Conv %"])
            .map(_color_volume, subset=["Volume"])
            .format({"Volume": "{:,.0f}", metric: f"{{:.{dec}f}}%", "Breach %": "{:.1f}%", "FAC %": "{:.1f}%", "ZRTO %": "{:.2f}%", "Conv %": "{:.1f}%"})
        )
        st.dataframe(st_data_worst, use_container_width=True, height=320)

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 3 — Select two days to compare seller details
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("#### 📅 Compare two days — seller details")
    st.caption("Select two dates to compare seller IDs and metric values side by side.")

    date_options = [fmt_date(d) for d in dates]
    day_col1, day_col2 = st.columns(2)
    with day_col1:
        label1 = st.selectbox("Day 1", date_options, key="daily_day_1")
        date1 = dates[date_options.index(label1)]
    with day_col2:
        label2 = st.selectbox("Day 2", date_options, key="daily_day_2")
        date2 = dates[date_options.index(label2)]

    detail_cols = ["seller_type", "PHin", metric]

    def _build_day_table(dt):
        slice_df = daily_df[daily_df["reporting_date"] == dt][detail_cols].copy()
        slice_df = slice_df.rename(columns={"seller_type": "Seller ID", "PHin": "Volume"})
        return slice_df.sort_values(metric, ascending=is_risk)

    tab1_df = _build_day_table(date1)
    tab2_df = _build_day_table(date2)

    def _style_day_table(df):
        return (
            df.style
            .map(_color_volume, subset=["Volume"])
            .map(_color_metric_val, subset=[metric])
            .format({"Volume": "{:,.0f}", metric: f"{{:.{dec}f}}%"})
        )

    table_col1, table_col2 = st.columns(2)
    with table_col1:
        st.markdown(f"**{label1}**")
        st.dataframe(_style_day_table(tab1_df), use_container_width=True, height=400)
    with table_col2:
        st.markdown(f"**{label2}**")
        st.dataframe(_style_day_table(tab2_df), use_container_width=True, height=400)


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center;color:#98A2B3;font-size:0.72rem;'>"
    "Seller Performance Dashboard · Data refreshed on load</div>",
    unsafe_allow_html=True,
)
