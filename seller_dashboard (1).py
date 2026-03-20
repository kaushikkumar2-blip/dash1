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

/* Sticky first column: wrapper must be the scroll container (max-width + overflow-x) */
.sticky-table-wrap {
    overflow-x: auto;
    overflow-y: auto;
    max-width: 100%;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.sticky-table-wrap.no-vscroll {
    overflow-y: visible;
    max-height: none;
}
.sticky-table-wrap .sticky-table thead th:first-child,
.sticky-table-wrap .sticky-table tbody td:first-child,
.sticky-table-wrap .sticky-table tbody th:first-child {
    position: sticky !important;
    left: 0 !important;
    z-index: 2 !important;
    background: #1E3A5F !important;
    color: #fff !important;
    width: 100px !important;
    min-width: 100px !important;
    max-width: 100px !important;
    box-sizing: border-box !important;
    border-right: 2px solid rgba(255,255,255,0.3) !important;
    box-shadow: 4px 0 8px rgba(0,0,0,0.08) !important;
}
.sticky-table-wrap .sticky-table tbody tr:hover td:first-child,
.sticky-table-wrap .sticky-table tbody tr:hover th:first-child {
    background: #2d4a6f !important;
    color: #fff !important;
}
.sticky-table-wrap .sticky-table thead th:first-child {
    z-index: 3 !important;
}
.sticky-table {
    border-collapse: separate;
    border-spacing: 0;
    width: max-content;
    min-width: 100%;
    font-size: 0.85rem;
    font-family: 'IBM Plex Sans', sans-serif;
}
.sticky-table thead th {
    background: #1E3A5F;
    color: #fff;
    font-weight: 600;
    padding: 10px 14px;
    white-space: nowrap;
    position: sticky;
    top: 0;
    z-index: 1;
    border-bottom: 2px solid #0F172A;
}
.sticky-table thead th:first-child { z-index: 3 !important; }
.sticky-table tbody td {
    padding: 8px 14px;
    white-space: nowrap;
    border-bottom: 1px solid #F1F5F9;
}
.sticky-table tbody tr:nth-child(even) td { background: #fff; }
.sticky-table tbody tr:hover td { background: #EFF6FF; }
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


def render_sticky_table(df, max_height="400px", no_vscroll=False):
    """Render a DataFrame as an HTML table with a sticky first column (for horizontal scroll).
    If no_vscroll=True, no vertical scrollbar; table shows full height."""
    raw_html = df.to_html(index=True)
    table_html = raw_html.replace('class="dataframe"', 'class="sticky-table"')
    if "sticky-table" not in table_html:
        table_html = raw_html.replace("<table ", '<table class="sticky-table" ', 1)
    wrap_class = "sticky-table-wrap no-vscroll" if no_vscroll else "sticky-table-wrap"
    style = "" if no_vscroll else f"max-height:{max_height};"
    scoped_css = (
        "<style>"
        ".sticky-table-wrap .sticky-table th:first-child,"
        ".sticky-table-wrap .sticky-table td:first-child{"
        "position:sticky!important;left:0!important;z-index:2!important;"
        "background:#1E3A5F!important;color:#fff!important;"
        "width:100px!important;min-width:100px!important;"
        "box-sizing:border-box!important;"
        "border-right:2px solid rgba(255,255,255,0.3)!important;"
        "box-shadow:4px 0 8px rgba(0,0,0,0.08)!important;}"
        ".sticky-table-wrap .sticky-table thead th:first-child{z-index:3!important;}"
        "</style>"
    )
    st.markdown(
        f'<div class="{wrap_class}" style="{style}max-width:100%;">{scoped_css}{table_html}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT MAPPING (seller code → client name)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_client_map(path: str) -> dict:
    """Load seller-code → client-name mapping from CSV (with or without header)."""
    _HEADER_TOKENS = {
        "SELLERCODE", "SELLER_CODE", "CODE", "SELLERCODES",
        "CUSTOMERCODE", "CUSTOMER_CODE", "CUSTOMERCODES",
    }
    mapping = {}
    try:
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                parts = line.strip().split(",")
                if len(parts) < 2:
                    continue
                codes_str, client_name = parts[0].strip(), parts[1].strip()
                if i == 0 and codes_str.upper().replace(" ", "") in _HEADER_TOKENS:
                    continue
                if not codes_str or not client_name:
                    continue
                for code in codes_str.split("/"):
                    code = code.strip().upper()
                    if code:
                        mapping[code] = client_name
    except FileNotFoundError:
        pass
    return mapping

CLIENT_MAP = load_client_map(r"client list.csv")


def _resolve_client(seller_str):
    """Resolve client name from a seller_type value that may contain merged codes like 'OIP/GLA/FMB'."""
    if not isinstance(seller_str, str):
        return "—"
    for code in seller_str.split("/"):
        name = CLIENT_MAP.get(code.strip().upper())
        if name:
            return name
    return "—"


def add_client_col(df, seller_col="Seller"):
    """Insert a 'Client' column right after the seller column using CLIENT_MAP."""
    df = df.copy()
    if seller_col in df.columns:
        idx = df.columns.get_loc(seller_col) + 1
        df.insert(idx, "Client", df[seller_col].apply(_resolve_client))
    return df


def _recompute_pcts(df):
    """Recompute percentage columns from raw count columns after aggregation."""
    nan = float("nan")
    if "PHin" in df.columns:
        phin = df["PHin"].replace(0, nan)
        if "conv_num" in df.columns:
            df["Overall Conversion %"] = (df["conv_num"] / phin * 100).round(2)
        if "zero_attempt_num" in df.columns:
            df["ZRTO %"] = (df["zero_attempt_num"] / phin * 100).round(2)
        if "conv_num" in df.columns:
            df["Conv %"] = (df["conv_num"] / phin * 100).round(2)
        if "cod_vol" in df.columns:
            df["COD Share %"] = (df["cod_vol"] / phin * 100).round(2)
        if "pp_vol" in df.columns:
            df["Prepaid Share %"] = (df["pp_vol"] / phin * 100).round(2)
    if "First_attempt_delivered" in df.columns and "fac_deno" in df.columns:
        df["FAC %"] = (df["First_attempt_delivered"] / df["fac_deno"].replace(0, nan) * 100).round(2)
    if "Breach_Num" in df.columns and "Breach_Den" in df.columns:
        df["Breach %"] = (df["Breach_Num"] / df["Breach_Den"].replace(0, nan) * 100).round(2)
    if "cod_conv" in df.columns and "cod_vol" in df.columns:
        df["COD Conversion %"] = (df["cod_conv"] / df["cod_vol"].replace(0, nan) * 100).round(2)
    if "pp_conv" in df.columns and "pp_vol" in df.columns:
        df["Prepaid Conversion %"] = (df["pp_conv"] / df["pp_vol"].replace(0, nan) * 100).round(2)
    return df.fillna(0)


_RAW_SUM_COLS = [
    "PHin", "conv_num", "First_attempt_delivered", "fac_deno",
    "Breach_Num", "Breach_Den", "zero_attempt_num",
    "cod_vol", "cod_conv", "pp_vol", "pp_conv",
]


def merge_seller_table_by_client(df):
    """Merge rows in seller_table that share the same client name.
    seller codes are joined with '/'."""
    df = df.copy()
    df["_client"] = df["seller_type"].str.upper().map(CLIENT_MAP).fillna(df["seller_type"])
    codes = (
        df.groupby("_client")["seller_type"]
        .apply(lambda x: "/".join(sorted(x.unique())))
        .reset_index()
        .rename(columns={"seller_type": "_codes"})
    )
    sum_cols = [c for c in _RAW_SUM_COLS if c in df.columns]
    agg = df.groupby("_client")[sum_cols].sum().reset_index()
    merged = agg.merge(codes, on="_client")
    merged["seller_type"] = merged["_codes"]
    merged = merged.drop(columns=["_client", "_codes"])
    merged = _recompute_pcts(merged)
    return merged.sort_values("PHin", ascending=False)


def merge_daily_by_client(df):
    """Merge rows in daily_df that share the same client name (per date).
    seller codes are joined with '/'."""
    df = df.copy()
    df["_client"] = df["seller_type"].str.upper().map(CLIENT_MAP).fillna(df["seller_type"])
    codes = (
        df.groupby("_client")["seller_type"]
        .apply(lambda x: "/".join(sorted(x.unique())))
        .reset_index()
        .rename(columns={"seller_type": "_codes"})
    )
    sum_cols = [c for c in _RAW_SUM_COLS if c in df.columns]
    grp_cols = ["_client"]
    if "reporting_date" in df.columns:
        grp_cols = ["reporting_date", "_client"]
    agg = df.groupby(grp_cols)[sum_cols].sum().reset_index()
    agg = agg.merge(codes, on="_client")
    agg["seller_type"] = agg["_codes"]
    agg = agg.drop(columns=["_client", "_codes"])
    agg = _recompute_pcts(agg)
    if "reporting_date" in agg.columns:
        return agg.sort_values("reporting_date")
    return agg.sort_values("PHin", ascending=False)


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING & METRIC HELPERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
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


@st.cache_data(ttl=120)
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


@st.cache_data(ttl=120)
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
    data_path = st.text_input("CSV file path", value="cd5a0d281d2bef0117eaeb0bffae3932.csv")

    ref_col1, ref_col2 = st.columns([1, 1])
    with ref_col1:
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with ref_col2:
        auto_refresh = st.toggle("Auto-refresh", value=False)
    if auto_refresh:
        refresh_sec = st.select_slider(
            "Refresh interval",
            options=[30, 60, 120, 300, 600],
            value=120,
            format_func=lambda s: f"{s // 60}m" if s >= 60 else f"{s}s",
        )
        st.caption(f"Page reloads every {refresh_sec // 60}m {refresh_sec % 60}s")
        st.markdown(
            f'<meta http-equiv="refresh" content="{refresh_sec}">',
            unsafe_allow_html=True,
        )

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

seller_table = merge_seller_table_by_client(build_seller_table(filtered_df))
seller_table = seller_table[seller_table["PHin"] >= min_vol]
daily_df     = merge_daily_by_client(build_daily_table(filtered_df))
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
    seller_table = merge_seller_table_by_client(build_seller_table(date_filtered_df))
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
        "seller_type", "PHin",
        "Breach %", "FAC %", "ZRTO %",
        "Overall Conversion %", "COD Conversion %", "Prepaid Conversion %",
        "COD Share %", "Prepaid Share %",
    ]
    breach_report = seller_table[breach_report_cols].rename(columns={
        "seller_type": "Seller",
        "PHin": "Volume",
    })
    breach_report = add_client_col(breach_report)
    if search:
        breach_report = breach_report[
            breach_report["Seller"].str.upper().str.contains(search.upper())
            | breach_report["Client"].str.upper().str.contains(search.upper())
        ]

    styled_breach = (
        breach_report.style
        .map(_color_breach, subset=["Breach %"])
        .map(_color_zrto, subset=["ZRTO %"])
        .map(_color_conv_fac, subset=["FAC %", "Overall Conversion %", "COD Conversion %", "Prepaid Conversion %"])
        .map(_color_volume, subset=["Volume"])
        .format({
            "Volume": "{:,.0f}",
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
    st.dataframe(styled_breach, use_container_width=True, height=420, hide_index=True)

    # ── Daily Seller-wise Breach Performance ────────────────────────────────
    st.divider()
    st.markdown("### 📅 Daily Seller-wise Breach Performance Report")
    st.caption(
        "Same metrics as above but broken down by date. "
        "Sort by any column to spot daily anomalies."
    )

    search_daily = st.text_input(
        "Search seller", placeholder="🔍 Search seller type…", label_visibility="collapsed", key="search_daily_breach"
    )

    daily_breach_df = date_filtered_df.copy()
    daily_breach_df["_client_grp"] = daily_breach_df["seller_type"].str.upper().map(CLIENT_MAP).fillna(daily_breach_df["seller_type"])

    _code_lookup = (
        daily_breach_df.groupby("_client_grp")["seller_type"]
        .apply(lambda x: "/".join(sorted(x.unique())))
        .to_dict()
    )

    agg_daily = daily_breach_df.groupby(["reporting_date", "_client_grp"]).agg(
        PHin=("PHin", "sum"),
        conv_num=("conv_num", "sum"),
        First_attempt_delivered=("First_attempt_delivered", "sum"),
        fac_deno=("fac_deno", "sum"),
        Breach_Num=("Breach_Num", "sum"),
        Breach_Den=("Breach_Den", "sum"),
        zero_attempt_num=("zero_attempt_num", "sum"),
    ).reset_index()

    cod_daily = (
        daily_breach_df[daily_breach_df["payment_type_norm"] == "COD"]
        .groupby(["reporting_date", "_client_grp"])
        .agg(cod_vol=("PHin", "sum"), cod_conv=("conv_num", "sum"))
        .reset_index()
    )
    pp_daily = (
        daily_breach_df[daily_breach_df["payment_type_norm"] == "Prepaid"]
        .groupby(["reporting_date", "_client_grp"])
        .agg(pp_vol=("PHin", "sum"), pp_conv=("conv_num", "sum"))
        .reset_index()
    )

    d_r = (
        agg_daily
        .merge(cod_daily, on=["reporting_date", "_client_grp"], how="left")
        .merge(pp_daily, on=["reporting_date", "_client_grp"], how="left")
        .fillna(0)
    )
    d_r["seller_type"] = d_r["_client_grp"].map(_code_lookup)
    d_r = d_r.drop(columns=["_client_grp"])

    _nan = float("nan")
    d_r["Overall Conversion %"] = (d_r["conv_num"] / d_r["PHin"].replace(0, _nan) * 100).round(2)
    d_r["COD Conversion %"]     = (d_r["cod_conv"] / d_r["cod_vol"].replace(0, _nan) * 100).round(2)
    d_r["Prepaid Conversion %"] = (d_r["pp_conv"]  / d_r["pp_vol"].replace(0, _nan) * 100).round(2)
    d_r["FAC %"]                = (d_r["First_attempt_delivered"] / d_r["fac_deno"].replace(0, _nan) * 100).round(2)
    d_r["Breach %"]             = (d_r["Breach_Num"] / d_r["Breach_Den"].replace(0, _nan) * 100).round(2)
    d_r["ZRTO %"]               = (d_r["zero_attempt_num"] / d_r["PHin"].replace(0, _nan) * 100).round(2)
    d_r["COD Share %"]          = (d_r["cod_vol"] / d_r["PHin"].replace(0, _nan) * 100).round(2)
    d_r["Prepaid Share %"]      = (d_r["pp_vol"]  / d_r["PHin"].replace(0, _nan) * 100).round(2)
    d_r = d_r.fillna(0)

    d_r = d_r[d_r["PHin"] >= min_vol]
    d_r["Date"] = d_r["reporting_date"].apply(fmt_date)

    daily_breach_display = d_r[[
        "Date", "seller_type", "Breach %", "FAC %",
        "PHin", "ZRTO %",
        "Overall Conversion %", "COD Conversion %", "Prepaid Conversion %",
        "COD Share %", "Prepaid Share %",
    ]].rename(columns={
        "seller_type": "Seller",
        "PHin": "Volume",
    }).sort_values(["Date", "Seller"])
    daily_breach_display = add_client_col(daily_breach_display)

    if search_daily:
        daily_breach_display = daily_breach_display[
            daily_breach_display["Seller"].str.upper().str.contains(search_daily.upper())
            | daily_breach_display["Client"].str.upper().str.contains(search_daily.upper())
        ]

    styled_daily_breach = (
        daily_breach_display.style
        .map(_color_breach, subset=["Breach %"])
        .map(_color_zrto, subset=["ZRTO %"])
        .map(_color_conv_fac, subset=["FAC %", "Overall Conversion %", "COD Conversion %", "Prepaid Conversion %"])
        .map(_color_volume, subset=["Volume"])
        .format({
            "Volume": "{:,.0f}",
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
    st.dataframe(styled_daily_breach, use_container_width=True, height=500, hide_index=True)


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
    row_metrics = ["Breach %", "FAC %", "ZRTO %", "Conv %"]
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
                    declined = (merged["v"] >= merged["v_prev"]).sum()
                else:
                    improved = (merged["v"] > merged["v_prev"]).sum()
                    declined = (merged["v"] <= merged["v_prev"]).sum()
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
    count_df = count_df[period_labels[::-1]]
    count_df.index.name = "Metric"
    count_df = count_df.reset_index()

    _blank_metrics = {"ZRTO %", "Conv %"}
    _cutoff = (datetime.now() - __import__("datetime").timedelta(days=15)).strftime("%Y%m%d")
    for col in count_df.columns:
        if col == "Metric":
            continue
        if compare_mode == "Day wise compare":
            raw_dt = [d for d in dates if fmt_date(d) == col]
            is_recent = bool(raw_dt) and raw_dt[0] >= _cutoff
        elif compare_mode == "Weekly compare":
            week_dates = [d for d in dates if datetime.strptime(d, "%Y%m%d").strftime("%Y-W%W") == col]
            is_recent = bool(week_dates) and max(week_dates) >= _cutoff
        else:
            month_dates = [d for d in dates if datetime.strptime(d, "%Y%m%d").strftime("%Y-%m") == col]
            is_recent = bool(month_dates) and max(month_dates) >= _cutoff
        if is_recent:
            count_df.loc[count_df["Metric"].isin(_blank_metrics), col] = ""

    render_sticky_table(count_df.set_index("Metric"), no_vscroll=True)

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
    # SECTION 2 — Decline report: sellers performing worse vs previous period
    # ─────────────────────────────────────────────────────────────────────────
    def _color_metric_val(v, risk=is_risk):
        if pd.isna(v): return ""
        if risk:
            if v <= (thresh * 0.5): return "background-color:#DCFCE7;color:#166534;font-weight:600;"
            if v <= thresh: return "background-color:#FEF9C3;color:#854D0E;font-weight:600;"
            return "background-color:#FEE2E2;color:#991B1B;font-weight:700;"
        else:
            if v >= thresh * 1.2: return "background-color:#DCFCE7;color:#166534;font-weight:600;"
            if v >= thresh: return "background-color:#FEF9C3;color:#854D0E;font-weight:600;"
            return "background-color:#FEE2E2;color:#991B1B;font-weight:600;"

    direction_word = "lower" if is_risk else "higher"
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#991B1B 0%,#DC2626 50%,#EF4444 100%);'
        f'border-radius:14px;padding:1.1rem 1.5rem;margin-bottom:1rem;'
        f'display:flex;justify-content:space-between;align-items:center;'
        f'box-shadow:0 4px 16px rgba(153,27,27,0.30);border:1px solid rgba(255,255,255,0.10);">'
        f'<div style="display:flex;align-items:center;gap:1rem;">'
        f'<div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:0.5rem 0.6rem;'
        f'display:flex;align-items:center;justify-content:center;">'
        f'<span style="font-size:1.4rem;">📉</span></div>'
        f'<div>'
        f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;'
        f'color:rgba(255,255,255,0.70);font-weight:600;margin-bottom:2px;">Decline Report</div>'
        f'<span style="font-size:1.15rem;font-weight:700;color:#fff;">{metric}</span>'
        f'<span style="font-size:0.82rem;color:rgba(255,255,255,0.80);margin-left:0.5rem;">'
        f'— sellers performing worse vs previous period</span>'
        f'</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:rgba(255,255,255,0.60);margin-bottom:2px;">Threshold</div>'
        f'<span style="font-size:1.05rem;font-weight:700;color:#fff;'
        f'font-family:\'IBM Plex Mono\',monospace;">{thresh}%</span>'
        f'<span style="font-size:0.72rem;color:rgba(255,255,255,0.70);margin-left:0.4rem;">'
        f'{direction_word} is better</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    dt_decline_mode = st.radio(
        "Period",
        ["Day", "Week", "Month"],
        horizontal=True,
        label_visibility="collapsed",
        key="dt_decline_period_mode",
    )

    nan_val = float("nan")

    if dt_decline_mode == "Day":
        st.caption("Pick a date. Shows sellers whose metric got worse compared to the previous day.")
        _dt_period_df = daily_df.copy()
        _dt_period_df["_period"] = _dt_period_df["reporting_date"]
        _dt_periods = dates

        try:
            _dt_min_d = datetime.strptime(min(dates), "%Y%m%d").date()
            _dt_max_d = datetime.strptime(max(dates), "%Y%m%d").date()
        except (ValueError, TypeError):
            _dt_min_d = _dt_max_d = datetime.now().date()

        _dt_default = _dt_min_d + ((_dt_max_d - _dt_min_d) if len(dates) < 2 else __import__("datetime").timedelta(days=1))
        if _dt_default > _dt_max_d:
            _dt_default = _dt_max_d

        dt_selected_date = st.date_input(
            "Select date",
            value=_dt_default,
            min_value=_dt_min_d,
            max_value=_dt_max_d,
            key="dt_decline_day_cal",
        )
        dt_selected_period = dt_selected_date.strftime("%Y%m%d")
        dt_selected_label = fmt_date(dt_selected_period)

        if dt_selected_period in _dt_periods:
            dt_sel_idx = _dt_periods.index(dt_selected_period)
        else:
            candidates = [d for d in _dt_periods if d <= dt_selected_period]
            if candidates:
                dt_selected_period = candidates[-1]
                dt_sel_idx = _dt_periods.index(dt_selected_period)
                dt_selected_label = fmt_date(dt_selected_period)
            else:
                dt_sel_idx = 0
                dt_selected_period = _dt_periods[0]
                dt_selected_label = fmt_date(dt_selected_period)

    else:
        _dt_period_df = daily_df.copy()
        _dt_period_df["_dt"] = _dt_period_df["reporting_date"].apply(
            lambda s: datetime.strptime(str(s), "%Y%m%d") if len(str(s)) == 8 else datetime.now()
        )
        if dt_decline_mode == "Week":
            st.caption("Pick a week. Shows sellers whose metric got worse compared to the previous week.")
            _dt_period_df["_period"] = _dt_period_df["_dt"].apply(lambda d: d.strftime("%Y-W%W"))
        else:
            st.caption("Pick a month. Shows sellers whose metric got worse compared to the previous month.")
            _dt_period_df["_period"] = _dt_period_df["_dt"].apply(lambda d: d.strftime("%Y-%m"))

        _dt_period_df = (
            _dt_period_df.groupby(["_period", "seller_type"])
            .agg(PHin=("PHin", "sum"), conv_num=("conv_num", "sum"),
                 zero_attempt_num=("zero_attempt_num", "sum"),
                 First_attempt_delivered=("First_attempt_delivered", "sum"),
                 fac_deno=("fac_deno", "sum"), Breach_Num=("Breach_Num", "sum"),
                 Breach_Den=("Breach_Den", "sum"))
            .reset_index()
        )
        _dt_period_df["ZRTO %"]   = (_dt_period_df["zero_attempt_num"] / _dt_period_df["PHin"].replace(0, nan_val) * 100).round(2)
        _dt_period_df["FAC %"]    = (_dt_period_df["First_attempt_delivered"] / _dt_period_df["fac_deno"].replace(0, nan_val) * 100).round(2)
        _dt_period_df["Breach %"] = (_dt_period_df["Breach_Num"] / _dt_period_df["Breach_Den"].replace(0, nan_val) * 100).round(2)
        _dt_period_df["Conv %"]   = (_dt_period_df["conv_num"] / _dt_period_df["PHin"].replace(0, nan_val) * 100).round(2)
        _dt_period_df = _dt_period_df.fillna(0)
        _dt_periods = sorted(_dt_period_df["_period"].unique())

        _dt_period_display = list(_dt_periods)
        dt_selected_label = st.selectbox(
            f"Select {dt_decline_mode.lower()}", _dt_period_display,
            index=min(1, len(_dt_period_display) - 1), key="dt_decline_period_sel",
        )
        dt_sel_idx = _dt_period_display.index(dt_selected_label)
        dt_selected_period = _dt_periods[dt_sel_idx]

    if dt_sel_idx == 0:
        st.info(f"First {dt_decline_mode.lower()} — no previous {dt_decline_mode.lower()} to compare against.")
    else:
        dt_prev_period = _dt_periods[dt_sel_idx - 1]
        dt_prev_label = fmt_date(dt_prev_period) if dt_decline_mode == "Day" else dt_prev_period

        dt_curr = _dt_period_df[_dt_period_df["_period"] == dt_selected_period][["seller_type", metric]].copy()
        dt_prev = _dt_period_df[_dt_period_df["_period"] == dt_prev_period][["seller_type", metric]].copy()
        dt_curr = dt_curr.rename(columns={metric: "Current"})
        dt_prev = dt_prev.rename(columns={metric: "Previous"})
        dt_merged = dt_curr.merge(dt_prev, on="seller_type", how="inner")
        dt_merged["Change"] = dt_merged["Current"] - dt_merged["Previous"]

        if is_risk:
            dt_declined = dt_merged[dt_merged["Change"] > 0].copy()
        else:
            dt_declined = dt_merged[dt_merged["Change"] < 0].copy()

        dt_declined = dt_declined.sort_values("Change", ascending=not is_risk)
        dt_declined = dt_declined.rename(columns={"seller_type": "Seller"})
        dt_declined = add_client_col(dt_declined)

        def _color_change_dt(v):
            if pd.isna(v): return ""
            return "background-color:#FEE2E2;color:#991B1B;font-weight:600;"

        if dt_declined.empty:
            st.success(f"No sellers declined on {dt_selected_label} vs {dt_prev_label}.")
        else:
            st.markdown(
                f"<div style='font-size:0.82rem;color:#64748B;margin-bottom:8px;'>"
                f"<b>{len(dt_declined)}</b> sellers performed worse on "
                f"<b>{dt_selected_label}</b> vs <b>{dt_prev_label}</b></div>",
                unsafe_allow_html=True,
            )
            fmt_str = f"{{:.{dec}f}}%"
            styled_dt_declined = (
                dt_declined.style
                .map(_color_change_dt, subset=["Change"])
                .map(_color_metric_val, subset=["Current", "Previous"])
                .format({"Current": fmt_str, "Previous": fmt_str, "Change": fmt_str})
            )
            st.dataframe(styled_dt_declined, use_container_width=True, height=400, hide_index=True)

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 3 — Seller × Period pivot table
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1E3A5F 0%,#1D4ED8 100%);'
        f'border-radius:14px;padding:1.1rem 1.5rem;margin-bottom:1rem;'
        f'display:flex;justify-content:space-between;align-items:center;'
        f'box-shadow:0 4px 16px rgba(29,78,216,0.25);border:1px solid rgba(255,255,255,0.10);">'
        f'<div style="display:flex;align-items:center;gap:1rem;">'
        f'<div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:0.5rem 0.6rem;'
        f'display:flex;align-items:center;justify-content:center;">'
        f'<span style="font-size:1.4rem;">📊</span></div>'
        f'<div>'
        f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;'
        f'color:rgba(255,255,255,0.70);font-weight:600;margin-bottom:2px;">Seller × Period</div>'
        f'<span style="font-size:1.15rem;font-weight:700;color:#fff;">{metric}</span>'
        f'<span style="font-size:0.82rem;color:rgba(255,255,255,0.80);margin-left:0.5rem;">'
        f'— rows = sellers · columns = selected periods</span>'
        f'</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:rgba(255,255,255,0.60);margin-bottom:2px;">Threshold</div>'
        f'<span style="font-size:1.05rem;font-weight:700;color:#fff;'
        f'font-family:\'IBM Plex Mono\',monospace;">{thresh}%</span>'
        f'<span style="font-size:0.72rem;color:rgba(255,255,255,0.70);margin-left:0.4rem;">'
        f'{"lower" if is_risk else "higher"} is better</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    pv_mode = st.radio(
        "Period granularity",
        ["Day", "Week", "Month"],
        horizontal=True,
        label_visibility="collapsed",
        key="pivot_period_mode",
    )

    _pv_nan = float("nan")
    _pv_df = daily_df.copy()

    if pv_mode == "Day":
        _pv_df["_period"] = _pv_df["reporting_date"]
    else:
        _pv_df["_pv_dt"] = _pv_df["reporting_date"].apply(
            lambda s: datetime.strptime(str(s), "%Y%m%d") if len(str(s)) == 8 else datetime.now()
        )
        if pv_mode == "Week":
            _pv_df["_period"] = _pv_df["_pv_dt"].apply(lambda d: d.strftime("%Y-W%W"))
        else:
            _pv_df["_period"] = _pv_df["_pv_dt"].apply(lambda d: d.strftime("%Y-%m"))

    if pv_mode != "Day":
        _pv_df = (
            _pv_df.groupby(["_period", "seller_type"])
            .agg(PHin=("PHin", "sum"), conv_num=("conv_num", "sum"),
                 zero_attempt_num=("zero_attempt_num", "sum"),
                 First_attempt_delivered=("First_attempt_delivered", "sum"),
                 fac_deno=("fac_deno", "sum"), Breach_Num=("Breach_Num", "sum"),
                 Breach_Den=("Breach_Den", "sum"))
            .reset_index()
        )
        _pv_df["ZRTO %"]   = (_pv_df["zero_attempt_num"] / _pv_df["PHin"].replace(0, _pv_nan) * 100).round(2)
        _pv_df["FAC %"]     = (_pv_df["First_attempt_delivered"] / _pv_df["fac_deno"].replace(0, _pv_nan) * 100).round(2)
        _pv_df["Breach %"]  = (_pv_df["Breach_Num"] / _pv_df["Breach_Den"].replace(0, _pv_nan) * 100).round(2)
        _pv_df["Conv %"]    = (_pv_df["conv_num"] / _pv_df["PHin"].replace(0, _pv_nan) * 100).round(2)
        _pv_df = _pv_df.fillna(0)

    _pv_periods = sorted(_pv_df["_period"].unique(), reverse=True)

    # Seller filter + period range
    pv_fc1, pv_fc2 = st.columns([2, 2])
    with pv_fc1:
        pv_seller_input = st.text_input(
            "Filter sellers (comma-separated)",
            placeholder="e.g. SDL, FCY, ROP",
            key="pv_seller_filter",
        )
    with pv_fc2:
        if pv_mode == "Day":
            try:
                _pv_min_d = datetime.strptime(min(dates), "%Y%m%d").date()
                _pv_max_d = datetime.strptime(max(dates), "%Y%m%d").date()
            except (ValueError, TypeError):
                _pv_min_d = _pv_max_d = datetime.now().date()
            pv_d_col1, pv_d_col2 = st.columns(2)
            with pv_d_col1:
                pv_start = st.date_input("From", value=_pv_min_d, min_value=_pv_min_d, max_value=_pv_max_d, key="pv_from")
            with pv_d_col2:
                pv_end = st.date_input("To", value=_pv_max_d, min_value=_pv_min_d, max_value=_pv_max_d, key="pv_to")
            if pv_start > pv_end:
                pv_start, pv_end = pv_end, pv_start
            pv_start_str = pv_start.strftime("%Y%m%d")
            pv_end_str = pv_end.strftime("%Y%m%d")
            _pv_df = _pv_df[(_pv_df["_period"] >= pv_start_str) & (_pv_df["_period"] <= pv_end_str)]
        else:
            pv_period_opts = sorted(_pv_df["_period"].unique())
            pv_p_col1, pv_p_col2 = st.columns(2)
            with pv_p_col1:
                pv_p_start = st.selectbox("From", pv_period_opts, index=0, key="pv_period_from")
            with pv_p_col2:
                pv_p_end = st.selectbox("To", pv_period_opts, index=len(pv_period_opts) - 1, key="pv_period_to")
            if pv_p_start > pv_p_end:
                pv_p_start, pv_p_end = pv_p_end, pv_p_start
            _pv_df = _pv_df[(_pv_df["_period"] >= pv_p_start) & (_pv_df["_period"] <= pv_p_end)]

    if pv_seller_input and pv_seller_input.strip():
        pv_sel_list = [s.strip().upper() for s in pv_seller_input.split(",") if s.strip()]
        _pv_df = _pv_df[_pv_df["seller_type"].apply(
            lambda st: any(
                tok in st.upper().split("/")
                or tok in _resolve_client(st).upper()
                for tok in pv_sel_list
            )
        )]

    if _pv_df.empty:
        st.warning("No data for the selected sellers / period range.")
    else:
        pv_pivot = _pv_df.pivot_table(
            index="seller_type", columns="_period", values=metric, aggfunc="first"
        ).fillna(0)
        pv_pivot = pv_pivot[sorted(pv_pivot.columns, reverse=True)]
        if pv_mode == "Day":
            pv_pivot.columns = [fmt_date(c) for c in pv_pivot.columns]

        pv_pivot["Avg"] = pv_pivot.mean(axis=1).round(dec)
        avg_col = pv_pivot.pop("Avg")
        pv_pivot.insert(0, "Avg", avg_col)

        pv_pivot = pv_pivot.sort_values("Avg", ascending=not is_risk)
        pv_pivot.index.name = "Seller"
        pv_pivot = pv_pivot.reset_index()
        pv_pivot = add_client_col(pv_pivot)

        st.markdown(
            f"<div style='font-size:0.78rem;color:#64748B;margin-bottom:6px;'>"
            f"Showing <b>{len(pv_pivot)}</b> sellers · <b>{len(pv_pivot.columns) - 3}</b> "
            f"{pv_mode.lower()}s</div>",
            unsafe_allow_html=True,
        )

        _skip_cols = {"Seller", "Client"}
        pv_fmt = f"{{:.{dec}f}}%"
        pv_fmt_dict = {c: pv_fmt for c in pv_pivot.columns if c not in _skip_cols}
        styled_pv = (
            pv_pivot.style
            .map(_color_metric_val, subset=[c for c in pv_pivot.columns if c not in _skip_cols])
            .format(pv_fmt_dict)
        )
        st.dataframe(styled_pv, use_container_width=True, height=500, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center;color:#98A2B3;font-size:0.72rem;'>"
    "Seller Performance Dashboard · Data refreshed on load</div>",
    unsafe_allow_html=True,
)
