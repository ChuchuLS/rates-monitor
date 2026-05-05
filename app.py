"""
Rates & Credit Monitor — single-page Streamlit dashboard, OFR dark theme.

Layout (top to bottom):
  Row 1: Curve slopes — 2s10s + 5s30s for US, DE, JP, AU, UK, CA (6x2 grid)
  Row 2: Real rate curves — 10Y linker yields for US, CA, DE, UK, JP, AU
  Row 3: Money-market spreads monitor — 5 OFR-style panels with label boxes
  Row 4: XCCY basis swaps — EUR, JPY, AUD, GBP, CAD
  Row 5: Credit — IG/HY OAS, bank CDS, EMBI sovereign
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Rates & Credit Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Password gate
# ---------------------------------------------------------------------------
def _check_password() -> bool:
    """
    Simple password gate. Reads the expected password from Streamlit secrets
    (key: 'app_password'). If the secret isn't set, the gate is disabled and
    the app runs normally — useful for local development.

    Returns True if the user has authenticated, False otherwise.
    """
    expected = st.secrets.get("app_password") if hasattr(st, "secrets") else None
    if not expected:
        # No password configured — let everyone in (e.g. local dev)
        return True

    if st.session_state.get("password_correct"):
        return True

    st.markdown(
        """
        <div style="max-width:420px;margin:5rem auto 1rem;
                    padding:2rem;background:#0a0a0a;
                    border:1px solid #1a1a1a;border-radius:6px;
                    font-family:Inter,system-ui,sans-serif;color:#fff;">
          <div style="font-size:18px;font-weight:700;letter-spacing:0.06em;
                      text-transform:uppercase;margin-bottom:6px;">
            Rates & Credit Monitor
          </div>
          <div style="font-size:11px;color:#888;letter-spacing:0.08em;
                      text-transform:uppercase;margin-bottom:1.5rem;">
            Authentication required
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pwd = st.text_input(
        "Password", type="password", key="password_input",
        label_visibility="collapsed", placeholder="Enter password",
    )
    if pwd:
        if pwd == expected:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


if not _check_password():
    st.stop()


DATA_PATH = Path(__file__).parent / "data" / "DATA.xlsx"

# ---------------------------------------------------------------------------
# Global dark theme — applied to the whole Streamlit page
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Page background */
    .stApp {
        background-color: #0a0a0a;
        color: #e0e0e0;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #050505;
        border-right: 1px solid #1a1a1a;
    }
    section[data-testid="stSidebar"] * {
        color: #ccc !important;
    }
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        letter-spacing: 0.04em;
        font-family: 'Inter', system-ui, sans-serif !important;
    }
    /* Captions and small text */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #888 !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        font-size: 11px !important;
    }
    /* Markdown body text */
    .stMarkdown p { color: #ccc; }
    /* Horizontal dividers */
    hr {
        border-color: #1a1a1a !important;
        margin: 0.75rem 0 !important;
    }
    /* Radio buttons in sidebar */
    [data-testid="stSidebar"] [role="radiogroup"] label {
        color: #ccc !important;
        font-size: 12px !important;
    }
    /* Plotly chart container — remove default white frame */
    [data-testid="stPlotlyChart"] {
        background-color: transparent !important;
    }
    /* Reduce default block padding for tighter dashboard feel */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 100% !important;
    }
    /* Hide Streamlit Cloud chrome: top toolbar (GitHub icon, Share, Deploy
       button, hamburger menu), the colored decoration bar, and the
       "Hosted with Streamlit" footer badge */
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden !important; display: none !important; }
    header { visibility: hidden !important; display: none !important; }
    footer { visibility: hidden !important; display: none !important; }
    .viewerBadge_container__1QSob { display: none !important; }
    .viewerBadge_link__1S137 { display: none !important; }
    /* Section header style */
    .section-header {
        background: #0a0a0a;
        padding: 0.6rem 0;
        margin: 0.5rem 0 0.25rem 0;
        border-bottom: 1px solid #1a1a1a;
    }
    .section-title {
        font-size: 18px;
        font-weight: 700;
        letter-spacing: 0.06em;
        color: #ffffff;
        text-transform: uppercase;
    }
    .section-sub {
        font-size: 10px;
        color: #888;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-top: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Ticker registry
# ---------------------------------------------------------------------------
TICKERS = {
    # Curve slopes — 2s10s
    "US_2s10s": "USYC2Y10 INDEX",
    "DE_2s10s": "DEYC2Y10 INDEX",
    "JP_2s10s": "JPYC2Y10 INDEX",
    "AU_2s10s": "AUYC2Y10 INDEX",
    "UK_2s10s": "UKYC2Y10 INDEX",
    "CA_2s10s": "CAYC2Y10 INDEX",
    # Curve slopes — 5s30s (or country equivalent)
    "US_5s30s": "USYC5Y30 INDEX",
    "DE_5s30s": "DE020510 INDEX",
    "JP_5s30s": "JPYC1030 INDEX",
    "AU_5s30s": "AD020510 INDEX",
    "UK_5s30s": "UK020510 INDEX",
    "CA_5s30s": "CB020510 INDEX",
    # Real rates 10Y
    # Real rates — 10Y (kept for backward compat / one-off charts)
    "US_real_10y": "GTII10 GOVT",
    "CA_real_10y": "GTCADII10Y GOVT",
    "DE_real_10y": "GTDEMII10Y GOVT",
    "UK_real_10y": "GTGBPII10Y GOVT",
    "JP_real_10y": "GTJPYII10Y GOVT",
    "AU_real_10y": "GTAUDII10YR GOVT",
    # Real rates — full term structure for curve plots
    "US_real_5y":  "GTII5 GOVT",   "US_real_30y": "GTII30 GOVT",
    "UK_real_5y":  "GTGBPII5Y GOVT",  "UK_real_30y": "GTGBPII30Y GOVT",
    "DE_real_3y":  "GTDEMII3Y GOVT",  "DE_real_7y":  "GTDEMII7Y GOVT",
    "DE_real_25y": "GTDEMII25Y GOVT",
    "JP_real_5y":  "GTJPYII5Y GOVT",  "JP_real_7y":  "GTJPYII7Y GOVT",
    "AU_real_5y":  "GTAUDII5YR GOVT",
    "CA_real_5y":  "GTCADII5Y GOVT",  "CA_real_30y": "GTCADII30Y GOVT",
    # Money-market funding rates
    "SOFR": "SOFRRATE INDEX",
    "IORB": "IRRBIOER INDEX",
    "EFFR": "FEDL01 INDEX",
    "GCF": "UREPGATO INDEX",
    "TGCR": "TGCRRATE INDEX",
    "RRP": "FDTRFTRL INDEX",
    "BGCR": "USBGRATE INDEX",
    "TPR": "UREPTATO INDEX",
    # XCCY basis swaps (3M)
    "XCCY_EUR": "EUXOQQC CURNCY",
    "XCCY_GBP": "BPXOQQC CURNCY",
    "XCCY_JPY": "JYBSS3M CURNCY",
    "XCCY_CAD": "CDXOQQC CURNCY",
    "XCCY_AUD": "ADBSQQC CURNCY",
    # XCCY basis swaps (12M / 1Y)
    "XCCY12_EUR": "EUXOQQ1 CURNCY",
    "XCCY12_GBP": "BPXOQQ1 CURNCY",
    "XCCY12_JPY": "JYBSS12M CURNCY",
    "XCCY12_CAD": "CDXOQQ1 CURNCY",
    "XCCY12_AUD": "ADBSQQ1 CURNCY",
    # Credit
    "IG_OAS": "LUACOAS INDEX",
    "HY_OAS": "LF98OAS INDEX",
    "EMBI": "JPEIGLSP INDEX",
    "CDS_BOFA": "BOFA CDS USD SR 5Y D14 CORP",
    "CDS_JPM": "JPMCC CDS USD SR 5Y D14 CORP",
    "CDS_DB_SR": "DB CDS EUR SR 5Y D14 CORP",
    "CDS_DB_SUB": "DB CDS EUR SUB 5Y D14 CORP",
    # Nominal yields — 2/5/10/30 by country (used for regime classification)
    "US_2Y":  "USGG2YR INDEX",  "US_5Y":  "USGG5YR INDEX",
    "US_10Y": "USGG10YR INDEX", "US_30Y": "USGG30YR INDEX",
    "DE_2Y":  "GDBR2 INDEX",    "DE_5Y":  "GDBR5 INDEX",
    "DE_10Y": "GDBR10 INDEX",   "DE_30Y": "GDBR30 INDEX",
    "JP_2Y":  "GJGB2 INDEX",    "JP_5Y":  "GJGB5 INDEX",
    "JP_10Y": "GJGB10 INDEX",   "JP_30Y": "GJGB30 INDEX",
    "UK_2Y":  "GUKG2 INDEX",    "UK_5Y":  "GUKG5 INDEX",
    "UK_10Y": "GUKG10 INDEX",   "UK_30Y": "GUKG30 INDEX",
    "CA_2Y":  "GCAN2YR INDEX",  "CA_5Y":  "GCAN5YR INDEX",
    "CA_10Y": "GCAN10YR INDEX", "CA_30Y": "GCAN30YR INDEX",
    "AU_2Y":  "GACGB2 INDEX",   "AU_5Y":  "GACGB5 INDEX",
    "AU_10Y": "GACGB10 INDEX",  "AU_30Y": "GACGB30 INDEX",
    # --- Inflation expectations -------------------------------------------
    # US TIPS breakevens
    "BE_2Y":  "USGGBE02 INDEX",  "BE_5Y":  "USGGBE05 INDEX",
    "BE_10Y": "USGGBE10 INDEX",  "BE_20Y": "USGGBE20 INDEX",
    "BE_30Y": "USGGBE30 INDEX",
    # USD zero-coupon inflation swaps
    "ZCIS_1Y":  "USSWIT1 CURNCY",   "ZCIS_2Y":  "USSWIT2 CURNCY",
    "ZCIS_3Y":  "USSWIT3 CURNCY",   "ZCIS_4Y":  "USSWIT4 CURNCY",
    "ZCIS_5Y":  "USSWIT5 CURNCY",   "ZCIS_7Y":  "USSWIT7 CURNCY",
    "ZCIS_10Y": "USSWIT10 CURNCY",  "ZCIS_20Y": "USSWIT20 CURNCY",
    "ZCIS_30Y": "USSWIT30 CURNCY",
    # 5Y5Y forward inflation swap
    "INFL_5Y5Y": "FWISUS55 INDEX",
    # --- Money market additions -------------------------------------------
    "TOMO_TCSO": "TOMOTCSO INDEX",
    "USRG_1T":   "USRG1T CURNCY",
    # --- Liquidity --------------------------------------------------------
    "FED_RESERVES": "FARBRBFB INDEX",
    "FCI_BBG":      "BFCIUS INDEX",
    "FCI_NFCI":     "NFCIINDX INDEX",
    # --- Credit indices (CDX/iTraxx) --------------------------------------
    "CDX_IG":       "IBOXUMAE CBBT CURNCY",
    "CDX_HY":       "IBOXHYAE CBIN CURNCY",
    "CDX_EM":       "IBOXUMSE CURNCY",
    "ITRX_EUROPE":  "ITRXEBE CBBT CURNCY",
    "ITRX_XOVER":   "ITRXEXE CBBT CURNCY",
    "ITRX_SR_FIN":  "ITRXESE CBBT CURNCY",
    "ITRX_SUB_FIN": "ITRXEUE CBBT CURNCY",
    "ITRX_JAPAN":   "ITRXAJE CBIN CURNCY",
    "ITRX_ASIA_XJ": "ITRXAGE CBBT CURNCY",
    "ITRX_AUS":     "ITRXAAE CBBT CURNCY",
    # --- Mortgage ---------------------------------------------------------
    "MTG_30Y": "APORF30Y INDEX",
}

# Countries with full 2/5/10/30 nominal coverage for regime classification
REGIME_COUNTRIES = ("US", "DE", "JP", "UK", "CA", "AU")
# Regime color map (matches the Bloomberg Studio screenshot)
REGIME_COLORS = {
    "bull_steepener":   "#67c757",  # green
    "bear_steepener":   "#e64545",  # red
    "steepener_twist":  "#f0a020",  # orange
    "bull_flattener":   "#9fc8e8",  # light blue
    "bear_flattener":   "#5e95c2",  # blue
    "flattener_twist":  "#f0e040",  # yellow
    "none":             "#444444",  # neutral grey for unclassified
}
REGIME_LABELS = {
    "bull_steepener":   "Bull steepener",
    "bear_steepener":   "Bear steepener",
    "steepener_twist":  "Steepener twist",
    "bull_flattener":   "Bull flattener",
    "bear_flattener":   "Bear flattener",
    "flattener_twist":  "Flattener twist",
}

# ---------------------------------------------------------------------------
# Color palette — OFR dark theme
# ---------------------------------------------------------------------------
BG = "#0a0a0a"
PANEL_BG = "#0f0f0f"
LINE_WHITE = "#ffffff"
GRID = "rgba(255,255,255,0.05)"
TEXT_DIM = "#888"
TEXT_VERY_DIM = "#666"

# Accent line colors for variety on multi-series charts
ACCENT_GREEN = "#5fb04f"
ACCENT_RED = "#d04848"
ACCENT_AMBER = "#d99830"
ACCENT_CYAN = "#4fa8b8"
ACCENT_PURPLE = "#9080d0"

# Note box colors (OFR style)
NOTE_RED_BG = "rgba(120,30,30,0.85)"
NOTE_RED_BORDER = "#C04040"
NOTE_RED_TEXT = "#FFB0B0"
NOTE_GREEN_BG = "rgba(30,80,40,0.85)"
NOTE_GREEN_BORDER = "#40A060"
NOTE_GREEN_TEXT = "#B0E8B8"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading Bloomberg data...")
def load_data() -> pd.DataFrame:
    df = pd.read_excel(DATA_PATH, sheet_name="Sheet1", header=0)
    df = df.rename(columns={df.columns[0]: "Date"})
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").set_index("Date")
    # Normalize column names to upper-case so ticker lookups are robust to
    # mixed casing across Bloomberg pulls ("Index" vs "INDEX", etc.)
    df.columns = [c.upper() if isinstance(c, str) else c for c in df.columns]
    return df


def get_series(df: pd.DataFrame, key: str) -> pd.Series:
    col = TICKERS.get(key)
    if col is None:
        return pd.Series(dtype=float)
    # Case-insensitive lookup
    col_upper = col.upper()
    if col_upper not in df.columns:
        return pd.Series(dtype=float)
    return df[col_upper].dropna()


def date_filter(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return df.loc[(df.index >= start) & (df.index <= end)]


# ---------------------------------------------------------------------------
# Chart builders — all dark-themed
# ---------------------------------------------------------------------------
DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=BG,
    plot_bgcolor=BG,
    font=dict(family="Inter, system-ui, sans-serif", size=10, color=TEXT_DIM),
    hovermode="x unified",
    showlegend=False,
)


def section_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="section-header">
          <div class="section-title">{title}</div>
          <div class="section-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mini_dark(series: pd.Series, title: str, color: str = LINE_WHITE,
              height: int = 180, zero_line: bool = True,
              fmt: str = "{:+.1f}") -> go.Figure:
    """Compact dark line chart with last-value badge."""
    fig = go.Figure()
    if len(series):
        fig.add_trace(go.Scatter(
            x=series.index, y=series.values, mode="lines",
            line=dict(color=color, width=1.1),
            hovertemplate="%{x|%Y-%m-%d}: %{y:.2f}<extra></extra>",
        ))
        # Last-point marker
        fig.add_trace(go.Scatter(
            x=[series.index[-1]], y=[series.iloc[-1]], mode="markers",
            marker=dict(color=color, size=5, line=dict(color=BG, width=1)),
            hoverinfo="skip", showlegend=False,
        ))

    if zero_line:
        fig.add_hline(y=0, line=dict(color=TEXT_VERY_DIM, width=0.5, dash="dot"))

    last_val = series.iloc[-1] if len(series) else float("nan")
    last_str = fmt.format(last_val) if pd.notna(last_val) else "—"
    last_color = ACCENT_GREEN if (pd.notna(last_val) and last_val >= 0) else ACCENT_RED
    title_html = (
        f"<span style='color:#fff;font-weight:700;letter-spacing:0.05em'>"
        f"{title.upper()}</span>  "
        f"<span style='color:{last_color};font-size:10px;font-weight:700'>"
        f"{last_str}</span>"
    )

    fig.update_layout(
        **DARK_LAYOUT, height=height,
        margin=dict(l=35, r=10, t=28, b=22),
        title=dict(text=title_html, font=dict(size=10),
                   x=0, xanchor="left", y=0.97),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(size=8, color=TEXT_DIM),
                     linecolor="#222")
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                     tickfont=dict(size=8, color=TEXT_DIM), linecolor="#222")
    return fig


def classify_regime(short: pd.Series, long_: pd.Series,
                    lookback: int) -> tuple[pd.Series, pd.Series]:
    """
    Classify curve regime based on lookback comparison.

    Returns (slope, regime) where regime ∈ {bull/bear steepener, steepener
    twist, bull/bear flattener, flattener twist, none}.

    Logic mirrors the Bloomberg Studio template:
      - dc = slope - slope_lookback   (curve change)
      - ds = short - short_lookback   (short-rate change)
      - dl = long - long_lookback     (long-rate change)

      Steepening (dc > 0):
        ds < 0 & dl < 0  → bull steepener  (rally, short outperforms)
        ds > 0 & dl > 0  → bear steepener  (sell-off, long underperforms)
        ds < 0 & dl > 0  → steepener twist (mixed)
      Flattening (dc < 0):
        ds < 0 & dl < 0  → bull flattener  (rally, long outperforms)
        ds > 0 & dl > 0  → bear flattener  (sell-off, short underperforms)
        ds > 0 & dl < 0  → flattener twist (mixed)
    """
    short, long_ = short.align(long_, join="inner")
    slope = (long_ - short) * 100.0  # bp

    ds = short - short.shift(lookback)
    dl = long_ - long_.shift(lookback)
    dc = slope - slope.shift(lookback)

    regime = pd.Series("none", index=slope.index, dtype="object")
    regime[(dc > 0) & (ds < 0) & (dl < 0)] = "bull_steepener"
    regime[(dc > 0) & (ds > 0) & (dl > 0)] = "bear_steepener"
    regime[(dc > 0) & (ds < 0) & (dl > 0)] = "steepener_twist"
    regime[(dc < 0) & (ds < 0) & (dl < 0)] = "bull_flattener"
    regime[(dc < 0) & (ds > 0) & (dl > 0)] = "bear_flattener"
    regime[(dc < 0) & (ds > 0) & (dl < 0)] = "flattener_twist"
    return slope, regime


def regime_panel(slope: pd.Series, regime: pd.Series,
                 title: str, height: int = 170,
                 fallback_color: str = ACCENT_AMBER) -> go.Figure:
    """
    Histogram of slope colored by regime, with slope line overlaid in amber.
    Bloomberg Studio style — bars span from zero up/down to the slope value.
    """
    fig = go.Figure()
    if len(slope):
        # Build per-regime bar traces so the legend works and colors are right
        bar_colors = regime.map(REGIME_COLORS).fillna(REGIME_COLORS["none"])
        fig.add_trace(go.Bar(
            x=slope.index, y=slope.values,
            marker=dict(color=bar_colors.values, line=dict(width=0)),
            customdata=regime.map(REGIME_LABELS).fillna("—").values,
            hovertemplate=(
                "%{x|%Y-%m-%d}<br>"
                "Slope: %{y:.1f} bp<br>"
                "Regime: %{customdata}<extra></extra>"
            ),
            showlegend=False,
        ))
        # Slope line overlay (amber, matches the Bloomberg screenshot)
        fig.add_trace(go.Scatter(
            x=slope.index, y=slope.values, mode="lines",
            line=dict(color=fallback_color, width=1.2),
            hoverinfo="skip", showlegend=False,
        ))
        # Last-point marker
        fig.add_trace(go.Scatter(
            x=[slope.index[-1]], y=[slope.iloc[-1]], mode="markers",
            marker=dict(color=fallback_color, size=5,
                        line=dict(color=BG, width=1)),
            hoverinfo="skip", showlegend=False,
        ))

    fig.add_hline(y=0, line=dict(color=TEXT_VERY_DIM, width=0.5, dash="dot"))

    last_val = slope.iloc[-1] if len(slope) else float("nan")
    last_str = f"{last_val:+.0f}bp" if pd.notna(last_val) else "—"
    last_color = ACCENT_GREEN if (pd.notna(last_val) and last_val >= 0) else ACCENT_RED
    title_html = (
        f"<span style='color:#fff;font-weight:700;letter-spacing:0.05em'>"
        f"{title.upper()}</span>  "
        f"<span style='color:{last_color};font-size:10px;font-weight:700'>"
        f"{last_str}</span>"
    )

    fig.update_layout(
        **DARK_LAYOUT, height=height,
        margin=dict(l=35, r=10, t=28, b=22),
        title=dict(text=title_html, font=dict(size=10),
                   x=0, xanchor="left", y=0.97),
        bargap=0.0,
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(size=8, color=TEXT_DIM),
                     linecolor="#222")
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                     tickfont=dict(size=8, color=TEXT_DIM), linecolor="#222")
    return fig



def ofr_chart(series: pd.Series, top_note: str | None,
              bottom_note: str | None, height: int = 160) -> go.Figure:
    """OFR-style dark chart with red/green interpretation note boxes."""
    fig = go.Figure()
    s = series.dropna()
    if len(s):
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, mode="lines",
            line=dict(color=LINE_WHITE, width=1),
            hovertemplate="%{x|%Y-%m-%d}: %{y:.3f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[s.index[-1]], y=[s.iloc[-1]], mode="markers",
            marker=dict(color=LINE_WHITE, size=6, line=dict(color=BG, width=1)),
            hoverinfo="skip", showlegend=False,
        ))

    fig.add_hline(y=0, line=dict(color=TEXT_VERY_DIM, width=0.5, dash="dot"))

    if top_note:
        fig.add_annotation(
            xref="paper", yref="paper", x=0.5, y=0.92,
            text=f"<b>{top_note}</b>", showarrow=False,
            bgcolor=NOTE_RED_BG, bordercolor=NOTE_RED_BORDER, borderwidth=1,
            font=dict(color=NOTE_RED_TEXT, size=9, family="Inter, sans-serif"),
            align="center",
        )
    if bottom_note:
        fig.add_annotation(
            xref="paper", yref="paper", x=0.5, y=0.08,
            text=f"<b>{bottom_note}</b>", showarrow=False,
            bgcolor=NOTE_GREEN_BG, bordercolor=NOTE_GREEN_BORDER, borderwidth=1,
            font=dict(color=NOTE_GREEN_TEXT, size=9, family="Inter, sans-serif"),
            align="center",
        )

    fig.update_layout(
        **DARK_LAYOUT, height=height,
        margin=dict(l=10, r=55, t=10, b=20),
        yaxis=dict(side="right", showgrid=True, gridcolor=GRID,
                   zeroline=False, tickfont=dict(color=TEXT_DIM, size=9),
                   title=dict(text="<i>spread</i>",
                              font=dict(size=9, color="#aaa"), standoff=2)),
        xaxis=dict(showgrid=False, tickfont=dict(color=TEXT_DIM, size=9)),
    )
    return fig


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
df = load_data()

with st.sidebar:
    st.markdown(
        """
        <div style="padding:0.5rem 0 0.25rem;">
          <div style="font-size:14px;font-weight:700;letter-spacing:0.08em;
                      color:#fff;text-transform:uppercase;">
            Rates & Credit Monitor
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"{df.index.min().date()} → {df.index.max().date()}")
    st.divider()

    range_preset = st.radio(
        "LOOKBACK",
        ["6M", "1Y", "3Y", "5Y", "10Y", "Max", "Custom"],
        index=2,
    )

    end_date = df.index.max()
    if range_preset == "6M":
        start_date = end_date - pd.DateOffset(months=6)
    elif range_preset == "1Y":
        start_date = end_date - pd.DateOffset(years=1)
    elif range_preset == "3Y":
        start_date = end_date - pd.DateOffset(years=3)
    elif range_preset == "5Y":
        start_date = end_date - pd.DateOffset(years=5)
    elif range_preset == "10Y":
        start_date = end_date - pd.DateOffset(years=10)
    elif range_preset == "Max":
        start_date = df.index.min()
    else:
        custom = st.date_input(
            "Range",
            value=(end_date - pd.DateOffset(years=3), end_date),
            min_value=df.index.min().date(),
            max_value=df.index.max().date(),
        )
        if isinstance(custom, tuple) and len(custom) == 2:
            start_date = pd.Timestamp(custom[0])
            end_date = pd.Timestamp(custom[1])
        else:
            start_date = end_date - pd.DateOffset(years=3)

    st.divider()
    st.markdown(
        """
        <div style="font-size:9px;color:#666;letter-spacing:0.1em;
                    text-transform:uppercase;line-height:1.8;">
          1 — Curve Explorer<br>
          2 — Inflation Expectations<br>
          3 — Money-market spreads<br>
          4 — Liquidity<br>
          5 — XCCY basis<br>
          6 — Credit
        </div>
        """,
        unsafe_allow_html=True,
    )

dff = date_filter(df, start_date, end_date)

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div style="padding:0 0 1rem 0;border-bottom:1px solid #1a1a1a;
                margin-bottom:1rem;">
      <div style="font-size:24px;font-weight:700;letter-spacing:0.06em;
                  color:#fff;text-transform:uppercase;">
        Rates & Credit Monitor
      </div>
      <div style="font-size:10px;color:#888;letter-spacing:0.1em;
                  text-transform:uppercase;margin-top:4px;">
        Latest: <span style="color:#ccc;font-weight:700;">
        {df.index.max().strftime('%b %d, %Y').upper()}</span>
        &nbsp;·&nbsp;
        Viewing: {start_date.strftime('%b %Y').upper()} →
        {end_date.strftime('%b %Y').upper()}
        &nbsp;·&nbsp; {len(dff):,} obs
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Row 1: Curve Explorer — one big chart, four dropdowns
# ---------------------------------------------------------------------------
section_header(
    "Curve Explorer",
    "Pick a country, chart type, tenor pair, and lookback "
    "to drill into rates structure",
)

# Tenor configuration for real-rate curves (used by the "Real rate curve" mode)
REAL_RATE_TENORS = {
    "US": [("5Y", 5,  "US_real_5y"),
           ("10Y", 10, "US_real_10y"),
           ("30Y", 30, "US_real_30y")],
    "UK": [("5Y", 5,  "UK_real_5y"),
           ("10Y", 10, "UK_real_10y"),
           ("30Y", 30, "UK_real_30y")],
    "DE": [("7Y", 7,  "DE_real_7y"),
           ("10Y", 10, "DE_real_10y"),
           ("25Y", 25, "DE_real_25y")],
    "JP": [("5Y", 5,  "JP_real_5y"),
           ("7Y", 7,  "JP_real_7y"),
           ("10Y", 10, "JP_real_10y")],
    "AU": [("5Y", 5,  "AU_real_5y"),
           ("10Y", 10, "AU_real_10y")],
    "CA": [("5Y", 5,  "CA_real_5y"),
           ("10Y", 10, "CA_real_10y"),
           ("30Y", 30, "CA_real_30y")],
}

# Tenor pairs for slope/regime mode
TENOR_PAIRS = {
    "2s10s":  ("2Y", "10Y"),
    "2s30s":  ("2Y", "30Y"),
    "5s10s":  ("5Y", "10Y"),
    "5s30s":  ("5Y", "30Y"),
    "10s30s": ("10Y", "30Y"),
}


# --- Helper: look up curve at a date --------------------------------------
def _curve_at(d, tenors):
    """Look up curve values at (or just before) date d. Skip missing tenors."""
    xs, ys, labels = [], [], []
    for label, t, key in tenors:
        s = get_series(df, key)
        if len(s) == 0:
            continue
        v = s.asof(d)
        if pd.notna(v):
            xs.append(t)
            ys.append(float(v))
            labels.append(label)
    return xs, ys, labels


# --- Big regime panel (slope mode) ----------------------------------------
def big_regime_panel(slope, regime, title, height=560):
    fig = go.Figure()
    if len(slope):
        bar_colors = regime.map(REGIME_COLORS).fillna(REGIME_COLORS["none"])
        fig.add_trace(go.Bar(
            x=slope.index, y=slope.values,
            marker=dict(color=bar_colors.values, line=dict(width=0)),
            customdata=regime.map(REGIME_LABELS).fillna("—").values,
            hovertemplate=("%{x|%Y-%m-%d}<br>Slope: %{y:.1f} bp<br>"
                           "Regime: %{customdata}<extra></extra>"),
            showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=slope.index, y=slope.values, mode="lines",
            line=dict(color=ACCENT_AMBER, width=1.4),
            hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=[slope.index[-1]], y=[slope.iloc[-1]], mode="markers",
            marker=dict(color=ACCENT_AMBER, size=8,
                        line=dict(color=BG, width=1)),
            hoverinfo="skip", showlegend=False,
        ))
    fig.add_hline(y=0, line=dict(color=TEXT_VERY_DIM, width=0.7, dash="dot"))

    last_val = slope.iloc[-1] if len(slope) else float("nan")
    last_str = f"{last_val:+.0f}bp" if pd.notna(last_val) else "—"
    last_color = ACCENT_GREEN if (pd.notna(last_val) and last_val >= 0) else ACCENT_RED
    title_html = (
        f"<span style='color:#fff;font-weight:700;letter-spacing:0.05em;font-size:14px;'>"
        f"{title.upper()}</span>  &nbsp;"
        f"<span style='color:{last_color};font-size:13px;font-weight:700'>"
        f"{last_str}</span>"
    )

    fig.update_layout(
        **DARK_LAYOUT, height=height,
        margin=dict(l=70, r=30, t=50, b=50),
        title=dict(text=title_html, font=dict(size=13),
                   x=0, xanchor="left", y=0.97),
        bargap=0.0,
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(size=11, color="#bbb"),
                     linecolor="#222")
    fig.update_yaxes(
        showgrid=True, gridcolor=GRID, zeroline=False,
        tickfont=dict(size=11, color="#bbb"), linecolor="#222",
        ticksuffix="bp",
        title=dict(text="Slope (bp)", font=dict(size=11, color="#888")),
    )
    return fig


# --- Big real-rate curve panel (curve mode) -------------------------------
def big_real_curve_panel(country, label, tenors, anchor_date, height=560):
    today = anchor_date
    week_ago = today - pd.Timedelta(days=7)
    month_ago = today - pd.Timedelta(days=30)
    fig = go.Figure()

    xs, ys, _ = _curve_at(month_ago, tenors)
    if len(xs) >= 2:
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers",
            line=dict(color="rgba(255,255,255,0.30)", width=1.5, dash="dot"),
            marker=dict(color="rgba(255,255,255,0.30)", size=7),
            name="1 month ago",
            hovertemplate="1m ago · %{x}Y: %{y:.2f}%<extra></extra>",
        ))

    xs, ys, _ = _curve_at(week_ago, tenors)
    if len(xs) >= 2:
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers",
            line=dict(color="rgba(217,152,48,0.70)", width=1.8, dash="dash"),
            marker=dict(color="rgba(217,152,48,0.70)", size=8),
            name="1 week ago",
            hovertemplate="1w ago · %{x}Y: %{y:.2f}%<extra></extra>",
        ))

    xs, ys, labels = _curve_at(today, tenors)
    if len(xs) >= 2:
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers+text",
            line=dict(color=LINE_WHITE, width=2.4),
            marker=dict(color=LINE_WHITE, size=11,
                        line=dict(color=BG, width=1.5)),
            text=[f"{y:+.2f}%" for y in ys],
            textposition="top center",
            textfont=dict(size=12, color="#fff"),
            name="Today",
            hovertemplate="Today · %{x}Y: %{y:.2f}%<extra></extra>",
        ))

    fig.add_hline(y=0, line=dict(color=TEXT_VERY_DIM, width=0.7, dash="dot"))

    title_html = (
        f"<span style='color:#fff;font-weight:700;letter-spacing:0.05em;font-size:14px;'>"
        f"{label.upper()} REAL RATE CURVE</span>"
    )

    all_y = []
    for tr in fig.data:
        if hasattr(tr, "y") and tr.y is not None:
            all_y.extend([v for v in tr.y if v is not None and pd.notna(v)])
    if all_y:
        y_min, y_max = min(all_y), max(all_y)
        y_range = y_max - y_min if y_max > y_min else 1.0
        y_pad_top = max(y_range * 0.25, 0.20)
        y_pad_bot = max(y_range * 0.15, 0.15)
        y_axis_min = y_min - y_pad_bot
        y_axis_max = y_max + y_pad_top
        # Only force zero into view if the curve actually crosses or is
        # within ~30% of its own range from zero. Otherwise zoom to where
        # the data lives — no dead vertical space below.
        if y_min < 0 < y_max:
            # Curve crosses zero; ensure both sides visible
            pass
        elif y_min > 0 and y_min < y_range * 0.3:
            # Curve hugs zero from above; show zero for context
            y_axis_min = -y_range * 0.05
    else:
        y_axis_min, y_axis_max = -1, 3

    fig.update_layout(
        **{**DARK_LAYOUT, "showlegend": True},
        height=height,
        margin=dict(l=70, r=30, t=50, b=70),
        title=dict(text=title_html, font=dict(size=13),
                   x=0, xanchor="left", y=0.97),
        legend=dict(orientation="h", yanchor="bottom", y=-0.18,
                    xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)",
                    font=dict(size=12, color="#ccc")),
    )

    if len(xs) >= 2:
        x_pad = (max(xs) - min(xs)) * 0.10
        fig.update_xaxes(
            tickvals=xs, ticktext=labels,
            range=[min(xs) - x_pad, max(xs) + x_pad],
            showgrid=False, tickfont=dict(size=13, color="#ddd"),
            linecolor="#222",
            title=None,
        )
    fig.update_yaxes(
        showgrid=True, gridcolor=GRID, zeroline=False,
        tickfont=dict(size=12, color="#bbb"), linecolor="#222",
        ticksuffix="%",
        range=[y_axis_min, y_axis_max],
        nticks=8,
        title=dict(text="Real yield (%)", font=dict(size=11, color="#888")),
    )
    return fig


# --- Dropdown row ---------------------------------------------------------
control_cols = st.columns([1, 1.3, 1, 1, 2])

with control_cols[0]:
    explorer_country = st.selectbox(
        "COUNTRY",
        options=["US", "DE", "JP", "UK", "CA", "AU"],
        index=0, key="explorer_country",
    )

with control_cols[1]:
    explorer_chart = st.selectbox(
        "CHART TYPE",
        options=["Curve slope (regime)", "Real rate curve"],
        index=0, key="explorer_chart",
    )

is_slope_mode = explorer_chart == "Curve slope (regime)"

with control_cols[2]:
    if is_slope_mode:
        explorer_pair = st.selectbox(
            "TENOR PAIR",
            options=list(TENOR_PAIRS.keys()),
            index=0, key="explorer_pair",
        )
    else:
        explorer_pair = None
        st.markdown(
            "<div style='color:#444;font-size:11px;padding-top:1.7rem;'>— n/a —</div>",
            unsafe_allow_html=True,
        )

with control_cols[3]:
    if is_slope_mode:
        explorer_lookback_choice = st.selectbox(
            "LOOKBACK",
            options=["5d", "10d", "20d", "60d", "120d"],
            index=2, key="explorer_lookback",
        )
        explorer_lookback = int(explorer_lookback_choice.rstrip("d"))
    else:
        explorer_lookback = None
        st.markdown(
            "<div style='color:#444;font-size:11px;padding-top:1.7rem;'>— n/a —</div>",
            unsafe_allow_html=True,
        )


# --- Render the chosen chart ---------------------------------------------
if is_slope_mode:
    short_tenor, long_tenor = TENOR_PAIRS[explorer_pair]
    short = get_series(dff, f"{explorer_country}_{short_tenor}")
    long_ = get_series(dff, f"{explorer_country}_{long_tenor}")

    if len(short) == 0 or len(long_) == 0:
        st.warning(
            f"No nominal yield data for {explorer_country} "
            f"{short_tenor}/{long_tenor}. Try a different pair or country."
        )
    else:
        slope, regime = classify_regime(short, long_, explorer_lookback)
        legend_chips = " &nbsp;&nbsp; ".join(
            f"<span style='display:inline-block;width:11px;height:11px;"
            f"background:{REGIME_COLORS[k]};vertical-align:middle;"
            f"margin-right:5px;'></span>"
            f"<span style='color:#bbb;font-size:10px;letter-spacing:0.05em;"
            f"text-transform:uppercase;'>{REGIME_LABELS[k]}</span>"
            for k in ["bull_steepener", "bear_steepener", "steepener_twist",
                      "bull_flattener", "bear_flattener", "flattener_twist"]
        )
        st.markdown(
            f"<div style='padding:0.5rem 0 0.25rem;'>{legend_chips}</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            big_regime_panel(
                slope, regime,
                f"{explorer_country} {explorer_pair} "
                f"(regime vs {explorer_lookback}d ago)",
            ),
            use_container_width=True,
            key="explorer_slope",
            config={"displayModeBar": False},
        )
else:
    anchor = dff.index.max() if len(dff) else df.index.max()
    tenors = REAL_RATE_TENORS[explorer_country]
    st.plotly_chart(
        big_real_curve_panel(
            explorer_country, explorer_country, tenors, anchor,
        ),
        use_container_width=True,
        key="explorer_curve",
        config={"displayModeBar": False},
    )

# ---------------------------------------------------------------------------
# Row 2: Inflation Expectations Explorer
# ---------------------------------------------------------------------------
section_header(
    "Inflation Expectations",
    "Pick a measure to drill into · TIPS breakevens · "
    "ZC inflation swaps · 5Y5Y forward",
)

# Tenor sets for the curve modes
INFL_BE_TENORS = [
    ("2Y", 2, "BE_2Y"), ("5Y", 5, "BE_5Y"),
    ("10Y", 10, "BE_10Y"), ("20Y", 20, "BE_20Y"),
    ("30Y", 30, "BE_30Y"),
]
INFL_ZCIS_TENORS = [
    ("1Y", 1, "ZCIS_1Y"), ("2Y", 2, "ZCIS_2Y"), ("3Y", 3, "ZCIS_3Y"),
    ("4Y", 4, "ZCIS_4Y"), ("5Y", 5, "ZCIS_5Y"), ("7Y", 7, "ZCIS_7Y"),
    ("10Y", 10, "ZCIS_10Y"), ("20Y", 20, "ZCIS_20Y"),
    ("30Y", 30, "ZCIS_30Y"),
]

infl_choice = st.selectbox(
    "MEASURE",
    options=[
        "TIPS breakeven curve",
        "ZC inflation swap curve",
        "5Y5Y forward inflation swap",
    ],
    index=0,
    key="infl_choice",
)

if infl_choice == "TIPS breakeven curve":
    anchor_infl = dff.index.max() if len(dff) else df.index.max()
    fig = big_real_curve_panel(
        "US", "US TIPS breakeven", INFL_BE_TENORS, anchor_infl,
    )
    # Override title since big_real_curve_panel hardcodes "REAL RATE CURVE"
    fig.update_layout(title=dict(
        text="<span style='color:#fff;font-weight:700;letter-spacing:0.05em;"
             "font-size:14px;'>US TIPS BREAKEVEN CURVE</span>",
        font=dict(size=13), x=0, xanchor="left", y=0.97,
    ))
    st.plotly_chart(fig, use_container_width=True, key="infl_be",
                    config={"displayModeBar": False})

elif infl_choice == "ZC inflation swap curve":
    anchor_infl = dff.index.max() if len(dff) else df.index.max()
    fig = big_real_curve_panel(
        "US", "USD ZC inflation swap", INFL_ZCIS_TENORS, anchor_infl,
    )
    fig.update_layout(title=dict(
        text="<span style='color:#fff;font-weight:700;letter-spacing:0.05em;"
             "font-size:14px;'>USD ZC INFLATION SWAP CURVE</span>",
        font=dict(size=13), x=0, xanchor="left", y=0.97,
    ))
    st.plotly_chart(fig, use_container_width=True, key="infl_zcis",
                    config={"displayModeBar": False})

else:  # 5Y5Y forward
    s = get_series(dff, "INFL_5Y5Y")
    fig = go.Figure()
    if len(s):
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, mode="lines",
            line=dict(color=LINE_WHITE, width=1.4),
            fill="tozeroy", fillcolor="rgba(255,255,255,0.05)",
            hovertemplate="%{x|%Y-%m-%d}: %{y:.2f}%<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[s.index[-1]], y=[s.iloc[-1]], mode="markers",
            marker=dict(color=LINE_WHITE, size=8,
                        line=dict(color=BG, width=1)),
            hoverinfo="skip", showlegend=False,
        ))
        # Reference line at 2% (Fed target)
        fig.add_hline(y=2.0, line=dict(color=ACCENT_AMBER, width=0.8,
                                       dash="dash"),
                      annotation_text="Fed target 2%",
                      annotation_position="right",
                      annotation_font=dict(size=10, color=ACCENT_AMBER))

    last_val = s.iloc[-1] if len(s) else float("nan")
    last_str = f"{last_val:+.2f}%" if pd.notna(last_val) else "—"
    fig.update_layout(
        **DARK_LAYOUT, height=520,
        margin=dict(l=70, r=30, t=50, b=40),
        title=dict(
            text=(f"<span style='color:#fff;font-weight:700;letter-spacing:0.05em;"
                  f"font-size:14px;'>USD 5Y5Y FORWARD INFLATION SWAP</span>  "
                  f"&nbsp;<span style='color:#aaa;font-size:12px;'>{last_str}</span>"),
            font=dict(size=13), x=0, xanchor="left", y=0.97,
        ),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(size=11, color="#bbb"),
                     linecolor="#222")
    fig.update_yaxes(
        showgrid=True, gridcolor=GRID, zeroline=False,
        tickfont=dict(size=11, color="#bbb"), linecolor="#222",
        ticksuffix="%",
        title=dict(text="5Y5Y forward (%)", font=dict(size=11, color="#888")),
    )
    st.plotly_chart(fig, use_container_width=True, key="infl_5y5y",
                    config={"displayModeBar": False})

# ---------------------------------------------------------------------------
# Row 3: Money-market spreads — OFR-style with label boxes
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div style="padding:0.6rem 0 0.5rem;margin-top:1rem;
                border-top:1px solid #1a1a1a;border-bottom:1px solid #1a1a1a;">
      <div style="font-size:18px;font-weight:700;letter-spacing:0.06em;
                  color:#fff;text-transform:uppercase;">
        Money Market Spreads Monitor
      </div>
      <div style="font-size:10px;color:#888;letter-spacing:0.1em;
                  text-transform:uppercase;margin-top:2px;">
        An overview of key money market spreads and how to interpret them
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

spreads_def = [
    (
        "GCF − TPR",
        "DEALER BALANCE<br>SHEET CAPACITY",
        "The spread between interdealer and triparty repo rates, "
        "a proxy for funding demand and dealer balance sheet capacity.",
        get_series(dff, "GCF") - get_series(dff, "TPR"),
        "INFLEXIBLE BALANCE SHEETS ↑",
        "FLEXIBLE BALANCE SHEETS ↓",
    ),
    (
        "TGCR − RRP",
        "PRIVATE REPO<br>DEMAND",
        "The spread between private repo &amp; Fed RRP rates, "
        "which measures demand for cash vs. collateral.",
        get_series(dff, "TGCR") - get_series(dff, "RRP"),
        "EXCESS COLLATERAL ↑",
        "EXCESS CASH ↓",
    ),
    (
        "SOFR − IORB",
        "BANK REPOS",
        "A positive spread indicates banks are lending reserves "
        "in repo on a consistent basis, reducing liquidity elsewhere.",
        get_series(dff, "SOFR") - get_series(dff, "IORB"),
        "ABOVE ZERO, BANKS DEPLOY RESERVES<br>CONSISTENTLY INTO REPO MARKETS ↑",
        None,
    ),
    (
        "EFFR − IORB",
        "RESERVE<br>DEMAND",
        "A positive spread suggests scarce reserves on a historical basis.",
        get_series(dff, "EFFR") - get_series(dff, "IORB"),
        "SCARCITY ↑",
        "ABUNDANCE ↓",
    ),
    (
        "SOFR − EFFR",
        "FHLB REPO<br>DEMAND",
        "The spread suggests where Federal Home Loan Banks "
        "might invest more of their liquidity portfolios.",
        get_series(dff, "SOFR") - get_series(dff, "EFFR"),
        "FHLBs DEPLOY MORE<br>CASH INTO REPOS ↑",
        None,
    ),
]

for name, category, explainer, s, top_note, bottom_note in spreads_def:
    last_val = s.dropna().iloc[-1] if len(s.dropna()) else float("nan")
    last_color = ACCENT_RED if (pd.notna(last_val) and last_val < 0) else ACCENT_GREEN
    last_str = f"{last_val:+.3f}" if pd.notna(last_val) else "—"

    parts = name.split(" − ")
    left_ticker = parts[0]
    right_ticker = parts[1] if len(parts) > 1 else ""

    label_col, chart_col = st.columns([1, 4], gap="small")

    with label_col:
        st.markdown(
            f"""
            <div style="background:{BG};padding:1rem 0.9rem;
                        height:160px;color:#fff;
                        display:flex;flex-direction:column;
                        font-family:Inter,sans-serif;">
              <div style="font-size:13px;font-weight:700;
                          letter-spacing:0.06em;line-height:1.15;
                          margin-bottom:10px;color:#fff;">
                {category}
              </div>
              <div style="background:#1a1a1a;padding:5px 10px;
                          border:1px solid #2a2a2a;display:inline-block;
                          width:fit-content;margin-bottom:8px;">
                <span style="color:{ACCENT_GREEN};font-weight:700;font-size:13px;
                             letter-spacing:0.05em;">{left_ticker}</span>
                <span style="color:#888;font-weight:700;font-size:13px;"> − </span>
                <span style="color:{ACCENT_RED};font-weight:700;font-size:13px;
                             letter-spacing:0.05em;">{right_ticker}</span>
                <div style="font-size:8px;color:#666;letter-spacing:0.18em;
                            margin-top:1px;text-align:center;">SPREAD</div>
              </div>
              <div style="font-size:9px;color:#aaa;line-height:1.45;
                          letter-spacing:0.04em;text-transform:uppercase;">
                {explainer}
              </div>
              <div style="margin-top:auto;font-size:9px;color:#666;
                          letter-spacing:0.05em;text-transform:uppercase;
                          padding-top:6px;">
                Latest: <span style="color:{last_color};font-weight:700;
                                     font-size:11px;letter-spacing:0.02em;">
                  {last_str}
                </span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with chart_col:
        st.plotly_chart(
            ofr_chart(s, top_note, bottom_note),
            use_container_width=True,
            key=f"mm_{name.replace(' ', '_').replace('−', '_')}",
            config={"displayModeBar": False},
        )

# --- Overnight rates composite (extends MM section) ----------------------
st.markdown(
    """
    <div style="padding:0.4rem 0 0.25rem;margin-top:0.5rem;">
      <div style="font-size:13px;font-weight:700;letter-spacing:0.06em;
                  color:#ccc;text-transform:uppercase;">
        Overnight rates layered
      </div>
      <div style="font-size:10px;color:#888;letter-spacing:0.08em;
                  text-transform:uppercase;margin-top:2px;">
        Six US dollar overnight rates plotted together · %
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

ovr_fig = go.Figure()
ovr_series = [
    ("Fed funds target (lower)", "RRP",     "#d062ff"),  # purple
    ("IORB",                     "IORB",    "#9bd62a"),  # lime green
    ("SOFR",                     "SOFR",    "#ffd200"),  # yellow
    ("TGCR",                     "TGCR",    "#ff8a3d"),  # orange
    ("USD repo GC ON",           "USRG_1T", "#5dd6e0"),  # cyan
    ("RRP award rate",           "TOMO_TCSO", "#ffffff"),  # white
]
for label, key, color in ovr_series:
    s = get_series(dff, key)
    if len(s):
        ovr_fig.add_trace(go.Scatter(
            x=s.index, y=s.values, mode="lines",
            line=dict(color=color, width=1.2),
            name=label,
            hovertemplate=f"<b>{label}</b><br>"
                          f"%{{x|%Y-%m-%d}}: %{{y:.3f}}%<extra></extra>",
        ))

ovr_fig.update_layout(
    **{**DARK_LAYOUT, "showlegend": True},
    height=380,
    margin=dict(l=60, r=20, t=20, b=30),
    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                xanchor="left", x=0,
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=10, color="#ccc")),
)
ovr_fig.update_xaxes(showgrid=False, tickfont=dict(size=10, color=TEXT_DIM),
                     linecolor="#222")
ovr_fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                     tickfont=dict(size=10, color=TEXT_DIM), linecolor="#222",
                     ticksuffix="%")
st.plotly_chart(ovr_fig, use_container_width=True, key="overnight_rates",
                config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# Row 3.5: Liquidity (new section between MM and XCCY)
# ---------------------------------------------------------------------------
section_header(
    "Liquidity",
    "Fed reserve balances · Financial Conditions Index composite",
)

liq_left, liq_right = st.columns(2, gap="medium")

with liq_left:
    # Fed reserves time-series with weekly change histogram below
    s = get_series(dff, "FED_RESERVES").dropna()
    weekly_change = s.diff()  # daily change, since data is daily; rename for clarity

    res_fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.72, 0.28], vertical_spacing=0.04,
    )
    if len(s):
        # Convert from $millions to $trillions for readability
        s_t = s / 1_000_000.0
        res_fig.add_trace(
            go.Scatter(
                x=s_t.index, y=s_t.values, mode="lines",
                line=dict(color="#9bd62a", width=1.2),
                fill="tozeroy", fillcolor="rgba(155,214,42,0.10)",
                hovertemplate="%{x|%Y-%m-%d}: $%{y:.2f}T<extra></extra>",
                showlegend=False,
            ),
            row=1, col=1,
        )
        res_fig.add_trace(
            go.Scatter(
                x=[s_t.index[-1]], y=[s_t.iloc[-1]], mode="markers",
                marker=dict(color="#9bd62a", size=7,
                            line=dict(color=BG, width=1)),
                hoverinfo="skip", showlegend=False,
            ),
            row=1, col=1,
        )
        # Weekly change histogram (in $bn for readability)
        chg_bn = weekly_change.dropna() / 1000.0
        bar_colors = ["#67c757" if v >= 0 else "#e64545"
                      for v in chg_bn.values]
        res_fig.add_trace(
            go.Bar(
                x=chg_bn.index, y=chg_bn.values,
                marker=dict(color=bar_colors, line=dict(width=0)),
                hovertemplate="%{x|%Y-%m-%d}: $%{y:+.0f}B<extra></extra>",
                showlegend=False,
            ),
            row=2, col=1,
        )
        res_fig.add_hline(y=0, line=dict(color=TEXT_VERY_DIM, width=0.5,
                                         dash="dot"), row=2, col=1)

    last_val = (s.iloc[-1] / 1_000_000.0) if len(s) else float("nan")
    last_str = f"${last_val:.2f}T" if pd.notna(last_val) else "—"
    res_fig.update_layout(
        **DARK_LAYOUT, height=460,
        margin=dict(l=55, r=20, t=40, b=30),
        title=dict(
            text=(f"<span style='color:#fff;font-weight:700;letter-spacing:0.05em;"
                  f"font-size:13px;'>FED RESERVE BALANCES</span>  "
                  f"&nbsp;<span style='color:#9bd62a;font-size:11px;font-weight:700'>"
                  f"{last_str}</span>"),
            font=dict(size=12), x=0, xanchor="left", y=0.97,
        ),
        bargap=0.0,
    )
    res_fig.update_xaxes(showgrid=False, linecolor="#222",
                         tickfont=dict(size=9, color=TEXT_DIM))
    res_fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                         tickfont=dict(size=9, color=TEXT_DIM), linecolor="#222",
                         ticksuffix="T", row=1, col=1,
                         title=dict(text="Reserves ($T)",
                                    font=dict(size=10, color="#888")))
    res_fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                         tickfont=dict(size=9, color=TEXT_DIM), linecolor="#222",
                         ticksuffix="B", row=2, col=1,
                         title=dict(text="Δ ($B)",
                                    font=dict(size=10, color="#888")))
    st.plotly_chart(res_fig, use_container_width=True, key="fed_reserves",
                    config={"displayModeBar": False})

with liq_right:
    # FCI composite: Bloomberg + Chicago Fed NFCI
    bbg_fci = get_series(dff, "FCI_BBG").dropna()
    nfci = get_series(dff, "FCI_NFCI").dropna()

    fci_fig = make_subplots(specs=[[{"secondary_y": True}]])
    if len(bbg_fci):
        fci_fig.add_trace(
            go.Scatter(
                x=bbg_fci.index, y=bbg_fci.values, mode="lines",
                line=dict(color=ACCENT_CYAN, width=1.4),
                name="Bloomberg US FCI",
                hovertemplate="BBG FCI: %{y:.3f}<extra></extra>",
            ),
            secondary_y=False,
        )
    if len(nfci):
        fci_fig.add_trace(
            go.Scatter(
                x=nfci.index, y=nfci.values, mode="lines",
                line=dict(color=ACCENT_AMBER, width=1.4),
                name="Chicago Fed NFCI",
                hovertemplate="NFCI: %{y:.3f}<extra></extra>",
            ),
            secondary_y=True,
        )
    fci_fig.add_hline(y=0, line=dict(color=TEXT_VERY_DIM, width=0.5,
                                     dash="dot"))

    bbg_last = bbg_fci.iloc[-1] if len(bbg_fci) else float("nan")
    nfci_last = nfci.iloc[-1] if len(nfci) else float("nan")
    fci_fig.update_layout(
        **{**DARK_LAYOUT, "showlegend": True},
        height=460,
        margin=dict(l=55, r=55, t=40, b=30),
        title=dict(
            text=(f"<span style='color:#fff;font-weight:700;letter-spacing:0.05em;"
                  f"font-size:13px;'>FINANCIAL CONDITIONS INDEX</span>  "
                  f"&nbsp;<span style='color:{ACCENT_CYAN};font-size:11px;font-weight:700'>"
                  f"BBG {bbg_last:+.2f}</span>  "
                  f"<span style='color:{ACCENT_AMBER};font-size:11px;font-weight:700'>"
                  f"NFCI {nfci_last:+.2f}</span>"),
            font=dict(size=12), x=0, xanchor="left", y=0.97,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.18,
                    xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)",
                    font=dict(size=10, color="#ccc")),
    )
    fci_fig.update_xaxes(showgrid=False, linecolor="#222",
                         tickfont=dict(size=10, color=TEXT_DIM))
    fci_fig.update_yaxes(title_text="BBG FCI (>100 = looser)",
                         secondary_y=False, showgrid=True, gridcolor=GRID,
                         zeroline=False, linecolor="#222",
                         tickfont=dict(size=10, color=TEXT_DIM),
                         title_font=dict(size=10, color="#888"))
    fci_fig.update_yaxes(title_text="NFCI (inverted, up = looser)",
                         secondary_y=True, showgrid=False, linecolor="#222",
                         autorange="reversed",
                         tickfont=dict(size=10, color=TEXT_DIM),
                         title_font=dict(size=10, color="#888"))
    st.plotly_chart(fci_fig, use_container_width=True, key="fci_composite",
                    config={"displayModeBar": False})

# ---------------------------------------------------------------------------
# Row 4: XCCY basis swaps — 3M (top row) and 12M (bottom row)
# ---------------------------------------------------------------------------
section_header("Cross-Currency Basis Swaps",
               "Top: 3M · Bottom: 12M · negative = USD funding premium · bp")

xccy_list = [("EUR", "EUR"), ("JPY", "JPY"), ("AUD", "AUD"),
             ("GBP", "GBP"), ("CAD", "CAD")]

# 3M row
cols = st.columns(5)
for col, (ccy, label) in zip(cols, xccy_list):
    with col:
        s = get_series(dff, f"XCCY_{ccy}")
        if len(s):
            st.plotly_chart(
                mini_dark(s, f"{label}/USD 3M basis", color=ACCENT_AMBER),
                use_container_width=True, key=f"xccy3m_{ccy}",
                config={"displayModeBar": False},
            )

# 12M row
cols = st.columns(5)
for col, (ccy, label) in zip(cols, xccy_list):
    with col:
        s = get_series(dff, f"XCCY12_{ccy}")
        if len(s):
            st.plotly_chart(
                mini_dark(s, f"{label}/USD 12M basis", color=ACCENT_CYAN),
                use_container_width=True, key=f"xccy12m_{ccy}",
                config={"displayModeBar": False},
            )

# ---------------------------------------------------------------------------
# Row 5: Credit
# ---------------------------------------------------------------------------
section_header("Credit", "IG/HY OAS · Bank CDS · EMBI sovereign · basis points")

credit_fig = make_subplots(
    rows=1, cols=1, specs=[[{"secondary_y": True}]],
)

# Convert OAS (quoted in %) to bp
ig = get_series(dff, "IG_OAS") * 100
hy = get_series(dff, "HY_OAS") * 100
embi = get_series(dff, "EMBI")
bofa = get_series(dff, "CDS_BOFA")
jpm = get_series(dff, "CDS_JPM")
db_sub = get_series(dff, "CDS_DB_SUB")

credit_fig.add_trace(
    go.Scatter(x=ig.index, y=ig.values, name="IG OAS",
               line=dict(color=ACCENT_CYAN, width=1.5),
               hovertemplate="IG OAS: %{y:.0f}bp<extra></extra>"),
    secondary_y=False,
)
credit_fig.add_trace(
    go.Scatter(x=embi.index, y=embi.values, name="EMBI sovereign",
               line=dict(color=ACCENT_GREEN, width=1.3),
               hovertemplate="EMBI: %{y:.0f}bp<extra></extra>"),
    secondary_y=False,
)
credit_fig.add_trace(
    go.Scatter(x=bofa.index, y=bofa.values, name="BofA 5Y CDS",
               line=dict(color=TEXT_DIM, width=1),
               hovertemplate="BofA CDS: %{y:.0f}bp<extra></extra>"),
    secondary_y=False,
)
credit_fig.add_trace(
    go.Scatter(x=jpm.index, y=jpm.values, name="JPM 5Y CDS",
               line=dict(color=ACCENT_PURPLE, width=1),
               hovertemplate="JPM CDS: %{y:.0f}bp<extra></extra>"),
    secondary_y=False,
)
credit_fig.add_trace(
    go.Scatter(x=hy.index, y=hy.values, name="HY OAS",
               line=dict(color=ACCENT_RED, width=1.7),
               hovertemplate="HY OAS: %{y:.0f}bp<extra></extra>"),
    secondary_y=True,
)
credit_fig.add_trace(
    go.Scatter(x=db_sub.index, y=db_sub.values, name="DB sub CDS",
               line=dict(color=ACCENT_AMBER, width=1),
               hovertemplate="DB sub: %{y:.0f}bp<extra></extra>"),
    secondary_y=True,
)

credit_fig.update_layout(
    **{**DARK_LAYOUT, "showlegend": True},
    height=440,
    margin=dict(l=50, r=50, t=20, b=30),
    legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02,
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=10, color="#ccc")),
)
credit_fig.update_xaxes(showgrid=False, linecolor="#222",
                        tickfont=dict(color=TEXT_DIM, size=9))
credit_fig.update_yaxes(title_text="IG / EMBI / Bank CDS (bp)", secondary_y=False,
                        showgrid=True, gridcolor=GRID, linecolor="#222",
                        title_font=dict(size=10, color="#aaa"),
                        tickfont=dict(color=TEXT_DIM, size=9))
credit_fig.update_yaxes(title_text="HY / DB sub (bp)", secondary_y=True,
                        showgrid=False, linecolor="#222",
                        title_font=dict(size=10, color="#aaa"),
                        tickfont=dict(color=TEXT_DIM, size=9))

st.plotly_chart(credit_fig, use_container_width=True, key="credit_panel",
                config={"displayModeBar": False})

# --- Credit index explorer (CDX / iTraxx) --------------------------------
st.markdown(
    """
    <div style="padding:0.6rem 0 0.25rem;margin-top:0.75rem;">
      <div style="font-size:13px;font-weight:700;letter-spacing:0.06em;
                  color:#ccc;text-transform:uppercase;">
        Credit Index Explorer
      </div>
      <div style="font-size:10px;color:#888;letter-spacing:0.08em;
                  text-transform:uppercase;margin-top:2px;">
        Pick any CDX or iTraxx series · daily change histogram below
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

CREDIT_INDICES = {
    "CDX NA IG (price)":           ("CDX_IG",       "price"),
    "CDX NA HY (price)":           ("CDX_HY",       "price"),
    "CDX EM (spread, bp)":         ("CDX_EM",       "spread"),
    "iTraxx Europe Main (bp)":     ("ITRX_EUROPE",  "spread"),
    "iTraxx Crossover (bp)":       ("ITRX_XOVER",   "spread"),
    "iTraxx Sr Financial (bp)":    ("ITRX_SR_FIN",  "spread"),
    "iTraxx Sub Financial (bp)":   ("ITRX_SUB_FIN", "spread"),
    "iTraxx Japan (bp)":           ("ITRX_JAPAN",   "spread"),
    "iTraxx Asia ex-Japan (bp)":   ("ITRX_ASIA_XJ", "spread"),
    "iTraxx Australia (bp)":       ("ITRX_AUS",     "spread"),
}

credit_choice = st.selectbox(
    "INDEX",
    options=list(CREDIT_INDICES.keys()),
    index=0,
    key="credit_idx_choice",
)
credit_key, credit_unit = CREDIT_INDICES[credit_choice]
cs = get_series(dff, credit_key).dropna()

cidx_fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.72, 0.28], vertical_spacing=0.04,
)

if len(cs):
    line_color = LINE_WHITE if credit_unit == "price" else ACCENT_CYAN
    cidx_fig.add_trace(
        go.Scatter(
            x=cs.index, y=cs.values, mode="lines",
            line=dict(color=line_color, width=1.3),
            fill="tozeroy" if credit_unit == "spread" else None,
            fillcolor=f"rgba(79,168,184,0.08)" if credit_unit == "spread" else None,
            hovertemplate=(
                ("%{x|%Y-%m-%d}: $%{y:.2f}<extra></extra>"
                 if credit_unit == "price"
                 else "%{x|%Y-%m-%d}: %{y:.1f}bp<extra></extra>")
            ),
            showlegend=False,
        ),
        row=1, col=1,
    )
    cidx_fig.add_trace(
        go.Scatter(
            x=[cs.index[-1]], y=[cs.iloc[-1]], mode="markers",
            marker=dict(color=line_color, size=7,
                        line=dict(color=BG, width=1)),
            hoverinfo="skip", showlegend=False,
        ),
        row=1, col=1,
    )
    # Daily change histogram
    chg = cs.diff().dropna()
    bar_colors = ["#67c757" if v >= 0 else "#e64545" for v in chg.values]
    cidx_fig.add_trace(
        go.Bar(
            x=chg.index, y=chg.values,
            marker=dict(color=bar_colors, line=dict(width=0)),
            hovertemplate=(
                ("%{x|%Y-%m-%d}: $%{y:+.2f}<extra></extra>"
                 if credit_unit == "price"
                 else "%{x|%Y-%m-%d}: %{y:+.1f}bp<extra></extra>")
            ),
            showlegend=False,
        ),
        row=2, col=1,
    )
    cidx_fig.add_hline(y=0, line=dict(color=TEXT_VERY_DIM, width=0.5,
                                      dash="dot"), row=2, col=1)

last_val = cs.iloc[-1] if len(cs) else float("nan")
last_str = (f"${last_val:.2f}" if credit_unit == "price"
            else f"{last_val:.1f}bp") if pd.notna(last_val) else "—"

cidx_fig.update_layout(
    **DARK_LAYOUT, height=520,
    margin=dict(l=55, r=20, t=45, b=30),
    title=dict(
        text=(f"<span style='color:#fff;font-weight:700;letter-spacing:0.05em;"
              f"font-size:14px;'>{credit_choice.upper()}</span>  "
              f"&nbsp;<span style='color:#aaa;font-size:11px;'>{last_str}</span>"),
        font=dict(size=12), x=0, xanchor="left", y=0.97,
    ),
    bargap=0.0,
)
cidx_fig.update_xaxes(showgrid=False, linecolor="#222",
                      tickfont=dict(size=10, color=TEXT_DIM))
y1_suffix = "" if credit_unit == "price" else "bp"
y1_title = "Price ($)" if credit_unit == "price" else "Spread (bp)"
cidx_fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                      tickfont=dict(size=10, color=TEXT_DIM), linecolor="#222",
                      ticksuffix=y1_suffix, row=1, col=1,
                      title=dict(text=y1_title, font=dict(size=10, color="#888")))
cidx_fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                      tickfont=dict(size=10, color=TEXT_DIM), linecolor="#222",
                      ticksuffix=y1_suffix, row=2, col=1,
                      title=dict(text="1d Δ", font=dict(size=10, color="#888")))
st.plotly_chart(cidx_fig, use_container_width=True, key="credit_idx_explorer",
                config={"displayModeBar": False})


# --- Mortgage panel: 30Y mortgage vs 10Y Treasury ------------------------
st.markdown(
    """
    <div style="padding:0.6rem 0 0.25rem;margin-top:0.75rem;">
      <div style="font-size:13px;font-weight:700;letter-spacing:0.06em;
                  color:#ccc;text-transform:uppercase;">
        Mortgage rate vs. 10Y Treasury
      </div>
      <div style="font-size:10px;color:#888;letter-spacing:0.08em;
                  text-transform:uppercase;margin-top:2px;">
        30Y fixed mortgage vs. UST 10Y · spread histogram below · bp
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

mtg = get_series(dff, "MTG_30Y").dropna()
ust10 = get_series(dff, "US_10Y").dropna()

mtg_fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.65, 0.35], vertical_spacing=0.04,
)

if len(mtg) and len(ust10):
    mtg_fig.add_trace(
        go.Scatter(
            x=mtg.index, y=mtg.values, mode="lines",
            line=dict(color=ACCENT_AMBER, width=1.3),
            name="30Y mortgage",
            hovertemplate="30Y mortgage: %{y:.2f}%<extra></extra>",
        ),
        row=1, col=1,
    )
    mtg_fig.add_trace(
        go.Scatter(
            x=ust10.index, y=ust10.values, mode="lines",
            line=dict(color=LINE_WHITE, width=1.3),
            name="UST 10Y",
            hovertemplate="UST 10Y: %{y:.2f}%<extra></extra>",
        ),
        row=1, col=1,
    )
    # Spread = mortgage - UST 10Y, in bp (positive = mortgage premium)
    aligned = pd.concat([mtg, ust10], axis=1, join="inner").dropna()
    aligned.columns = ["mtg", "ust"]
    spread_bp = (aligned["mtg"] - aligned["ust"]) * 100
    mtg_fig.add_trace(
        go.Scatter(
            x=spread_bp.index, y=spread_bp.values, mode="lines",
            line=dict(color="#e64545", width=1.1),
            fill="tozeroy", fillcolor="rgba(230,69,69,0.18)",
            name="Mortgage – UST10Y spread",
            hovertemplate="Spread: %{y:+.0f}bp<extra></extra>",
            showlegend=False,
        ),
        row=2, col=1,
    )
    # Reference: long-run avg of spread
    avg_spread = float(spread_bp.mean())
    mtg_fig.add_hline(y=avg_spread, line=dict(color=TEXT_VERY_DIM, width=0.5,
                                              dash="dash"),
                      annotation_text=f"avg {avg_spread:.0f}bp",
                      annotation_position="right",
                      annotation_font=dict(size=9, color="#888"),
                      row=2, col=1)

mtg_last = mtg.iloc[-1] if len(mtg) else float("nan")
ust_last = ust10.iloc[-1] if len(ust10) else float("nan")
spread_last = (mtg_last - ust_last) * 100 if (pd.notna(mtg_last) and pd.notna(ust_last)) else float("nan")

mtg_fig.update_layout(
    **{**DARK_LAYOUT, "showlegend": True},
    height=520,
    margin=dict(l=55, r=20, t=45, b=30),
    title=dict(
        text=(f"<span style='color:#fff;font-weight:700;letter-spacing:0.05em;"
              f"font-size:14px;'>30Y MORTGAGE vs UST 10Y</span>  "
              f"&nbsp;<span style='color:{ACCENT_AMBER};font-size:11px;font-weight:700'>"
              f"Mtg {mtg_last:.2f}%</span>  "
              f"<span style='color:#fff;font-size:11px;font-weight:700'>"
              f"UST {ust_last:.2f}%</span>  "
              f"<span style='color:#e64545;font-size:11px;font-weight:700'>"
              f"Spread {spread_last:+.0f}bp</span>"),
        font=dict(size=12), x=0, xanchor="left", y=0.97,
    ),
    legend=dict(orientation="h", yanchor="bottom", y=-0.18,
                xanchor="left", x=0,
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=10, color="#ccc")),
)
mtg_fig.update_xaxes(showgrid=False, linecolor="#222",
                     tickfont=dict(size=10, color=TEXT_DIM))
mtg_fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                     tickfont=dict(size=10, color=TEXT_DIM), linecolor="#222",
                     ticksuffix="%", row=1, col=1,
                     title=dict(text="Yield (%)",
                                font=dict(size=10, color="#888")))
mtg_fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                     tickfont=dict(size=10, color=TEXT_DIM), linecolor="#222",
                     ticksuffix="bp", row=2, col=1,
                     title=dict(text="Spread (bp)",
                                font=dict(size=10, color="#888")))
st.plotly_chart(mtg_fig, use_container_width=True, key="mortgage_panel",
                config={"displayModeBar": False})

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div style="margin-top:1rem;padding-top:0.75rem;
                border-top:1px solid #1a1a1a;color:#666;
                font-size:9px;letter-spacing:0.1em;text-transform:uppercase;">
      Source: DATA.xlsx · {len(df):,} daily observations ·
      {len(df.columns)} Bloomberg series · spreads computed from raw rates
    </div>
    """,
    unsafe_allow_html=True,
)
