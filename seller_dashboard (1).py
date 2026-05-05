"""
Seller Performance Dashboard — Streamlit App (2 pages)
=======================================================
Page 1 : Overall Metric — Seller-wise breach performance (table-first, coloured)
Page 2 : Daily Trends — Daily breach tables, rankings, trend selector

Run with:
    streamlit run "seller_dashboard (1).py"

Requirements:
    pip install streamlit pandas numpy
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
import hmac
import hashlib
import json
import re
import time
import base64
from pathlib import Path
from datetime import datetime, timedelta
import streamlit.components.v1 as _components


import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Seller Performance",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)


ROOT_DIR = Path(__file__).resolve().parent
CLIENT_LIST_CSV = ROOT_DIR / "client list.csv"
ADMIN_EMAILS_JSON = ROOT_DIR / "admin_emails.json"
_METRICS_CSV_NAME = "cd5a0d281d2bef0117eaeb0bffae3932.csv"


def _resolve_default_metrics_csv() -> Path:
    """Prefer data/ (common in repo layout); fall back to same directory as this script."""
    data_p = ROOT_DIR / _METRICS_CSV_NAME
    root_p = ROOT_DIR / _METRICS_CSV_NAME
    if data_p.is_file():
        return data_p
    return root_p


DEFAULT_METRICS_CSV = _resolve_default_metrics_csv()
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _safe_secret_compare(a: str, b: str) -> bool:
    try:
        return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
    except ValueError:
        return False




def _norm_email(s: str) -> str:
    return (s or "").strip().lower()


def _dashboard_auth_cfg() -> dict:
    try:
        x = st.secrets.get("dashboard_auth")
        if x is None:
            return {}
        return dict(x)
    except Exception:
        return {}


def _load_admin_emails_from_disk() -> list[str]:
    if not ADMIN_EMAILS_JSON.is_file():
        return []
    try:
        data = json.loads(ADMIN_EMAILS_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return sorted({_norm_email(e) for e in data if isinstance(e, str) and _norm_email(e)})


def _save_admin_emails_to_disk(emails: list[str]) -> None:
    norm = sorted({_norm_email(e) for e in emails if _norm_email(e)})
    ADMIN_EMAILS_JSON.write_text(json.dumps(norm, indent=2), encoding="utf-8")


def _ensure_admin_file_seeded() -> None:
    cfg = _dashboard_auth_cfg()
    boot = cfg.get("bootstrap_admin_emails") or []
    if not isinstance(boot, list):
        boot = []
    boot_norm = [_norm_email(e) for e in boot if _norm_email(e)]
    if not ADMIN_EMAILS_JSON.is_file() and boot_norm:
        _save_admin_emails_to_disk(boot_norm)


def _viewer_accounts() -> list[dict]:
    cfg = _dashboard_auth_cfg()
    v = cfg.get("viewers")
    if not v:
        return []
    if isinstance(v, list):
        return [dict(x) for x in v if isinstance(x, dict)]
    return []


def _attempt_login(email: str, password: str) -> tuple[bool, str, str, str | None]:
    """Return (ok, role, error_message, viewer_zone_or_none)."""
    em = _norm_email(email)
    pwd = password or ""
    cfg = _dashboard_auth_cfg()
    admin_pwd = str(cfg.get("admin_password", "") or "")
    _ensure_admin_file_seeded()
    admins = _load_admin_emails_from_disk()
    if em and em in admins and admin_pwd and _safe_secret_compare(pwd, admin_pwd):
        return True, "admin", "", None
    for row in _viewer_accounts():
        ve = _norm_email(str(row.get("email", "")))
        vp = str(row.get("password", "") or "")
        zone = str(row.get("zone", "") or "").strip()
        if ve == em and vp and _safe_secret_compare(pwd, vp):
            if not zone:
                return False, "", "Viewer account missing zone in secrets.", None
            return True, "viewer", "", zone
    if not cfg and not _viewer_accounts():
        return False, "", "Missing dashboard_auth in .streamlit/secrets.toml.", None
    return False, "", "Invalid email or password.", None


# ─────────────────────────────────────────────────────────────────────────────
# COOKIE-BASED SESSION PERSISTENCE
# ─────────────────────────────────────────────────────────────────────────────
_COOKIE_NAME = "seller_dash_session"
_COOKIE_MAX_AGE = 86400 * 7  # 7 days


def _get_cookie_secret() -> str:
    cfg = _dashboard_auth_cfg()
    admin_pwd = str(cfg.get("admin_password", "") or "fallback-key")
    return hashlib.sha256(f"seller-dash-{admin_pwd}".encode()).hexdigest()


def _sign_session(email: str, role: str, zone: str | None) -> str:
    secret = _get_cookie_secret()
    expiry = int(time.time()) + _COOKIE_MAX_AGE
    payload = json.dumps({"email": email, "role": role, "zone": zone, "exp": expiry})
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def _verify_session(token: str) -> dict | None:
    try:
        secret = _get_cookie_secret()
        parts = token.split(".", 1)
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def _read_session_cookie() -> dict | None:
    try:
        token = st.context.cookies.get(_COOKIE_NAME)
        if not token:
            return None
        return _verify_session(token)
    except Exception:
        return None


def _set_session_cookie(email: str, role: str, zone: str | None) -> None:
    token = _sign_session(email, role, zone)
    _components.html(
        f"<script>document.cookie='{_COOKIE_NAME}={token};path=/;max-age={_COOKIE_MAX_AGE};SameSite=Lax';</script>",
        height=0,
    )


def _clear_session_cookie() -> None:
    _components.html(
        f"<script>document.cookie='{_COOKIE_NAME}=;path=/;max-age=0;SameSite=Lax';</script>",
        height=0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SESSION INITIALIZATION (restore from cookie on fresh page load)
# ─────────────────────────────────────────────────────────────────────────────
if "_session_initialized" not in st.session_state:
    st.session_state._session_initialized = True
    session = _read_session_cookie()
    if session:
        st.session_state.authenticated = True
        st.session_state.auth_email = session.get("email", "")
        st.session_state.auth_role = session.get("role", "")
        st.session_state.auth_zone = session.get("zone")
    else:
        st.session_state.authenticated = False
        st.session_state.auth_email = ""
        st.session_state.auth_role = ""
        st.session_state.auth_zone = None
else:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "auth_email" not in st.session_state:
        st.session_state.auth_email = ""
    if "auth_role" not in st.session_state:
        st.session_state.auth_role = ""
    if "auth_zone" not in st.session_state:
        st.session_state.auth_zone = None

if not st.session_state.authenticated:
    if st.session_state.pop("_needs_cookie_clear", False):
        _clear_session_cookie()
    st.title("Seller Dashboard — Sign in")
    cfg = _dashboard_auth_cfg()
    if not cfg.get("admin_password") and not _viewer_accounts():
        st.error(
            "Configure **[dashboard_auth]** in `.streamlit/secrets.toml` "
            "(copy from `.streamlit/secrets.toml.example`)."
        )
    with st.form("login_form"):
        le = st.text_input("Email")
        lp = st.text_input("Password", type="password")
        sub = st.form_submit_button("Sign in")
    if sub:
        ok, role, msg, zone = _attempt_login(le, lp)
        if ok:
            st.session_state.authenticated = True
            st.session_state.auth_email = _norm_email(le)
            st.session_state.auth_role = role
            st.session_state.auth_zone = zone
            st.session_state._needs_cookie_set = True
            st.rerun()
        elif msg:
            st.error(msg)
    st.stop()

IS_ADMIN = st.session_state.auth_role == "admin"

# Deferred cookie write: runs on the dashboard page where no st.rerun() will kill the iframe
if st.session_state.pop("_needs_cookie_set", False):
    _set_session_cookie(
        st.session_state.auth_email,
        st.session_state.auth_role,
        st.session_state.auth_zone,
    )

if st.session_state.pop("_needs_cookie_clear", False):
    _clear_session_cookie()


st.markdown("""
<style>
/* fonts loaded via preconnect link below */

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

st.markdown(
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=IBM+Plex+Sans:wght@300;400;500;600;700&'
    'family=IBM+Plex+Mono:wght@400;500&display=swap">',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
METRIC_CONFIG = {
    "FAC %":       {"thresh": 70.0, "risk": False, "decimals": 1, "color": "#6D28D9", "sub": "Faulty Article Count %"},
    "Breach %":    {"thresh": 10.0, "risk": True,  "decimals": 1, "color": "#EA580C", "sub": "SLA Breach %"},
    "FM Picked %": {"thresh": 80.0, "risk": False, "decimals": 1, "color": "#0891B2", "sub": "FM Picked %"},
    "ZRTO %":      {"thresh": 1.5,  "risk": True,  "decimals": 2, "color": "#B91C1C", "sub": "Zero-Rate-To-Order %"},
    "Conv %":      {"thresh": 65.0, "risk": False, "decimals": 1, "color": "#1D4ED8", "sub": "Conversion %"},
}
PALETTE = ["#1D4ED8", "#EA580C", "#15803D", "#6D28D9", "#0891B2"]
NAN = float("nan")


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
    st.markdown(
        f'<div class="{wrap_class}" style="{style}max-width:100%;">{table_html}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────

# CLIENT MAPPING (seller code → client name, code → region/zone)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_client_and_region(path: str) -> tuple[dict, dict]:
    """Load seller-code → client name and code → Region from client list CSV."""
    client_map: dict[str, str] = {}
    code_to_region: dict[str, str] = {}
    p = Path(path)
    if not p.is_file():
        return client_map, code_to_region
    try:
        df = pd.read_csv(p)
    except Exception:
        return client_map, code_to_region
    if df.empty:
        return client_map, code_to_region
    cols_lower = {str(c).strip().lower(): c for c in df.columns}

    def _pick(*substrings: str) -> str | None:
        for key, orig in cols_lower.items():
            if all(s in key for s in substrings):
                return orig
        return None

    code_key = _pick("customer", "code") or _pick("seller", "code")
    name_key = _pick("customer", "name")
    region_key = _pick("region")
    if not code_key or not name_key or not region_key:
        cols = list(df.columns)
        if len(cols) >= 5:
            code_key, name_key, region_key = cols[0], cols[1], cols[4]
        else:
            return client_map, code_to_region

    for _, row in df.iterrows():
        codes_cell = row[code_key]
        if pd.isna(codes_cell):
            continue
        codes_str = str(codes_cell).strip()
        name_cell, region_cell = row[name_key], row[region_key]
        client_name = "" if pd.isna(name_cell) else str(name_cell).strip()
        region = "" if pd.isna(region_cell) else str(region_cell).strip()
        if not codes_str or not region:
            continue
        for code in codes_str.split("/"):
            code = code.strip().upper()
            if not code:
                continue
            if client_name:
                client_map[code] = client_name
            code_to_region[code] = region
    return client_map, code_to_region


CLIENT_MAP, CODE_TO_REGION = load_client_and_region(str(CLIENT_LIST_CSV))


def seller_types_in_zone(seller_types: list, zone: str, code_to_region: dict) -> list[str]:
    """Seller types where at least one slash-separated code maps to zone (exact Region string)."""
    z = (zone or "").strip()
    if not z:
        return []
    out: list[str] = []
    for stype in seller_types:
        if not isinstance(stype, str):
            continue
        for part in stype.split("/"):
            c = part.strip().upper()
            if code_to_region.get(c) == z:
                out.append(stype)
                break
    return sorted(set(out))

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

CLIENT_MAP = load_client_map("client list.csv")



def _resolve_client(seller_str):
    """Resolve client name from a seller_type value that may contain merged codes like 'OIP/GLA/FMB'."""
    if not isinstance(seller_str, str):
        return "—"
    for code in seller_str.split("/"):
        name = CLIENT_MAP.get(code.strip().upper())
        if name:
            return name
    return "—"


_CLIENT_CACHE: dict = {}


def _resolve_client_cached(seller_str):
    """Cached wrapper — avoids repeated split/lookup for the same seller string."""
    r = _CLIENT_CACHE.get(seller_str)
    if r is None:
        r = _resolve_client(seller_str)
        _CLIENT_CACHE[seller_str] = r
    return r


def add_client_col(df, seller_col="Seller"):
    """Insert a 'Client' column right after the seller column using vectorized .map()."""
    df = df.copy()
    if seller_col in df.columns:
        idx = df.columns.get_loc(seller_col) + 1
        df.insert(idx, "Client", df[seller_col].map(_resolve_client_cached))
    return df


def _recompute_pcts(df):
    """Recompute percentage columns from raw count columns after aggregation."""
    if "PHin" in df.columns:
        phin = df["PHin"].replace(0, NAN)
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
        df["FAC %"] = (df["First_attempt_delivered"] / df["fac_deno"].replace(0, NAN) * 100).round(2)
    if "Breach_Num" in df.columns and "Breach_Den" in df.columns:
        df["Breach %"] = (df["Breach_Num"] / df["Breach_Den"].replace(0, NAN) * 100).round(2)
    if "cod_conv" in df.columns and "cod_vol" in df.columns:
        df["COD Conversion %"] = (df["cod_conv"] / df["cod_vol"].replace(0, NAN) * 100).round(2)
    if "pp_conv" in df.columns and "pp_vol" in df.columns:
        df["Prepaid Conversion %"] = (df["pp_conv"] / df["pp_vol"].replace(0, NAN) * 100).round(2)
    if "fm_picked" in df.columns and "fm_created" in df.columns:
        df["FM Picked %"] = (df["fm_picked"] / df["fm_created"].replace(0, NAN) * 100).round(2)
    return df.fillna(0)


_RAW_SUM_COLS = [
    "PHin", "conv_num", "First_attempt_delivered", "fac_deno",
    "Breach_Num", "Breach_Den", "zero_attempt_num",
    "cod_vol", "cod_conv", "pp_vol", "pp_conv",
    "fm_picked", "fm_created",
]


@st.cache_data(ttl=120)
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


@st.cache_data(ttl=120)
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
def _metrics_csv_mtime(path: str) -> float:
    """Bust Streamlit cache when file content changes but path stays the same (e.g. Cloud redeploy)."""
    try:
        return Path(path).resolve().stat().st_mtime
    except OSError:
        return 0.0


@st.cache_data(ttl=300)
def load_raw(path: str, _file_mtime: float) -> pd.DataFrame:
    _ = _file_mtime  # cache key only — changes when CSV on disk is replaced/updated
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
    _sum_cols = ["PHin", "conv_num", "First_attempt_delivered", "fac_deno",
                 "Breach_Num", "Breach_Den", "zero_attempt_num",
                 "fm_picked", "fm_created"]
    _available = [c for c in _sum_cols if c in df.columns]
    _totals = df[_available].sum()
    tv  = _totals.get("PHin", 0)
    td  = _totals.get("conv_num", 0)
    fn  = _totals.get("First_attempt_delivered", 0)
    fd  = _totals.get("fac_deno", 0)
    bn  = _totals.get("Breach_Num", 0)
    bd  = _totals.get("Breach_Den", 0)
    zn  = _totals.get("zero_attempt_num", 0)
    fmp = _totals.get("fm_picked", 0)
    fmc = _totals.get("fm_created", 0)
    _is_cod = df["payment_type_norm"] == "COD"
    _is_pp  = df["payment_type_norm"] == "Prepaid"
    cv  = df.loc[_is_cod, "PHin"].sum()
    pv  = df.loc[_is_pp,  "PHin"].sum()
    cd  = df.loc[_is_cod, "conv_num"].sum()
    pd_ = df.loc[_is_pp,  "conv_num"].sum()
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
        "FM Picked %":          safe_div(fmp, fmc),
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
        fm_picked=("fm_picked", "sum"),
        fm_created=("fm_created", "sum"),
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

    r["Overall Conversion %"] = (r["conv_num"]               / r["PHin"].replace(0, NAN) * 100).round(2)
    r["COD Conversion %"]     = (r["cod_conv"]               / r["cod_vol"].replace(0, NAN) * 100).round(2)
    r["Prepaid Conversion %"] = (r["pp_conv"]                / r["pp_vol"].replace(0, NAN) * 100).round(2)
    r["FAC %"]                = (r["First_attempt_delivered"] / r["fac_deno"].replace(0, NAN) * 100).round(2)
    r["Breach %"]             = (r["Breach_Num"]             / r["Breach_Den"].replace(0, NAN) * 100).round(2)
    r["ZRTO %"]               = (r["zero_attempt_num"]        / r["PHin"].replace(0, NAN) * 100).round(2)
    r["COD Share %"]          = (r["cod_vol"]                / r["PHin"].replace(0, NAN) * 100).round(2)
    r["Prepaid Share %"]      = (r["pp_vol"]                 / r["PHin"].replace(0, NAN) * 100).round(2)
    r["FM Picked %"]          = (r["fm_picked"]              / r["fm_created"].replace(0, NAN) * 100).round(2)

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
        fm_picked=("fm_picked", "sum"),
        fm_created=("fm_created", "sum"),
    ).reset_index()

    daily["ZRTO %"]      = (daily["zero_attempt_num"]        / daily["PHin"].replace(0, NAN) * 100).round(2)
    daily["FAC %"]       = (daily["First_attempt_delivered"] / daily["fac_deno"].replace(0, NAN) * 100).round(2)
    daily["Breach %"]    = (daily["Breach_Num"]              / daily["Breach_Den"].replace(0, NAN) * 100).round(2)
    daily["Conv %"]      = (daily["conv_num"]                / daily["PHin"].replace(0, NAN) * 100).round(2)
    daily["FM Picked %"] = (daily["fm_picked"]               / daily["fm_created"].replace(0, NAN) * 100).round(2)

    return daily.fillna(0).sort_values("reporting_date")


_AGG_SPEC = dict(
    PHin=("PHin", "sum"), conv_num=("conv_num", "sum"),
    zero_attempt_num=("zero_attempt_num", "sum"),
    First_attempt_delivered=("First_attempt_delivered", "sum"),
    fac_deno=("fac_deno", "sum"), Breach_Num=("Breach_Num", "sum"),
    Breach_Den=("Breach_Den", "sum"),
    fm_picked=("fm_picked", "sum"), fm_created=("fm_created", "sum"),
)


@st.cache_data(ttl=120)
def _aggregate_by_period(daily_df: pd.DataFrame, period_type: str) -> pd.DataFrame:
    """Aggregate daily data into Week or Month periods. Returns df with _period column."""
    dt = pd.to_datetime(daily_df["reporting_date"], format="%Y%m%d", errors="coerce")
    fmt = "%Y-W%W" if period_type == "Week" else "%Y-%m"
    src = daily_df.assign(_period=dt.dt.strftime(fmt))
    agg = src.groupby(["_period", "seller_type"]).agg(**_AGG_SPEC).reset_index()
    phin = agg["PHin"].replace(0, NAN)
    agg["ZRTO %"]      = (agg["zero_attempt_num"]        / phin * 100).round(2)
    agg["FAC %"]        = (agg["First_attempt_delivered"] / agg["fac_deno"].replace(0, NAN) * 100).round(2)
    agg["Breach %"]     = (agg["Breach_Num"]              / agg["Breach_Den"].replace(0, NAN) * 100).round(2)
    agg["Conv %"]       = (agg["conv_num"]                / phin * 100).round(2)
    agg["FM Picked %"]  = (agg["fm_picked"]               / agg["fm_created"].replace(0, NAN) * 100).round(2)
    return agg.fillna(0)


def fmt_date(s: str) -> str:
    return f"{s[6:8]}-{s[4:6]}-{s[:4]}" if len(s) == 8 else s


# ── Vectorized table colour helpers (np.select operates on entire columns) ──
def _color_volume_vec(s: pd.Series) -> list:
    return np.where(
        s.isna() | (s == 0),
        "background-color:#F8FAFC;color:#64748B;",
        "background-color:#E0F2FE;color:#0369A1;font-weight:500;",
    ).tolist()


def _make_color_metric_vec(thresh, is_risk):
    """Factory for vectorized metric color functions (used in Daily Trends)."""
    if is_risk:
        def _apply(s: pd.Series) -> list:
            return np.select(
                [s.isna(), s <= thresh * 0.5, s <= thresh],
                ["",
                 "background-color:#DCFCE7;color:#166534;font-weight:600;",
                 "background-color:#FEF9C3;color:#854D0E;font-weight:600;"],
                default="background-color:#FEE2E2;color:#991B1B;font-weight:700;",
            ).tolist()
    else:
        def _apply(s: pd.Series) -> list:
            return np.select(
                [s.isna(), s >= thresh * 1.2, s >= thresh],
                ["",
                 "background-color:#DCFCE7;color:#166534;font-weight:600;",
                 "background-color:#FEF9C3;color:#854D0E;font-weight:600;"],
                default="background-color:#FEE2E2;color:#991B1B;font-weight:600;",
            ).tolist()
    return _apply


def _color_change_vec(s: pd.Series) -> list:
    return np.where(
        s.isna(), "", "background-color:#FEE2E2;color:#991B1B;font-weight:600;"
    ).tolist()


def _color_gap_vec(s: pd.Series) -> list:
    return np.where(
        s.isna(), "", "background-color:#FEE2E2;color:#991B1B;font-weight:600;"
    ).tolist()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📦 Seller Dashboard")

    role_label = "Admin" if IS_ADMIN else f"Viewer ({st.session_state.auth_zone or '—'})"
    st.caption(f"**{st.session_state.auth_email}** · {role_label}")
    if st.button("Log out", use_container_width=True, key="logout_btn"):
        st.session_state.authenticated = False
        st.session_state.auth_email = ""
        st.session_state.auth_role = ""
        st.session_state.auth_zone = None
        st.session_state._needs_cookie_clear = True
        st.rerun()
    st.divider()
    if IS_ADMIN:
        data_path = st.text_input("CSV file path", value=str(DEFAULT_METRICS_CSV))
    else:
        data_path = str(DEFAULT_METRICS_CSV)

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

    if IS_ADMIN:
        st.divider()
        with st.expander("Admin users", expanded=False):
            cur_admins = _load_admin_emails_from_disk()
            if cur_admins:
                st.markdown("**Admin emails**")
                for _e in cur_admins:
                    st.text(_e)
            else:
                st.caption("No admin emails on file. Add one below or set bootstrap_admin_emails in secrets.")
            new_ad = st.text_input("Add admin email", key="new_admin_email_input")
            if st.button("Add email", key="add_admin_email_btn"):
                ne = _norm_email(new_ad)
                if not ne or not _EMAIL_RE.match(ne):
                    st.error("Enter a valid email address.")
                elif ne in cur_admins:
                    st.warning("That email is already an admin.")
                else:
                    _save_admin_emails_to_disk(cur_admins + [ne])
                    st.success(f"Added {ne}")
                    st.rerun()
            rm_opts = ["—"] + cur_admins
            rm_pick = st.selectbox("Remove admin", options=rm_opts, key="remove_admin_select")
            if st.button("Remove selected", key="remove_admin_btn") and rm_pick != "—":
                _save_admin_emails_to_disk([e for e in cur_admins if e != rm_pick])
                st.success(f"Removed {rm_pick}")
                st.rerun()


    st.divider()
    st.markdown("### Global Filters")

try:
    raw_df = load_raw(data_path, _metrics_csv_mtime(data_path))
except FileNotFoundError:

    _hint = " Update the path in the sidebar." if IS_ADMIN else ""
    st.error(f"File not found: `{data_path}`.{_hint}")
    st.stop()

if st.session_state.auth_role == "viewer":
    vz = st.session_state.auth_zone or ""
    all_types = list(raw_df["seller_type"].unique())
    allowed_types = seller_types_in_zone(all_types, vz, CODE_TO_REGION)
    raw_df = raw_df[raw_df["seller_type"].isin(allowed_types)]
    if raw_df.empty:
        st.warning(
            f"No rows match your zone **{vz}** for the codes in this metrics file. "
            "Check that seller codes exist in the client list with that Region."
        )
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

# ─────────────────────────────────────────────────────────────────────────────
# Initialise threshold session-state with METRIC_CONFIG defaults so the values
# are available on every page even before the user visits Threshold Performance.
# ─────────────────────────────────────────────────────────────────────────────
for _mk, _mv in METRIC_CONFIG.items():
    _sk = f"tp_thresh_{_mk}"
    if _sk not in st.session_state:
        st.session_state[_sk] = _mv["thresh"]


def _get_thresh(metric: str) -> float:
    """Return the current user-chosen threshold for *metric* from session state."""
    return st.session_state.get(f"tp_thresh_{metric}", METRIC_CONFIG[metric]["thresh"])


# ─────────────────────────────────────────────────────────────────────────────
# QUICK LINKS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="display:flex;gap:24px;margin-bottom:12px;">'
    '<a href="https://rto-zrto-dashboard123.streamlit.app/" target="_blank" style="color:#1D4ED8;font-weight:500;text-decoration:none;">🔗 RTO Dashboard</a>'
    '<a href="https://citydashtemp-2tp3qsdn4utx3q6vrb3nzc.streamlit.app/" target="_blank" style="color:#1D4ED8;font-weight:500;text-decoration:none;">🔗 state wise</a>'
    '</div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE NAVIGATION (data built lazily per page to avoid redundant computation)
# ─────────────────────────────────────────────────────────────────────────────
page = st.radio(
    "Page",
    ["📊 Overall Metric", "📈 Daily Trends", "🎯 Threshold Performance"],
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
    kpi_cols = st.columns(6)
    kpis = [
        ("Total Volume", f"{int(overall.get('Volume', 0)):,}", "PHin", ""),
        ("Breach %",     f"{overall.get('Breach %', 0):.1f}%", "SLA breach rate", "red"),
        ("ZRTO %",       f"{overall.get('ZRTO %', 0):.2f}%",  "Zero-attempt", "red"),
        ("FAC %",        f"{overall.get('FAC %', 0):.1f}%",   "1st attempt", "orange"),
        ("Conv %",       f"{overall.get('Overall Conversion %', 0):.1f}%", "Conversion", "green"),
        ("FM Picked %",  f"{overall.get('FM Picked %', 0):.1f}%", "Picked / Created", "purple"),
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
        "Breach %", "FAC %", "ZRTO %", "FM Picked %",
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
        .apply(_make_color_metric_vec(_get_thresh("Breach %"), True), subset=["Breach %"])
        .apply(_make_color_metric_vec(_get_thresh("ZRTO %"), True), subset=["ZRTO %"])
        .apply(_make_color_metric_vec(_get_thresh("FAC %"), False), subset=["FAC %"])
        .apply(_make_color_metric_vec(_get_thresh("FM Picked %"), False), subset=["FM Picked %"])
        .apply(_make_color_metric_vec(_get_thresh("Conv %"), False), subset=["Overall Conversion %", "COD Conversion %", "Prepaid Conversion %"])
        .apply(_color_volume_vec, subset=["Volume"])
        .format({
            "Volume": "{:,.0f}",
            "Breach %": "{:.1f}%",
            "FAC %": "{:.1f}%",
            "ZRTO %": "{:.2f}%",
            "FM Picked %": "{:.1f}%",
            "Overall Conversion %": "{:.1f}%",
            "COD Conversion %": "{:.1f}%",
            "Prepaid Conversion %": "{:.1f}%",
            "COD Share %": "{:.1f}%",
            "Prepaid Share %": "{:.1f}%",
        })
    )
    st.dataframe(styled_breach, use_container_width=True, height=420, hide_index=True)

    # ── Day-wise, Seller-wise Performance ────────────────────────────────────
    st.divider()
    st.markdown("### 📅 Day-wise, Seller-wise Performance")
    st.caption(
        "Select a date range and one or more sellers below to load the report. "
        "Sort by any column to spot daily anomalies."
    )

    # Build seller/client options from the date-filtered data
    _dw_all_sellers = sorted(date_filtered_df["seller_type"].unique())
    _dw_seller_client = {s: _resolve_client(s) for s in _dw_all_sellers}
    _dw_options = [
        f"{s}  ({_dw_seller_client[s]})" if _dw_seller_client[s] != "—" else s
        for s in _dw_all_sellers
    ]
    _dw_opt_to_seller = dict(zip(_dw_options, _dw_all_sellers))

    _dw_fc1, _dw_fc2, _dw_fc3 = st.columns([2, 2, 1.2])
    with _dw_fc1:
        try:
            _dw_all_dates = sorted(date_filtered_df["reporting_date"].unique())
            _dw_min_d = datetime.strptime(min(_dw_all_dates), "%Y%m%d").date()
            _dw_max_d = datetime.strptime(max(_dw_all_dates), "%Y%m%d").date()
        except (ValueError, TypeError):
            _dw_min_d = _dw_max_d = datetime.now().date()
        _dw_d1, _dw_d2 = st.columns(2)
        with _dw_d1:
            _dw_start = st.date_input("From", value=_dw_min_d, min_value=_dw_min_d, max_value=_dw_max_d, key="dw_from")
        with _dw_d2:
            _dw_end = st.date_input("To", value=_dw_max_d, min_value=_dw_min_d, max_value=_dw_max_d, key="dw_to")
        if _dw_start > _dw_end:
            _dw_start, _dw_end = _dw_end, _dw_start
    with _dw_fc2:
        _dw_selected_opts = st.multiselect(
            "Select sellers",
            options=_dw_options,
            default=[],
            key="dw_seller_select",
            placeholder="Choose one or more sellers…",
        )
    with _dw_fc3:
        _dw_granularity = st.radio(
            "View by",
            ["Daily", "Weekly", "Monthly"],
            horizontal=False,
            key="dw_granularity",
        )

    _dw_selected_sellers = [_dw_opt_to_seller[o] for o in _dw_selected_opts]

    if not _dw_selected_sellers:
        st.info("Select at least one seller above to load the report.")
    else:
        _dw_start_str = _dw_start.strftime("%Y%m%d")
        _dw_end_str = _dw_end.strftime("%Y%m%d")
        daily_breach_df = date_filtered_df[
            (date_filtered_df["reporting_date"] >= _dw_start_str)
            & (date_filtered_df["reporting_date"] <= _dw_end_str)
            & (date_filtered_df["seller_type"].isin(_dw_selected_sellers))
        ]

        if daily_breach_df.empty:
            st.warning("No data for the selected date range and sellers.")
        else:
            daily_breach_df = daily_breach_df.copy()
            daily_breach_df["_client_grp"] = daily_breach_df["seller_type"].str.upper().map(CLIENT_MAP).fillna(daily_breach_df["seller_type"])

            _code_lookup = (
                daily_breach_df.groupby("_client_grp")["seller_type"]
                .apply(lambda x: "/".join(sorted(x.unique())))
                .to_dict()
            )

            _dw_period_dt = pd.to_datetime(daily_breach_df["reporting_date"], format="%Y%m%d", errors="coerce")
            if _dw_granularity == "Weekly":
                _period_keys = _dw_period_dt.dt.strftime("%G-W%V")
                _period_label_col = "Week"
            elif _dw_granularity == "Monthly":
                _period_keys = _dw_period_dt.dt.strftime("%Y-%m")
                _period_label_col = "Month"
            else:
                _period_keys = daily_breach_df["reporting_date"]
                _period_label_col = "Date"
            daily_breach_df["_period"] = _period_keys.values

            agg_daily = daily_breach_df.groupby(["_period", "_client_grp"]).agg(
                PHin=("PHin", "sum"),
                conv_num=("conv_num", "sum"),
                First_attempt_delivered=("First_attempt_delivered", "sum"),
                fac_deno=("fac_deno", "sum"),
                Breach_Num=("Breach_Num", "sum"),
                Breach_Den=("Breach_Den", "sum"),
                zero_attempt_num=("zero_attempt_num", "sum"),
                fm_picked=("fm_picked", "sum"),
                fm_created=("fm_created", "sum"),
            ).reset_index()

            cod_daily = (
                daily_breach_df[daily_breach_df["payment_type_norm"] == "COD"]
                .groupby(["_period", "_client_grp"])
                .agg(cod_vol=("PHin", "sum"), cod_conv=("conv_num", "sum"))
                .reset_index()
            )
            pp_daily = (
                daily_breach_df[daily_breach_df["payment_type_norm"] == "Prepaid"]
                .groupby(["_period", "_client_grp"])
                .agg(pp_vol=("PHin", "sum"), pp_conv=("conv_num", "sum"))
                .reset_index()
            )

            d_r = (
                agg_daily
                .merge(cod_daily, on=["_period", "_client_grp"], how="left")
                .merge(pp_daily, on=["_period", "_client_grp"], how="left")
                .fillna(0)
            )
            d_r["seller_type"] = d_r["_client_grp"].map(_code_lookup)
            d_r = d_r.drop(columns=["_client_grp"])

            d_r["Overall Conversion %"] = (d_r["conv_num"] / d_r["PHin"].replace(0, NAN) * 100).round(2)
            d_r["COD Conversion %"]     = (d_r["cod_conv"] / d_r["cod_vol"].replace(0, NAN) * 100).round(2)
            d_r["Prepaid Conversion %"] = (d_r["pp_conv"]  / d_r["pp_vol"].replace(0, NAN) * 100).round(2)
            d_r["FAC %"]                = (d_r["First_attempt_delivered"] / d_r["fac_deno"].replace(0, NAN) * 100).round(2)
            d_r["Breach %"]             = (d_r["Breach_Num"] / d_r["Breach_Den"].replace(0, NAN) * 100).round(2)
            d_r["ZRTO %"]               = (d_r["zero_attempt_num"] / d_r["PHin"].replace(0, NAN) * 100).round(2)
            d_r["COD Share %"]          = (d_r["cod_vol"] / d_r["PHin"].replace(0, NAN) * 100).round(2)
            d_r["Prepaid Share %"]      = (d_r["pp_vol"]  / d_r["PHin"].replace(0, NAN) * 100).round(2)
            d_r["FM Picked %"]          = (d_r["fm_picked"] / d_r["fm_created"].replace(0, NAN) * 100).round(2)
            d_r = d_r.fillna(0)

            d_r = d_r[d_r["PHin"] >= min_vol]

            if _dw_granularity == "Daily":
                d_r[_period_label_col] = (
                    d_r["_period"].str[6:8] + "-" + d_r["_period"].str[4:6] + "-" + d_r["_period"].str[:4]
                )
            elif _dw_granularity == "Monthly":
                _month_dt = pd.to_datetime(d_r["_period"] + "-01", format="%Y-%m-%d", errors="coerce")
                d_r[_period_label_col] = _month_dt.dt.strftime("%b %Y")
            else:
                d_r[_period_label_col] = d_r["_period"]

            daily_breach_display = d_r[[
                _period_label_col, "seller_type", "Breach %", "FAC %",
                "PHin", "ZRTO %", "FM Picked %",
                "Overall Conversion %", "COD Conversion %", "Prepaid Conversion %",
                "COD Share %", "Prepaid Share %", "_period",
            ]].rename(columns={
                "seller_type": "Seller",
                "PHin": "Volume",
            }).sort_values(["_period", "Seller"]).drop(columns=["_period"])
            daily_breach_display = add_client_col(daily_breach_display)

            _gran_word = {"Daily": "day", "Weekly": "week", "Monthly": "month"}[_dw_granularity]
            st.markdown(
                f"<div style='font-size:0.82rem;color:#64748B;margin-bottom:8px;'>"
                f"Showing <b>{len(daily_breach_display)}</b> rows · "
                f"<b>{len(_dw_selected_sellers)}</b> sellers · "
                f"grouped by <b>{_gran_word}</b> · "
                f"{_dw_start} to {_dw_end}</div>",
                unsafe_allow_html=True,
            )

            styled_daily_breach = (
                daily_breach_display.style
                .apply(_make_color_metric_vec(_get_thresh("Breach %"), True), subset=["Breach %"])
                .apply(_make_color_metric_vec(_get_thresh("ZRTO %"), True), subset=["ZRTO %"])
                .apply(_make_color_metric_vec(_get_thresh("FAC %"), False), subset=["FAC %"])
                .apply(_make_color_metric_vec(_get_thresh("FM Picked %"), False), subset=["FM Picked %"])
                .apply(_make_color_metric_vec(_get_thresh("Conv %"), False), subset=["Overall Conversion %", "COD Conversion %", "Prepaid Conversion %"])
                .apply(_color_volume_vec, subset=["Volume"])
                .format({
                    "Volume": "{:,.0f}",
                    "Breach %": "{:.1f}%",
                    "FAC %": "{:.1f}%",
                    "ZRTO %": "{:.2f}%",
                    "FM Picked %": "{:.1f}%",
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
elif page == "📈 Daily Trends":
    daily_df = merge_daily_by_client(build_daily_table(filtered_df))
    dates = sorted(daily_df["reporting_date"].unique())
    sellers = sorted(daily_df["seller_type"].unique())

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
    row_metrics = ["FAC %", "Breach %", "FM Picked %", "ZRTO %", "Conv %"]
    risk_flags = [False, True, False, True, False]

    def _vectorized_counts(src_df, period_col, ordered_periods, metrics, risks):
        """Pivot+diff approach: replaces O(periods×merges) with vectorized ops."""
        table = {}
        for m, is_risk in zip(metrics, risks):
            col = _metric_to_col.get(m, m)
            pivot = src_df.pivot_table(
                index="seller_type", columns=period_col, values=col, aggfunc="first",
            ).reindex(columns=ordered_periods)
            diff = pivot.diff(axis=1)
            if is_risk:
                imp_counts = (diff < 0).sum()
                dec_counts = (diff > 0).sum()
            else:
                imp_counts = (diff > 0).sum()
                dec_counts = (diff < 0).sum()
            cells = ["—"]
            for p in ordered_periods[1:]:
                imp, dec_ = int(imp_counts.get(p, 0)), int(dec_counts.get(p, 0))
                parts = []
                if imp > 0:
                    parts.append(f"{imp}↑")
                if dec_ > 0:
                    parts.append(f"{dec_}↓")
                cells.append(", ".join(parts) if parts else "—")
            table[m] = cells
        return table

    _p2_period_type = "Week" if compare_mode == "Weekly compare" else "Month"

    if compare_mode == "Day wise compare":
        period_labels = [fmt_date(d) for d in dates]
        table_data = _vectorized_counts(daily_df, "reporting_date", dates, row_metrics, risk_flags)
    else:
        period_agg = _aggregate_by_period(daily_df, _p2_period_type)
        periods = sorted(period_agg["_period"].unique())

        period_labels = periods
        table_data = _vectorized_counts(period_agg, "_period", periods, row_metrics, risk_flags)

    count_df = pd.DataFrame(table_data, index=period_labels).T
    count_df = count_df[period_labels[::-1]]
    count_df.index.name = "Metric"
    count_df = count_df.reset_index()

    _blank_metrics = {"ZRTO %", "Conv %"}
    _cutoff = (datetime.now() - timedelta(days=15)).strftime("%Y%m%d")
    _recent_cols: set = set()
    if compare_mode == "Day wise compare":
        _fmt_to_raw = {fmt_date(d): d for d in dates}
        for col in count_df.columns:
            rd = _fmt_to_raw.get(col)
            if rd and rd >= _cutoff:
                _recent_cols.add(col)
    else:
        _parsed_dates = pd.to_datetime(pd.Series(dates), format="%Y%m%d", errors="coerce")
        fmt = "%Y-W%W" if compare_mode == "Weekly compare" else "%Y-%m"
        _period_max: dict = {}
        for d, p in zip(dates, _parsed_dates.dt.strftime(fmt)):
            if d > _period_max.get(p, ""):
                _period_max[p] = d
        for p, mx in _period_max.items():
            if mx >= _cutoff:
                _recent_cols.add(p)
    if _recent_cols:
        _blank_mask = count_df["Metric"].isin(_blank_metrics)
        for col in _recent_cols:
            if col in count_df.columns:
                count_df.loc[_blank_mask, col] = ""

    render_sticky_table(count_df.set_index("Metric"), no_vscroll=True)

    st.divider()

    _trends_overall = calculate_summary_metrics(filtered_df)
    _metric_values = {
        "FAC %":       f"{_trends_overall.get('FAC %', 0):.1f}%",
        "Breach %":    f"{_trends_overall.get('Breach %', 0):.1f}%",
        "FM Picked %": f"{_trends_overall.get('FM Picked %', 0):.1f}%",
        "ZRTO %":      f"{_trends_overall.get('ZRTO %', 0):.2f}%",
        "Conv %":      f"{_trends_overall.get('Overall Conversion %', 0):.1f}%",
    }
    _risk_dot = {True: "#EF4444", False: "#22C55E"}

    _metric_names = list(METRIC_CONFIG.keys())
    _cards_html = ""
    for _mn in _metric_names:
        _mcfg = METRIC_CONFIG[_mn]
        _dot = _risk_dot[_mcfg["risk"]]
        _cards_html += (
            f'<div style="flex:1;text-align:center;padding:0.5rem 0.3rem;'
            f'border-left:1px solid #E2E8F0;">'
            f'<div style="font-size:0.62rem;font-weight:700;color:{_mcfg["color"]};'
            f'text-transform:uppercase;letter-spacing:0.05em;">{_mn}'
            f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
            f'background:{_dot};margin-left:5px;vertical-align:middle;"></span></div>'
            f'<div style="font-size:0.5rem;color:#94A3B8;margin-bottom:3px;">'
            f'{_mcfg["sub"]}</div>'
            f'<div style="font-size:1.15rem;font-weight:700;color:#0F172A;'
            f'font-family:\'IBM Plex Mono\',monospace;line-height:1;">'
            f'{_metric_values[_mn]}</div>'
            f'</div>'
        )
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#F8FAFC,#EFF6FF);'
        f'border:1px solid #E2E8F0;border-radius:14px;padding:0.5rem 0;'
        f'margin-bottom:0.5rem;display:flex;align-items:center;'
        f'box-shadow:0 1px 4px rgba(0,0,0,0.04);">'
        f'<div style="padding:0.4rem 1rem;min-width:170px;">'
        f'<div style="font-size:0.7rem;font-weight:700;color:#1E3A5F;'
        f'text-transform:uppercase;letter-spacing:0.06em;">'
        f'Performance Metrics Overview</div>'
        f'<div style="font-size:0.58rem;color:#94A3B8;margin-top:2px;">'
        f'📅 Period: {len(dates)} days · 👥 Sellers: {len(sellers)}</div>'
        f'</div>'
        f'{_cards_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.caption("select a metric to explore all panels below")
    metric = st.radio(
        "Active Metric",
        _metric_names,
        horizontal=True,
        label_visibility="collapsed",
    )
    cfg     = METRIC_CONFIG[metric]
    thresh  = _get_thresh(metric)
    is_risk = cfg["risk"]
    dec     = cfg["decimals"]

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 2 — Decline report: sellers performing worse vs previous period
    # ─────────────────────────────────────────────────────────────────────────
    _color_metric_val_vec = _make_color_metric_vec(thresh, is_risk)

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

    if dt_decline_mode == "Day":
        st.caption("Pick a date. Shows sellers whose metric got worse compared to the previous day.")
        _dt_period_df = daily_df.assign(_period=daily_df["reporting_date"])
        _dt_periods = dates

        try:
            _dt_min_d = datetime.strptime(min(dates), "%Y%m%d").date()
            _dt_max_d = datetime.strptime(max(dates), "%Y%m%d").date()
        except (ValueError, TypeError):
            _dt_min_d = _dt_max_d = datetime.now().date()

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
        if dt_decline_mode == "Week":
            st.caption("Pick a week. Shows sellers whose metric got worse compared to the previous week.")
        else:
            st.caption("Pick a month. Shows sellers whose metric got worse compared to the previous month.")

        _dt_period_df = _aggregate_by_period(daily_df, dt_decline_mode)
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
            dt_declined = dt_merged[dt_merged["Change"] >= 0].copy()
        else:
            dt_declined = dt_merged[dt_merged["Change"] <= 0].copy()

        dt_declined = dt_declined.sort_values("Change", ascending=not is_risk)
        dt_declined = dt_declined.rename(columns={"seller_type": "Seller"})
        dt_declined = add_client_col(dt_declined)

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
                .apply(_color_change_vec, subset=["Change"])
                .apply(_color_metric_val_vec, subset=["Current", "Previous"])
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

    if pv_mode == "Day":
        _pv_df = daily_df.assign(_period=daily_df["reporting_date"])
    else:
        _pv_df = _aggregate_by_period(daily_df, pv_mode)

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
        _pv_upper = _pv_df["seller_type"].str.upper()
        _pv_clients = _pv_df["seller_type"].map(_resolve_client_cached).str.upper()
        _pv_pat = "|".join(pv_sel_list)
        _pv_mask = _pv_upper.str.contains(_pv_pat, na=False) | _pv_clients.str.contains(_pv_pat, na=False)
        _pv_df = _pv_df[_pv_mask]

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

        pv_pivot = pv_pivot.sort_values("Avg", ascending=is_risk)
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
            .apply(_color_metric_val_vec, subset=[c for c in pv_pivot.columns if c not in _skip_cols])
            .format(pv_fmt_dict)
        )
        st.dataframe(styled_pv, use_container_width=True, height=500, hide_index=True)


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE 3 — THRESHOLD PERFORMANCE
# ═════════════════════════════════════════════════════════════════════════════
else:
    daily_df_tp = merge_daily_by_client(build_daily_table(filtered_df))
    dates_tp = sorted(daily_df_tp["reporting_date"].unique())
    sellers_tp = sorted(daily_df_tp["seller_type"].unique())

    st.markdown("### 🎯 Threshold Performance")
    st.caption(
        "Set custom thresholds for each metric. The table shows how many sellers "
        "meet or miss the threshold per date. The decline report lists sellers "
        "performing at or worse than the threshold."
    )

    # ── Threshold inputs ──────────────────────────────────────────────────────
    _tp_metrics = {
        "FAC %":       {"default": 70.0, "risk": False, "col": "FAC %",       "dec": 1},
        "Breach %":    {"default": 10.0, "risk": True,  "col": "Breach %",    "dec": 1},
        "FM Picked %": {"default": 80.0, "risk": False, "col": "FM Picked %", "dec": 1},
        "ZRTO %":      {"default": 1.5,  "risk": True,  "col": "ZRTO %",      "dec": 2},
        "Conv %":      {"default": 65.0, "risk": False, "col": "Conv %",      "dec": 1},
    }

    st.markdown(
        '<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;'
        'padding:0.7rem 1rem;margin-bottom:0.8rem;">'
        '<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.08em;'
        'color:#64748B;font-weight:600;margin-bottom:4px;">Set Thresholds</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    _tp_thresh = {}
    _tp_cols = st.columns(len(_tp_metrics))
    for _tc, (_tm, _tcfg) in zip(_tp_cols, _tp_metrics.items()):
        with _tc:
            _tp_thresh[_tm] = st.number_input(
                _tm,
                value=_tcfg["default"],
                step=0.5 if _tcfg["dec"] > 1 else 1.0,
                format=f"%.{_tcfg['dec']}f",
                key=f"tp_thresh_{_tm}",
            )

    st.divider()

    # ── Compare mode ──────────────────────────────────────────────────────────
    tp_compare = st.radio(
        "Compare",
        ["Day wise compare", "Weekly compare", "Monthly compare"],
        horizontal=True,
        label_visibility="collapsed",
        key="tp_compare_mode",
    )

    # Build period-level data
    _tp3_period_type = "Week" if tp_compare == "Weekly compare" else "Month"

    if tp_compare == "Day wise compare":
        _tp_src = daily_df_tp.assign(_period=daily_df_tp["reporting_date"])
        _tp_periods = dates_tp
        _tp_labels = [fmt_date(d) for d in dates_tp]
    else:
        _tp_src = _aggregate_by_period(daily_df_tp, _tp3_period_type)
        _tp_periods = sorted(_tp_src["_period"].unique())
        _tp_labels = _tp_periods

    # ── Threshold Count Table ─────────────────────────────────────────────────
    st.markdown("#### 📊 Seller Threshold Count")
    if tp_compare == "Day wise compare":
        st.caption("✅ meeting threshold · ❌ missing threshold (including same for risk metrics)")
    elif tp_compare == "Weekly compare":
        st.caption("✅ meeting threshold · ❌ missing threshold per week")
    else:
        st.caption("✅ meeting threshold · ❌ missing threshold per month")

    _tp_table = {}
    for _tm, _tcfg in _tp_metrics.items():
        col = _tcfg["col"]
        th = _tp_thresh[_tm]
        is_risk = _tcfg["risk"]

        pivot = _tp_src.pivot_table(
            index="seller_type", columns="_period", values=col, aggfunc="first",
        ).reindex(columns=_tp_periods)

        if is_risk:
            good = (pivot <= th).sum()
            bad = (pivot > th).sum()
        else:
            good = (pivot >= th).sum()
            bad = (pivot < th).sum()

        cells = []
        for p in _tp_periods:
            g, b = int(good.get(p, 0)), int(bad.get(p, 0))
            cells.append(f"✅{g}, ❌{b}")
        _tp_table[_tm] = cells

    tp_count_df = pd.DataFrame(_tp_table, index=_tp_labels).T
    tp_count_df = tp_count_df[_tp_labels[::-1]]
    tp_count_df.index.name = "Metric"
    tp_count_df = tp_count_df.reset_index()

    _tp_blank = {"ZRTO %", "Conv %"}
    _tp_cutoff = (datetime.now() - timedelta(days=15)).strftime("%Y%m%d")
    _tp_recent_cols: set = set()
    if tp_compare == "Day wise compare":
        _tp_fmt_to_raw = {fmt_date(d): d for d in dates_tp}
        for _tpc in tp_count_df.columns:
            rd = _tp_fmt_to_raw.get(_tpc)
            if rd and rd >= _tp_cutoff:
                _tp_recent_cols.add(_tpc)
    else:
        _tp_parsed = pd.to_datetime(pd.Series(dates_tp), format="%Y%m%d", errors="coerce")
        fmt = "%Y-W%W" if tp_compare == "Weekly compare" else "%Y-%m"
        _tp_pmax: dict = {}
        for d, p in zip(dates_tp, _tp_parsed.dt.strftime(fmt)):
            if d > _tp_pmax.get(p, ""):
                _tp_pmax[p] = d
        for p, mx in _tp_pmax.items():
            if mx >= _tp_cutoff:
                _tp_recent_cols.add(p)
    if _tp_recent_cols:
        _tp_blank_mask = tp_count_df["Metric"].isin(_tp_blank)
        for _tpc in _tp_recent_cols:
            if _tpc in tp_count_df.columns:
                tp_count_df.loc[_tp_blank_mask, _tpc] = ""

    render_sticky_table(tp_count_df.set_index("Metric"), no_vscroll=True)

    st.divider()

    # ── Threshold Decline Report ──────────────────────────────────────────────
    st.markdown("#### 📉 Threshold Decline Report")
    st.caption("Sellers performing at or worse than the set threshold for the selected metric and date.")

    _tp_metric_names = list(_tp_metrics.keys())
    tp_metric = st.radio(
        "Metric",
        _tp_metric_names,
        horizontal=True,
        label_visibility="collapsed",
        key="tp_decline_metric",
    )
    _tp_mcfg = _tp_metrics[tp_metric]
    _tp_th = _tp_thresh[tp_metric]
    _tp_is_risk = _tp_mcfg["risk"]
    _tp_dec = _tp_mcfg["dec"]

    tp_decline_mode = st.radio(
        "Period",
        ["Day", "Week", "Month"],
        horizontal=True,
        label_visibility="collapsed",
        key="tp_decline_period",
    )

    if tp_decline_mode == "Day":
        _tp_decline_df = daily_df_tp.assign(_period=daily_df_tp["reporting_date"])
        _tp_decline_periods = dates_tp

        try:
            _tp_min_d = datetime.strptime(min(dates_tp), "%Y%m%d").date()
            _tp_max_d = datetime.strptime(max(dates_tp), "%Y%m%d").date()
        except (ValueError, TypeError):
            _tp_min_d = _tp_max_d = datetime.now().date()

        tp_sel_date = st.date_input(
            "Select date",
            value=_tp_max_d,
            min_value=_tp_min_d,
            max_value=_tp_max_d,
            key="tp_decline_day_cal",
        )
        tp_sel_period = tp_sel_date.strftime("%Y%m%d")
        tp_sel_label = fmt_date(tp_sel_period)

        if tp_sel_period not in _tp_decline_periods:
            candidates = [d for d in _tp_decline_periods if d <= tp_sel_period]
            if candidates:
                tp_sel_period = candidates[-1]
                tp_sel_label = fmt_date(tp_sel_period)
            elif _tp_decline_periods:
                tp_sel_period = _tp_decline_periods[-1]
                tp_sel_label = fmt_date(tp_sel_period)
    else:
        _tp_decline_df = _aggregate_by_period(daily_df_tp, tp_decline_mode)
        _tp_decline_periods = sorted(_tp_decline_df["_period"].unique())

        tp_sel_label = st.selectbox(
            f"Select {tp_decline_mode.lower()}",
            _tp_decline_periods,
            index=len(_tp_decline_periods) - 1,
            key="tp_decline_period_sel",
        )
        tp_sel_period = tp_sel_label

    # Filter to selected period and find sellers at/worse than threshold
    _tp_period_data = _tp_decline_df[_tp_decline_df["_period"] == tp_sel_period][
        ["seller_type", _tp_mcfg["col"]]
    ].copy()
    _tp_period_data = _tp_period_data.rename(columns={_tp_mcfg["col"]: "Value"})

    if _tp_is_risk:
        tp_bad = _tp_period_data[_tp_period_data["Value"] >= _tp_th].copy()
    else:
        tp_bad = _tp_period_data[_tp_period_data["Value"] <= _tp_th].copy()

    tp_bad = tp_bad.sort_values("Value", ascending=not _tp_is_risk)
    tp_bad["Threshold"] = _tp_th
    tp_bad["Gap"] = tp_bad["Value"] - _tp_th
    tp_bad = tp_bad.rename(columns={"seller_type": "Seller"})
    tp_bad = add_client_col(tp_bad)

    if tp_bad.empty:
        st.success(
            f"All sellers are meeting the {tp_metric} threshold of {_tp_th}% "
            f"on {tp_sel_label}."
        )
    else:
        st.markdown(
            f"<div style='font-size:0.82rem;color:#64748B;margin-bottom:8px;'>"
            f"<b>{len(tp_bad)}</b> sellers at or worse than "
            f"<b>{tp_metric} = {_tp_th}%</b> on <b>{tp_sel_label}</b></div>",
            unsafe_allow_html=True,
        )

        _tp_fmt = f"{{:.{_tp_dec}f}}%"
        _tp_color_val = _make_color_metric_vec(_tp_th, _tp_is_risk)

        styled_tp = (
            tp_bad.style
            .apply(_tp_color_val, subset=["Value"])
            .apply(_color_gap_vec, subset=["Gap"])
            .format({"Value": _tp_fmt, "Threshold": _tp_fmt, "Gap": _tp_fmt})
        )
        st.dataframe(styled_tp, use_container_width=True, height=450, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center;color:#98A2B3;font-size:0.72rem;'>"
    "Seller Performance Dashboard · Data refreshed on load</div>",
    unsafe_allow_html=True,
)