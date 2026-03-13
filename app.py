"""
app.py - Guild Statistics Tracker for Forge of Empires
"""

import streamlit as st
import pandas as pd
import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from modules.importer import (
    import_gbg, import_qi, import_members,
    get_gbg_df, get_qi_df, get_members_df, get_member_snapshots,
    get_all_seasons, delete_season,
)
from modules.gbg_analysis import (
    get_leaderboard as gbg_leaderboard,
    get_guild_totals_by_season as gbg_totals,
    get_top_contributors as gbg_top,
    get_cumulative_fights,
)
from modules.qi_analysis import (
    get_leaderboard as qi_leaderboard,
    get_guild_totals_by_season as qi_totals,
    get_top_contributors as qi_top,
    get_cumulative_progress,
)
from modules.player_profile import (
    get_all_players, get_player_profile, get_most_consistent_players,
    get_latest_member_stats, get_all_season_winners,
    get_hall_of_fame, get_guild_health, get_active_streak, get_newcomers, get_most_improved,
    get_points_leaderboard, get_goods_leaderboard, get_battles_leaderboard,
)
from modules.comparisons import (
    gbg_season_comparison, qi_season_comparison,
    detect_player_status, most_improved_gbg, most_improved_qi, sort_seasons,
)
from modules.charts import (
    gbg_fights_leaderboard, gbg_total_contribution_chart, gbg_guild_trend, gbg_player_trend,
    qi_progress_leaderboard, qi_guild_trend, qi_player_trend, comparison_waterfall,
    points_trend_chart, era_distribution_chart, activity_heatmap,
)

# ── Constants ──────────────────────────────────────────────────────────────
AVATAR_DIR  = Path("assets/avatars")
ICON_DIR    = Path("assets/icons")
IMPORT_PASS = os.environ.get("IMPORT_PASSWORD", "guild2024")  # set via Streamlit secrets or env


# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FoE Guild Tracker",
    page_icon="🏴",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Icon helpers ───────────────────────────────────────────────────────────
def _img_to_b64(path: Path) -> str:
    if path.exists():
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def icon_html(filename: str, size: int = 22) -> str:
    b64 = _img_to_b64(ICON_DIR / filename)
    if b64:
        return f'<img src="data:image/png;base64,{b64}" width="{size}" height="{size}" style="vertical-align:middle;margin-right:6px;">'
    return ""

def gbg_icon(size=22):  return icon_html("gbg_icon.png", size)
def qi_icon(size=22):   return icon_html("qi_icon.png", size)
def flag_icon(size=22): return icon_html("flag_icon.png", size)


# ── Avatar helper ──────────────────────────────────────────────────────────
def get_avatar_html(player_name: str, size: int = 56) -> str:
    """Return <img> if player_name.jpg exists, else styled initials div. Rectangular shape."""
    safe_name = player_name.strip()
    jpg_path = AVATAR_DIR / f"{safe_name}.jpg"
    png_path = AVATAR_DIR / f"{safe_name}.png"

    # Rectangular dimensions — slightly wider than tall, like a game card
    w = int(size * 1.0)
    h = int(size * 1.2)

    for path in [jpg_path, png_path]:
        if path.exists():
            ext = "jpeg" if path.suffix == ".jpg" else "png"
            b64 = _img_to_b64(path)
            return (f'<img src="data:image/{ext};base64,{b64}" '
                    f'width="{w}" height="{h}" '
                    f'style="border-radius:6px;object-fit:cover;object-position:top;">')

    initials = "".join(w[0].upper() for w in safe_name.split()[:2]) or "?"
    return (f'<div style="width:{w}px;height:{h}px;border-radius:6px;'
            f'background:linear-gradient(160deg,#4A90D9 0%,#9B59B6 100%);'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:{int(size*0.32)}px;font-weight:700;color:white;">'
            f'{initials}</div>')


# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Main area: white background, dark text ── */
[data-testid="stAppViewContainer"] > .main { background: #FFFFFF; }
[data-testid="stAppViewContainer"] { background: #FFFFFF; }

/* ── Sidebar: always dark regardless of theme ── */
[data-testid="stSidebar"] {
    background: #12151E !important;
    border-right: 1px solid #2A2D3A;
}
[data-testid="stSidebar"] * { color: #E8E8E8 !important; }
[data-testid="stSidebar"] .stRadio label { color: #E8E8E8 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSelectbox div[data-baseweb] { color: #E8E8E8 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #1A1D27 !important;
    border-color: #2A2D3A !important;
    color: #E8E8E8 !important;
}
[data-testid="stSidebar"] hr { border-color: #2A2D3A !important; }

/* ── Section titles readable on white ── */
.section-title {
    color:#4A90D9; font-size:1.05rem; font-weight:700;
    border-left:3px solid #4A90D9; padding-left:10px; margin:18px 0 10px;
}
.former-section-header {
    color:#E74C3C; font-size:1rem; font-weight:700; margin:28px 0 10px;
    border-left:3px solid #E74C3C; padding-left:10px;
}

/* ── Cards stay dark ── */
.metric-card {
    background: #1A1D27; border: 1px solid #2A2D3A;
    border-radius: 12px; padding: 18px 22px; margin-bottom: 12px;
}
.metric-label { color: #8A8D9A; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
.metric-value { color: #E8E8E8; font-size: 1.9rem; font-weight: 700; margin: 4px 0; }
.metric-change-pos { color: #2ECC71; font-size: 0.88rem; font-weight: 600; }
.metric-change-neg { color: #E74C3C; font-size: 0.88rem; font-weight: 600; }

.player-card {
    background: #1A1D27; border: 1px solid #2A2D3A;
    border-radius: 14px; padding: 18px 20px; margin-bottom: 12px;
}
.player-card-former {
    background: #161820; border: 1px solid #3A2A2A;
    border-radius: 14px; padding: 18px 20px; margin-bottom: 12px;
    opacity: 0.75;
}
.player-name  { color: #E8E8E8; font-size: 1.05rem; font-weight: 700; }
.player-name-former { color: #8A8D9A; font-size: 1.05rem; font-weight: 700; }
.former-badge {
    display:inline-block; background:#3A1A1A; color:#E74C3C;
    padding:2px 10px; border-radius:20px; font-size:0.72rem; font-weight:700;
    margin-left:6px; vertical-align:middle;
}

.badge-gbg { background:#1A3A5C; color:#4A90D9; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:700; }
.badge-qi  { background:#3A1A5C; color:#9B59B6; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:700; }

.profile-hero {
    background: linear-gradient(135deg,#1A1D27 0%,#12151E 100%);
    border: 1px solid #2A2D3A; border-radius:16px; padding:28px; margin-bottom:20px;
}
.profile-name        { color:#E8E8E8; font-size:1.6rem; font-weight:800; margin:0; }
.profile-name-former { color:#8A8D9A; font-size:1.6rem; font-weight:800; margin:0; }

.pill-new       { background:#1A3A1A; color:#2ECC71; padding:2px 10px; border-radius:20px; font-size:0.75rem; }
.pill-returning { background:#3A2A1A; color:#F39C12; padding:2px 10px; border-radius:20px; font-size:0.75rem; }
.pill-missing   { background:#3A1A1A; color:#E74C3C;  padding:2px 10px; border-radius:20px; font-size:0.75rem; }
.pill-active    { background:#1A1D27; color:#8A8D9A;  padding:2px 10px; border-radius:20px; font-size:0.75rem; }

.stButton button {
    background:#4A90D9 !important; color:white !important;
    border:none !important; border-radius:8px !important; font-weight:600 !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────
if "selected_player" not in st.session_state:
    st.session_state.selected_player = None
if "import_authenticated" not in st.session_state:
    st.session_state.import_authenticated = False


# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    flag_b64 = _img_to_b64(ICON_DIR / "flag_icon.png")
    gbg_b64  = _img_to_b64(ICON_DIR / "gbg_icon.png")
    qi_b64   = _img_to_b64(ICON_DIR / "qi_icon.png")

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
        f'{"<img src=data:image/png;base64," + flag_b64 + " width=28 height=28>" if flag_b64 else "🏴"}'
        f'<span style="font-size:1.2rem;font-weight:800;color:#E8E8E8;">NEXUS</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    _nav_default = ["🏴 Dashboard", "⚔️ GBG", "🌀 QI", "👤 Player Profiles", "📥 Data Import"]
    _nav_target  = st.session_state.pop("nav_page", None)
    _nav_index   = _nav_default.index(_nav_target) if _nav_target in _nav_default else 0
    page = st.radio(
        "Navigate",
        _nav_default,
        index=_nav_index,
        label_visibility="collapsed",
        format_func=lambda x: x,
    )
    st.markdown("---")

    # ── Last updated indicator ────────────────────────────────────────────
    seasons = get_all_seasons()
    all_season_names = (
        sort_seasons(seasons["gbg"], descending=True)[:1] +
        sort_seasons(seasons["qi"], descending=True)[:1]
    )
    if all_season_names:
        st.markdown(
            f'<div style="color:#8A8D9A;font-size:0.72rem;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:4px;">Latest Data</div>',
            unsafe_allow_html=True,
        )
        if seasons["gbg"]:
            st.markdown(
                f'<div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:8px;'
                f'padding:8px 10px;margin-bottom:4px;font-size:0.78rem;">'
                f'⚔️ <b>{sort_seasons(seasons["gbg"], descending=True)[0]}</b></div>',
                unsafe_allow_html=True,
            )
        if seasons["qi"]:
            st.markdown(
                f'<div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:8px;'
                f'padding:8px 10px;margin-bottom:4px;font-size:0.78rem;">'
                f'🌀 <b>{sort_seasons(seasons["qi"], descending=True)[0]}</b></div>',
                unsafe_allow_html=True,
            )
        st.markdown("---")

    # ── Player quick-jump ─────────────────────────────────────────────────
    _gbg_tmp     = get_gbg_df()
    _qi_tmp      = get_qi_df()
    _members_tmp = get_members_df()
    _all_players = get_all_players(_gbg_tmp, _qi_tmp, _members_tmp)
    _current     = _all_players.get("current", pd.DataFrame())
    if not _current.empty and "Player" in _current.columns:
        st.markdown(
            f'<div style="color:#8A8D9A;font-size:0.72rem;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:6px;">Quick Jump to Player</div>',
            unsafe_allow_html=True,
        )
        _player_names = ["—"] + sorted(_current["Player"].dropna().tolist())
        _jump = st.selectbox("Player", _player_names, label_visibility="collapsed", key="sidebar_jump")
        if _jump != "—":
            st.session_state["profile_jump"] = _jump
            st.session_state["nav_page"] = "👤 Player Profiles"
            st.rerun()


# ── Patch radio labels to include icons ───────────────────────────────────
# (Streamlit sidebar radio doesn't render HTML, so we use emoji fallbacks
#  and display the real icons in page headings instead)

# ── Load data ──────────────────────────────────────────────────────────────
gbg_df     = get_gbg_df()
qi_df      = get_qi_df()
members_df = get_members_df()
wins_df    = get_all_season_winners(gbg_df, qi_df)  # medal counts per player


# ── Strip Player_ID from any display dataframe ─────────────────────────────
def hide_pid(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[c for c in ["Player_ID", "player_id"] if c in df.columns])


# ══════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════
if page == "🏴 Dashboard":
    st.markdown(
        f'<h1>{flag_icon(32)} Guild Dashboard</h1>',
        unsafe_allow_html=True,
    )

    gbg_tots = gbg_totals(gbg_df)
    qi_tots  = qi_totals(qi_df)

    if gbg_tots.empty and qi_tots.empty:
        st.info("👋 Welcome! Head to **📥 Data Import** to upload your first season CSV.")
    else:
        # ── KPI row ───────────────────────────────────────────────────────
        health = get_guild_health(gbg_df, qi_df, members_df)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.metric("Total Guild Fights", f"{int(gbg_df['Fights'].sum()):,}" if not gbg_df.empty else "—")
        with c2:
            st.metric("Total QI Progress", f"{int(qi_df['Progress'].sum()):,}" if not qi_df.empty else "—")
        with c3:
            st.metric("GBG Seasons", gbg_df["season"].nunique() if not gbg_df.empty else 0)
        with c4:
            st.metric("QI Seasons", qi_df["season"].nunique() if not qi_df.empty else 0)
        with c5:
            part = health.get("gbg_participation")
            st.metric("GBG Participation", f"{part}%" if part is not None else "—",
                      help=f"{health.get('gbg_players','?')} of {health.get('total_members','?')} members active last season")
        with c6:
            inactive = health.get("inactive_count")
            st.metric("Zero Fights Last Season", inactive if inactive is not None else "—",
                      delta=None if inactive is None else (f"⚠️ {inactive} inactive" if inactive > 0 else "✅ All active"),
                      delta_color="inverse")

        # ── Guild health strip ────────────────────────────────────────────
        goods_latest = health.get("total_goods_latest")
        goods_delta  = health.get("goods_delta")
        inactive_names = health.get("inactive_players", [])
        if goods_latest or inactive_names:
            hc1, hc2 = st.columns(2)
            with hc1:
                if goods_latest:
                    delta_str = f"{goods_delta:+,}" if goods_delta is not None else None
                    st.metric("Total Guild Goods (Latest Snapshot)", f"{goods_latest:,}", delta=delta_str)
            with hc2:
                if inactive_names:
                    st.markdown(
                        f'<div class="section-title">⚠️ Zero Fights — Latest GBG Season</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(", ".join(inactive_names))

        st.markdown("---")

        # ── Season vs season KPI comparison ──────────────────────────────
        gbg_seasons = sort_seasons(gbg_df["season"].unique().tolist()) if not gbg_df.empty else []
        qi_seasons  = sort_seasons(qi_df["season"].unique().tolist())  if not qi_df.empty  else []

        if len(gbg_seasons) >= 2 or len(qi_seasons) >= 2:
            st.markdown('<div class="section-title">📊 Season vs Season Comparison</div>', unsafe_allow_html=True)
            kc1, kc2, kc3, kc4 = st.columns(4)
            if len(gbg_seasons) >= 2:
                curr_s, prev_s = gbg_seasons[-1], gbg_seasons[-2]
                curr_fights = int(gbg_df[gbg_df["season"] == curr_s]["Fights"].sum())
                prev_fights = int(gbg_df[gbg_df["season"] == prev_s]["Fights"].sum())
                delta_f     = curr_fights - prev_fights
                curr_players = gbg_df[gbg_df["season"] == curr_s]["Player_ID"].nunique()
                prev_players = gbg_df[gbg_df["season"] == prev_s]["Player_ID"].nunique()
                with kc1:
                    st.metric(f"GBG Fights ({curr_s})", f"{curr_fights:,}", delta=f"{delta_f:+,}")
                with kc2:
                    st.metric("GBG Players", curr_players, delta=curr_players - prev_players)
            if len(qi_seasons) >= 2:
                curr_qs, prev_qs = qi_seasons[-1], qi_seasons[-2]
                curr_prog = int(qi_df[qi_df["season"] == curr_qs]["Progress"].sum())
                prev_prog = int(qi_df[qi_df["season"] == prev_qs]["Progress"].sum())
                delta_p   = curr_prog - prev_prog
                curr_qp   = qi_df[qi_df["season"] == curr_qs]["Player_ID"].nunique()
                prev_qp   = qi_df[qi_df["season"] == prev_qs]["Player_ID"].nunique()
                with kc3:
                    st.metric(f"QI Progress ({curr_qs})", f"{curr_prog:,}", delta=f"{delta_p:+,}")
                with kc4:
                    st.metric("QI Players", curr_qp, delta=curr_qp - prev_qp)
            st.markdown("---")

        # ── Trend charts + season total CARDS ────────────────────────────
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown(f'<div class="section-title">{gbg_icon()} GBG Season Totals</div>', unsafe_allow_html=True)
            if not gbg_tots.empty:
                st.plotly_chart(gbg_guild_trend(gbg_tots), width="stretch")
                gbg_tot_disp = hide_pid(gbg_tots).rename(columns={
                    "season":"Season","total_fights":"Fights",
                    "total_negotiations":"Negotiations","total_contribution":"Total","player_count":"Players"
                })
                for _, row in gbg_tot_disp.iterrows():
                    st.markdown(f"""
                    <div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:10px;
                                padding:12px 16px;margin-bottom:6px;display:flex;align-items:center;gap:16px;">
                      <div style="flex:1;">
                        <div style="color:#E8E8E8;font-weight:700;font-size:0.9rem;">⚔️ {row['Season']}</div>
                      </div>
                      <div style="text-align:center;min-width:70px;">
                        <div style="color:#8A8D9A;font-size:0.65rem;text-transform:uppercase;">Fights</div>
                        <div style="color:#FFD700;font-weight:700;">{int(row['Fights']):,}</div>
                      </div>
                      <div style="text-align:center;min-width:70px;">
                        <div style="color:#8A8D9A;font-size:0.65rem;text-transform:uppercase;">Negotiations</div>
                        <div style="color:#4A90D9;font-weight:700;">{int(row['Negotiations']):,}</div>
                      </div>
                      <div style="text-align:center;min-width:60px;">
                        <div style="color:#8A8D9A;font-size:0.65rem;text-transform:uppercase;">Players</div>
                        <div style="color:#2ECC71;font-weight:700;">{int(row['Players'])}</div>
                      </div>
                    </div>""", unsafe_allow_html=True)

        with col_r:
            st.markdown(f'<div class="section-title">{qi_icon()} QI Season Totals</div>', unsafe_allow_html=True)
            if not qi_tots.empty:
                st.plotly_chart(qi_guild_trend(qi_tots), width="stretch")
                qi_tot_disp = hide_pid(qi_tots).rename(columns={
                    "season":"Season","total_actions":"Actions","total_progress":"Progress","player_count":"Players"
                })
                for _, row in qi_tot_disp.iterrows():
                    st.markdown(f"""
                    <div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:10px;
                                padding:12px 16px;margin-bottom:6px;display:flex;align-items:center;gap:16px;">
                      <div style="flex:1;">
                        <div style="color:#E8E8E8;font-weight:700;font-size:0.9rem;">🌀 {row['Season']}</div>
                      </div>
                      <div style="text-align:center;min-width:80px;">
                        <div style="color:#8A8D9A;font-size:0.65rem;text-transform:uppercase;">Progress</div>
                        <div style="color:#FFD700;font-weight:700;">{int(row['Progress']):,}</div>
                      </div>
                      <div style="text-align:center;min-width:80px;">
                        <div style="color:#8A8D9A;font-size:0.65rem;text-transform:uppercase;">Actions</div>
                        <div style="color:#4A90D9;font-weight:700;">{int(row['Actions']):,}</div>
                      </div>
                      <div style="text-align:center;min-width:60px;">
                        <div style="color:#8A8D9A;font-size:0.65rem;text-transform:uppercase;">Players</div>
                        <div style="color:#2ECC71;font-weight:700;">{int(row['Players'])}</div>
                      </div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── Top contributors CARDS ────────────────────────────────────────
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f'<div class="section-title">{gbg_icon()} Top GBG Contributors (Latest)</div>', unsafe_allow_html=True)
            top_gbg = hide_pid(gbg_top(gbg_df, n=10))
            if not top_gbg.empty:
                medal_map = {0:"🥇",1:"🥈",2:"🥉"}
                max_fights = top_gbg["Fights"].max() if "Fights" in top_gbg.columns else 1
                for i, (_, row) in enumerate(top_gbg.iterrows()):
                    medal   = medal_map.get(i, f"#{i+1}")
                    bar_pct = int(row.get("Fights", 0) / max(max_fights, 1) * 100)
                    bar_col = "#FFD700" if i == 0 else "#C0C0C0" if i == 1 else "#CD7F32" if i == 2 else "#4A90D9"
                    fights  = f"{int(row.get('Fights',0)):,}"
                    negs    = f"{int(row.get('Negotiations',0)):,}"
                    st.markdown(f"""
                    <div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:10px;
                                padding:12px 16px;margin-bottom:6px;">
                      <div style="display:flex;align-items:center;justify-content:space-between;">
                        <div style="display:flex;align-items:center;gap:10px;">
                          <span style="font-size:1.1rem;">{medal}</span>
                          <span style="color:#E8E8E8;font-weight:700;font-size:0.9rem;">{row['Player']}</span>
                        </div>
                        <div style="display:flex;gap:16px;">
                          <div style="text-align:right;">
                            <div style="color:#8A8D9A;font-size:0.62rem;text-transform:uppercase;">Fights</div>
                            <div style="color:#FFD700;font-weight:700;font-size:0.85rem;">{fights}</div>
                          </div>
                          <div style="text-align:right;">
                            <div style="color:#8A8D9A;font-size:0.62rem;text-transform:uppercase;">Negs</div>
                            <div style="color:#4A90D9;font-weight:700;font-size:0.85rem;">{negs}</div>
                          </div>
                        </div>
                      </div>
                      <div style="background:#0E1117;border-radius:4px;height:4px;margin-top:8px;">
                        <div style="background:{bar_col};width:{bar_pct}%;height:4px;border-radius:4px;"></div>
                      </div>
                    </div>""", unsafe_allow_html=True)

        with col_b:
            st.markdown(f'<div class="section-title">{qi_icon()} Top QI Contributors (Latest)</div>', unsafe_allow_html=True)
            top_qi = hide_pid(qi_top(qi_df, n=10))
            if not top_qi.empty:
                medal_map = {0:"🥇",1:"🥈",2:"🥉"}
                max_prog = top_qi["Progress"].max() if "Progress" in top_qi.columns else 1
                for i, (_, row) in enumerate(top_qi.iterrows()):
                    medal   = medal_map.get(i, f"#{i+1}")
                    bar_pct = int(row.get("Progress", 0) / max(max_prog, 1) * 100)
                    bar_col = "#FFD700" if i == 0 else "#C0C0C0" if i == 1 else "#CD7F32" if i == 2 else "#9B59B6"
                    prog    = f"{int(row.get('Progress',0)):,}"
                    actions = f"{int(row.get('Actions',0)):,}"
                    st.markdown(f"""
                    <div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:10px;
                                padding:12px 16px;margin-bottom:6px;">
                      <div style="display:flex;align-items:center;justify-content:space-between;">
                        <div style="display:flex;align-items:center;gap:10px;">
                          <span style="font-size:1.1rem;">{medal}</span>
                          <span style="color:#E8E8E8;font-weight:700;font-size:0.9rem;">{row['Player']}</span>
                        </div>
                        <div style="display:flex;gap:16px;">
                          <div style="text-align:right;">
                            <div style="color:#8A8D9A;font-size:0.62rem;text-transform:uppercase;">Progress</div>
                            <div style="color:#FFD700;font-weight:700;font-size:0.85rem;">{prog}</div>
                          </div>
                          <div style="text-align:right;">
                            <div style="color:#8A8D9A;font-size:0.62rem;text-transform:uppercase;">Actions</div>
                            <div style="color:#9B59B6;font-weight:700;font-size:0.85rem;">{actions}</div>
                          </div>
                        </div>
                      </div>
                      <div style="background:#0E1117;border-radius:4px;height:4px;margin-top:8px;">
                        <div style="background:{bar_col};width:{bar_pct}%;height:4px;border-radius:4px;"></div>
                      </div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── Veteran ranking CARDS ─────────────────────────────────────────
        avg1, avg2 = st.columns(2)
        with avg1:
            st.markdown(f'<div class="section-title">{gbg_icon()} Top 10 Avg Fights / Season (GBG)</div>', unsafe_allow_html=True)
            cons_gbg = get_most_consistent_players(gbg_df, qi_df, "GBG")
            if not cons_gbg.empty:
                medal_map  = {1:"🥇",2:"🥈",3:"🥉"}
                score_col  = "⭐ Score"
                avg_col    = "Avg Fights / Season"
                max_score  = int(str(cons_gbg[score_col].iloc[0]).replace(",","")) if score_col in cons_gbg.columns else 1
                for rank, (_, row) in enumerate(cons_gbg.iterrows(), 1):
                    medal   = medal_map.get(rank, f"#{rank}")
                    score_v = str(row.get(score_col,"")).replace(",","")
                    bar_pct = int(int(score_v) / max(max_score,1) * 100) if score_v.isdigit() else 0
                    bar_col = "#FFD700" if rank == 1 else "#C0C0C0" if rank == 2 else "#CD7F32" if rank == 3 else "#4A90D9"
                    st.markdown(f"""
                    <div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:10px;
                                padding:12px 16px;margin-bottom:6px;">
                      <div style="display:flex;align-items:center;justify-content:space-between;">
                        <div style="display:flex;align-items:center;gap:10px;">
                          <span style="font-size:1.0rem;">{medal}</span>
                          <span style="color:#E8E8E8;font-weight:700;font-size:0.9rem;">{row['Player']}</span>
                        </div>
                        <div style="display:flex;gap:14px;">
                          <div style="text-align:right;">
                            <div style="color:#8A8D9A;font-size:0.62rem;text-transform:uppercase;">Seasons</div>
                            <div style="color:#2ECC71;font-weight:700;font-size:0.85rem;">{row['Seasons']}</div>
                          </div>
                          <div style="text-align:right;">
                            <div style="color:#8A8D9A;font-size:0.62rem;text-transform:uppercase;">Avg / Season</div>
                            <div style="color:#FFD700;font-weight:700;font-size:0.85rem;">{row.get(avg_col,'—')}</div>
                          </div>
                          <div style="text-align:right;">
                            <div style="color:#8A8D9A;font-size:0.62rem;text-transform:uppercase;">⭐ Score</div>
                            <div style="color:#E8E8E8;font-weight:700;font-size:0.85rem;">{row.get(score_col,'—')}</div>
                          </div>
                        </div>
                      </div>
                      <div style="background:#0E1117;border-radius:4px;height:4px;margin-top:8px;">
                        <div style="background:{bar_col};width:{bar_pct}%;height:4px;border-radius:4px;"></div>
                      </div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("No GBG data yet.")

        with avg2:
            st.markdown(f'<div class="section-title">{qi_icon()} Top 10 Avg Progress / Season (QI)</div>', unsafe_allow_html=True)
            cons_qi = get_most_consistent_players(gbg_df, qi_df, "QI")
            if not cons_qi.empty:
                medal_map = {1:"🥇",2:"🥈",3:"🥉"}
                score_col = "⭐ Score"
                avg_col   = "Avg Progress / Season"
                max_score = int(str(cons_qi[score_col].iloc[0]).replace(",","")) if score_col in cons_qi.columns else 1
                for rank, (_, row) in enumerate(cons_qi.iterrows(), 1):
                    medal   = medal_map.get(rank, f"#{rank}")
                    score_v = str(row.get(score_col,"")).replace(",","")
                    bar_pct = int(int(score_v) / max(max_score,1) * 100) if score_v.isdigit() else 0
                    bar_col = "#FFD700" if rank == 1 else "#C0C0C0" if rank == 2 else "#CD7F32" if rank == 3 else "#9B59B6"
                    st.markdown(f"""
                    <div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:10px;
                                padding:12px 16px;margin-bottom:6px;">
                      <div style="display:flex;align-items:center;justify-content:space-between;">
                        <div style="display:flex;align-items:center;gap:10px;">
                          <span style="font-size:1.0rem;">{medal}</span>
                          <span style="color:#E8E8E8;font-weight:700;font-size:0.9rem;">{row['Player']}</span>
                        </div>
                        <div style="display:flex;gap:14px;">
                          <div style="text-align:right;">
                            <div style="color:#8A8D9A;font-size:0.62rem;text-transform:uppercase;">Seasons</div>
                            <div style="color:#2ECC71;font-weight:700;font-size:0.85rem;">{row['Seasons']}</div>
                          </div>
                          <div style="text-align:right;">
                            <div style="color:#8A8D9A;font-size:0.62rem;text-transform:uppercase;">Avg / Season</div>
                            <div style="color:#FFD700;font-weight:700;font-size:0.85rem;">{row.get(avg_col,'—')}</div>
                          </div>
                          <div style="text-align:right;">
                            <div style="color:#8A8D9A;font-size:0.62rem;text-transform:uppercase;">⭐ Score</div>
                            <div style="color:#E8E8E8;font-weight:700;font-size:0.85rem;">{row.get(score_col,'—')}</div>
                          </div>
                        </div>
                      </div>
                      <div style="background:#0E1117;border-radius:4px;height:4px;margin-top:8px;">
                        <div style="background:{bar_col};width:{bar_pct}%;height:4px;border-radius:4px;"></div>
                      </div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("No QI data yet.")

        st.markdown("---")

        # ── Player spotlights ─────────────────────────────────────────────
        st.markdown('<div class="section-title">🔦 Player Spotlights</div>', unsafe_allow_html=True)
        improved = get_most_improved(gbg_df, qi_df)
        streaks  = get_active_streak(gbg_df, qi_df)
        newcomers = get_newcomers(gbg_df, qi_df)

        sp1, sp2, sp3, sp4 = st.columns(4)

        def _stat_card(emoji, title, name, value_html, sub=""):
            return f"""
            <div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:12px;
                        padding:16px 18px;height:100%;min-height:120px;">
              <div style="color:#8A8D9A;font-size:0.7rem;text-transform:uppercase;
                          letter-spacing:1px;margin-bottom:6px;">{emoji} {title}</div>
              <div style="color:#E8E8E8;font-size:1rem;font-weight:700;margin-bottom:4px;">{name}</div>
              <div style="font-size:0.9rem;">{value_html}</div>
              {"<div style='color:#5A5D6A;font-size:0.72rem;margin-top:6px;'>"+sub+"</div>" if sub else ""}
            </div>"""

        with sp1:
            b = improved.get("best")
            if b:
                sign  = "+" if b["delta"] >= 0 else ""
                vhtml = f'<span style="color:#2ECC71;font-weight:700;">{sign}{b["delta"]:,} fights ({sign}{b["pct"]:.1f}%)</span>'
                st.markdown(_stat_card("🚀","Most Improved", b["player"], vhtml, b["seasons"]), unsafe_allow_html=True)
            else:
                st.markdown(_stat_card("🚀","Most Improved","—","Need 2+ seasons",""), unsafe_allow_html=True)

        with sp2:
            w = improved.get("worst")
            if w:
                sign  = "+" if w["delta"] >= 0 else ""
                col   = "#E74C3C" if w["delta"] < 0 else "#2ECC71"
                vhtml = f'<span style="color:{col};font-weight:700;">{sign}{w["delta"]:,} fights ({sign}{w["pct"]:.1f}%)</span>'
                st.markdown(_stat_card("⚠️","Needs Attention", w["player"], vhtml, w["seasons"]), unsafe_allow_html=True)
            else:
                st.markdown(_stat_card("⚠️","Needs Attention","—","Need 2+ seasons",""), unsafe_allow_html=True)

        with sp3:
            if streaks:
                top_s = streaks[0]
                vhtml = f'<span style="color:#FFD700;font-weight:700;">{top_s["streak"]} consecutive seasons</span>'
                sub   = f'{top_s["total_seasons"]} total seasons played'
                st.markdown(_stat_card("🔥","Longest Streak", top_s["player"], vhtml, sub), unsafe_allow_html=True)
            else:
                st.markdown(_stat_card("🔥","Longest Streak","—","No data",""), unsafe_allow_html=True)

        with sp4:
            if newcomers:
                names_html = "".join(
                    f'<div style="color:#4A90D9;font-size:0.85rem;">• {n["player"]} '
                    f'<span style="color:#5A5D6A;font-size:0.75rem;">({", ".join(n["sections"])})</span></div>'
                    for n in newcomers[:4]
                )
                extra = f'+{len(newcomers)-4} more' if len(newcomers) > 4 else ""
                st.markdown(f"""
                <div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:12px;
                            padding:16px 18px;min-height:120px;">
                  <div style="color:#8A8D9A;font-size:0.7rem;text-transform:uppercase;
                              letter-spacing:1px;margin-bottom:8px;">🌟 Newcomers This Season</div>
                  {names_html}
                  {"<div style='color:#5A5D6A;font-size:0.72rem;margin-top:4px;'>"+extra+"</div>" if extra else ""}
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(_stat_card("🌟","Newcomers This Season","—","No newcomers",""), unsafe_allow_html=True)

        st.markdown("---")

        # ── Hall of Fame + Active Streaks as cards ────────────────────────
        hof_data = get_hall_of_fame(gbg_df, qi_df)
        hof1, hof2 = st.columns(2)

        with hof1:
            st.markdown('<div class="section-title">🏆 Hall of Fame — All-Time #1 Finishers</div>', unsafe_allow_html=True)
            if hof_data:
                medal_map = {1:"🥇", 2:"🥈", 3:"🥉"}
                for rank, row in enumerate(hof_data, 1):
                    medal = medal_map.get(rank, f"#{rank}")
                    gbg_b = f'<span style="color:#FFD700;">⚔️ {row["gbg_wins"]}× GBG</span>' if row["gbg_wins"] else ""
                    qi_b  = f'<span style="color:#C0C0C0;">🌀 {row["qi_wins"]}× QI</span>'   if row["qi_wins"]  else ""
                    gap   = "&nbsp;&nbsp;" if row["gbg_wins"] and row["qi_wins"] else ""
                    st.markdown(f"""
                    <div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:10px;
                                padding:12px 16px;margin-bottom:8px;display:flex;
                                align-items:center;gap:14px;">
                      <div style="font-size:1.4rem;min-width:32px;">{medal}</div>
                      <div style="flex:1;">
                        <div style="color:#E8E8E8;font-weight:700;font-size:0.95rem;">{row["player"]}</div>
                        <div style="margin-top:4px;">{gbg_b}{gap}{qi_b}</div>
                      </div>
                      <div style="color:#FFD700;font-size:1.1rem;font-weight:800;">{row["total"]} 🥇</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("No season winners yet.")

        with hof2:
            st.markdown('<div class="section-title">🔥 Longest Active Streaks (GBG)</div>', unsafe_allow_html=True)
            if streaks:
                max_streak = streaks[0]["streak"] if streaks else 1
                for rank, row in enumerate(streaks, 1):
                    bar_pct = int(row["streak"] / max_streak * 100)
                    bar_col = "#FFD700" if rank == 1 else "#4A90D9" if rank <= 3 else "#2A2D3A"
                    st.markdown(f"""
                    <div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:10px;
                                padding:12px 16px;margin-bottom:8px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="color:#E8E8E8;font-weight:700;">#{rank} {row["player"]}</div>
                        <div style="color:#FFD700;font-weight:800;">{row["streak"]} 🔥</div>
                      </div>
                      <div style="background:#0E1117;border-radius:4px;height:6px;margin-top:8px;">
                        <div style="background:{bar_col};width:{bar_pct}%;height:6px;border-radius:4px;"></div>
                      </div>
                      <div style="color:#5A5D6A;font-size:0.72rem;margin-top:4px;">{row["total_seasons"]} total seasons</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("No streak data.")

        st.markdown("---")

        # ── Member leaderboards (Points / Goods / Battles) ────────────────
        ml1, ml2, ml3 = st.columns(3)

        def _leaderboard_cards(title, icon, data, value_key, value_label, value_color, sub_key=None):
            st.markdown(f'<div class="section-title">{icon} {title}</div>', unsafe_allow_html=True)
            if not data:
                st.info("No member data yet.")
                return
            medal_map = {0:"🥇", 1:"🥈", 2:"🥉"}
            max_val   = data[0][value_key] if data else 1
            for i, row in enumerate(data):
                medal   = medal_map.get(i, f"#{i+1}")
                bar_pct = int(row[value_key] / max(max_val, 1) * 100)
                bar_col = "#FFD700" if i==0 else "#C0C0C0" if i==1 else "#CD7F32" if i==2 else value_color
                val_str = f"{row[value_key]:,}"
                sub_str = row.get(sub_key, "") if sub_key else ""
                st.markdown(f"""
                <div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:10px;
                            padding:10px 14px;margin-bottom:6px;">
                  <div style="display:flex;align-items:center;justify-content:space-between;">
                    <div style="display:flex;align-items:center;gap:8px;">
                      <span style="font-size:1rem;">{medal}</span>
                      <div>
                        <div style="color:#E8E8E8;font-weight:700;font-size:0.88rem;">{row['player']}</div>
                        {"<div style='color:#8A8D9A;font-size:0.7rem;'>"+sub_str+"</div>" if sub_str else ""}
                      </div>
                    </div>
                    <div style="text-align:right;">
                      <div style="color:#8A8D9A;font-size:0.62rem;text-transform:uppercase;">{value_label}</div>
                      <div style="color:{value_color};font-weight:800;font-size:0.9rem;">{val_str}</div>
                    </div>
                  </div>
                  <div style="background:#0E1117;border-radius:4px;height:3px;margin-top:7px;">
                    <div style="background:{bar_col};width:{bar_pct}%;height:3px;border-radius:4px;"></div>
                  </div>
                </div>""", unsafe_allow_html=True)

        with ml1:
            pts_data = get_points_leaderboard(members_df, gbg_df, qi_df)
            _leaderboard_cards("Top Points", "🏅", pts_data, "points", "Points", "#FFD700", "eraName")

        with ml2:
            goods_data = get_goods_leaderboard(members_df, gbg_df, qi_df)
            _leaderboard_cards("Top Guild Goods Daily", "📦", goods_data, "guildgoods", "Goods/Day", "#4A90D9", "eraName")

        with ml3:
            battles_data = get_battles_leaderboard(members_df, gbg_df, qi_df)
            _leaderboard_cards("Top Won Battles", "⚔️", battles_data, "won_battles", "Won Battles", "#2ECC71", "eraName")

        st.markdown("---")

        # ── Points trend + Era distribution ──────────────────────────────
        pt1, pt2 = st.columns(2)
        with pt1:
            st.markdown('<div class="section-title">📈 Guild Points Trend</div>', unsafe_allow_html=True)
            if not members_df.empty:
                st.plotly_chart(points_trend_chart(members_df), width="stretch")
            else:
                st.info("No member snapshot data yet.")
        with pt2:
            st.markdown('<div class="section-title">🌍 Era Distribution</div>', unsafe_allow_html=True)
            if not members_df.empty:
                st.plotly_chart(era_distribution_chart(members_df), width="stretch")
            else:
                st.info("No member snapshot data yet.")

        st.markdown("---")

        # ── Activity heatmap ──────────────────────────────────────────────
        st.markdown('<div class="section-title">🗓️ Season Activity Heatmap (GBG Fights)</div>', unsafe_allow_html=True)
        if not gbg_df.empty:
            st.plotly_chart(activity_heatmap(gbg_df), width="stretch")
        else:
            st.info("No GBG data yet.")

        st.markdown("---")

        # ── Player status ─────────────────────────────────────────────────
        st.markdown('<div class="section-title">📋 Player Status — Latest Season</div>', unsafe_allow_html=True)
        status_df = detect_player_status(gbg_df, qi_df)
        if not status_df.empty:
            for sec in status_df["section"].unique():
                st.markdown(f"**{sec}**")
                sec_df = status_df[status_df["section"] == sec]
                latest_season = sec_df["season"].max()
                latest_df = sec_df[sec_df["season"] == latest_season]
                for status, css in [("new","pill-new"),("returning","pill-returning"),
                                     ("missing","pill-missing"),("active","pill-active")]:
                    names = latest_df[latest_df["status"] == status]["Player"].tolist()
                    if names:
                        st.markdown(
                            f'<span class="{css}">{status.upper()}: {len(names)}</span> — {", ".join(names)}',
                            unsafe_allow_html=True,
                        )


# ══════════════════════════════════════════════════════════════════════════
# PAGE: GBG
# ══════════════════════════════════════════════════════════════════════════
elif page == "⚔️ GBG":
    st.markdown(f'<h1>{gbg_icon(32)} Guild Battlegrounds (GBG)</h1>', unsafe_allow_html=True)

    if gbg_df.empty:
        st.info("No GBG data yet. Import a season in **📥 Data Import**.")
    else:
        # Filter to current players only
        _current_pids_gbg = set(gbg_df[gbg_df["season"] == sort_seasons(gbg_df["season"].unique().tolist())[-1]]["Player_ID"].astype(str))
        gbg_df_curr = gbg_df[gbg_df["Player_ID"].astype(str).isin(_current_pids_gbg)]

        seasons_list = sort_seasons(get_all_seasons()["gbg"], descending=True)
        tab_lb, tab_charts, tab_comp, tab_cumu = st.tabs(
            ["🏅 Leaderboard", "📊 Charts", "📈 Season Comparison", "📦 Cumulative"]
        )

        with tab_lb:
            col_s, col_sort = st.columns([2, 2])
            with col_s:
                sel_season = st.selectbox("Season", ["Latest"] + seasons_list, key="gbg_lb_season")
            with col_sort:
                sort_col = st.selectbox("Sort by", ["Total", "Fights", "Negotiations"], key="gbg_sort")
            season_arg = None if sel_season == "Latest" else sel_season
            lb = hide_pid(gbg_leaderboard(gbg_df_curr, season=season_arg, sort_by=sort_col))
            if not lb.empty:
                st.dataframe(lb, width="stretch")

        with tab_charts:
            chart_season = st.selectbox("Season for charts", ["Latest"] + seasons_list, key="gbg_chart_season")
            ca = None if chart_season == "Latest" else chart_season
            top_n = st.slider("Show top N players", 5, 40, 20, key="gbg_topn")
            st.plotly_chart(gbg_fights_leaderboard(gbg_df_curr, season=ca, top_n=top_n), width="stretch")
            st.plotly_chart(gbg_total_contribution_chart(gbg_df_curr, season=ca, top_n=top_n), width="stretch")
            st.plotly_chart(gbg_guild_trend(gbg_totals(gbg_df_curr)), width="stretch")

        with tab_comp:
            comp = gbg_season_comparison(gbg_df_curr)
            if comp.empty:
                st.info("Need at least 2 seasons for comparison.")
            else:
                s_curr = comp["season_current"].iloc[0]
                s_prev = comp["season_previous"].iloc[0]
                st.markdown(f"### {s_curr} vs {s_prev}")
                comp_metric = st.selectbox("Metric", ["Fights", "Negotiations", "Total"], key="gbg_comp_metric")
                display = comp[["Player", f"{comp_metric}_previous", f"{comp_metric}_current",
                                f"{comp_metric}_change", f"{comp_metric}_pct"]].copy()
                display.columns = ["Player", s_prev, s_curr, "Change", "Change %"]
                display["Change"]   = display["Change"].apply(lambda v: f"+{v:,}" if v >= 0 else f"{v:,}")
                display["Change %"] = display["Change %"].apply(lambda v: f"+{v:.2f}%" if v >= 0 else f"{v:.2f}%")
                st.dataframe(display.reset_index(drop=True), width="stretch", hide_index=True)
                st.plotly_chart(
                    comparison_waterfall(comp, comp_metric, f"GBG {comp_metric}: {s_curr} vs {s_prev}"),
                    width="stretch",
                )

        with tab_cumu:
            st.subheader("📦 Cumulative Fights (Current Players)")
            cumu = hide_pid(get_cumulative_fights(gbg_df_curr))
            if not cumu.empty:
                st.dataframe(cumu.reset_index(drop=True), width="stretch", hide_index=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: QI
# ══════════════════════════════════════════════════════════════════════════
elif page == "🌀 QI":
    st.markdown(f'<h1>{qi_icon(32)} Quantum Incursions (QI)</h1>', unsafe_allow_html=True)

    if qi_df.empty:
        st.info("No QI data yet. Import a season in **📥 Data Import**.")
    else:
        # Filter to current players only
        _current_pids_qi = set(qi_df[qi_df["season"] == sort_seasons(qi_df["season"].unique().tolist())[-1]]["Player_ID"].astype(str))
        qi_df_curr = qi_df[qi_df["Player_ID"].astype(str).isin(_current_pids_qi)]

        qi_seasons_list = sort_seasons(get_all_seasons()["qi"], descending=True)
        tab_lb, tab_charts, tab_comp, tab_cumu = st.tabs(
            ["🏅 Leaderboard", "📊 Charts", "📈 Season Comparison", "📦 Cumulative"]
        )

        with tab_lb:
            col_s, col_sort = st.columns([2, 2])
            with col_s:
                qi_sel = st.selectbox("Season", ["Latest"] + qi_seasons_list, key="qi_lb_season")
            with col_sort:
                qi_sort = st.selectbox("Sort by", ["Progress", "Actions"], key="qi_sort")
            qi_season_arg = None if qi_sel == "Latest" else qi_sel
            qi_lb = hide_pid(qi_leaderboard(qi_df_curr, season=qi_season_arg, sort_by=qi_sort))
            if not qi_lb.empty:
                st.dataframe(qi_lb, width="stretch")

        with tab_charts:
            qi_chart_s = st.selectbox("Season for charts", ["Latest"] + qi_seasons_list, key="qi_chart_season")
            qi_ca = None if qi_chart_s == "Latest" else qi_chart_s
            qi_top_n = st.slider("Show top N players", 5, 40, 20, key="qi_topn")
            st.plotly_chart(qi_progress_leaderboard(qi_df_curr, season=qi_ca, top_n=qi_top_n), width="stretch")
            st.plotly_chart(qi_guild_trend(qi_totals(qi_df_curr)), width="stretch")

        with tab_comp:
            qi_comp = qi_season_comparison(qi_df_curr)
            if qi_comp.empty:
                st.info("Need at least 2 seasons for comparison.")
            else:
                qi_s_curr = qi_comp["season_current"].iloc[0]
                qi_s_prev = qi_comp["season_previous"].iloc[0]
                st.markdown(f"### {qi_s_curr} vs {qi_s_prev}")
                qi_comp_metric = st.selectbox("Metric", ["Progress", "Actions"], key="qi_comp_metric")
                qi_display = qi_comp[["Player", f"{qi_comp_metric}_previous", f"{qi_comp_metric}_current",
                                      f"{qi_comp_metric}_change", f"{qi_comp_metric}_pct"]].copy()
                qi_display.columns = ["Player", qi_s_prev, qi_s_curr, "Change", "Change %"]
                qi_display["Change"]   = qi_display["Change"].apply(lambda v: f"+{v:,}" if v >= 0 else f"{v:,}")
                qi_display["Change %"] = qi_display["Change %"].apply(lambda v: f"+{v:.2f}%" if v >= 0 else f"{v:.2f}%")
                st.dataframe(qi_display.reset_index(drop=True), width="stretch", hide_index=True)
                st.plotly_chart(
                    comparison_waterfall(qi_comp, qi_comp_metric, f"QI {qi_comp_metric}: {qi_s_curr} vs {qi_s_prev}"),
                    width="stretch",
                )

        with tab_cumu:
            st.subheader("📦 Cumulative Progress (Current Players)")
            qi_cumu = hide_pid(get_cumulative_progress(qi_df_curr))
            if not qi_cumu.empty:
                st.dataframe(qi_cumu.reset_index(drop=True), width="stretch", hide_index=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: PLAYER PROFILES
# ══════════════════════════════════════════════════════════════════════════
elif page == "👤 Player Profiles":
    st.title("👤 Player Profiles")

    # Handle sidebar quick-jump
    _jump_name = st.session_state.pop("profile_jump", None)
    st.session_state.pop("force_profiles", None)

    players = get_all_players(gbg_df, qi_df, members_df)
    current_players = players["current"]
    former_players  = players["former"]

    if current_players.empty and former_players.empty:
        st.info("No player data found. Import seasons first.")
    else:
        # Pre-fill search if jumped from sidebar
        default_search = _jump_name if _jump_name else ""
        search = st.text_input("🔍 Search players...", value=default_search, placeholder="Type a name...")

        def filter_players(df):
            if not search:
                return df
            return df[df["Player"].str.contains(search, case=False, na=False)]

        curr_filtered   = filter_players(current_players)
        former_filtered = filter_players(former_players)

        def render_player_grid(df, is_former=False):
            if df.empty:
                return
            cols_per_row = 3
            for i in range(0, len(df), cols_per_row):
                row_df = df.iloc[i:i+cols_per_row]
                cols = st.columns(cols_per_row)
                for col, (_, prow) in zip(cols, row_df.iterrows()):
                    with col:
                        pid = str(prow["Player_ID"])
                        has_gbg = not gbg_df.empty and pid in gbg_df["Player_ID"].values
                        has_qi  = not qi_df.empty  and pid in qi_df["Player_ID"].values
                        badges = ""
                        if has_gbg: badges += '<span class="badge-gbg">GBG</span> '
                        if has_qi:  badges += '<span class="badge-qi">QI</span>'

                        avatar_html = get_avatar_html(prow["Player"], size=56)
                        name_class  = "player-name-former" if is_former else "player-name"
                        card_class  = "player-card-former" if is_former else "player-card"
                        former_tag  = '<span class="former-badge">LEFT GUILD</span>' if is_former else ""

                        # Member stats for card — pre-format to avoid f-string conflicts
                        mem = get_latest_member_stats(members_df, pid)
                        stats_html = ""
                        if mem:
                            pts  = f"{mem['points']:,}"
                            era  = mem['eraName']
                            wb   = f"{mem['won_battles']:,}"
                            gg   = f"{mem['guildgoods']:,}"
                            stats_html = (
                                f'<div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px;">'
                                f'<span style="color:#FFD700;font-size:0.8rem;font-weight:700;">🏅 {pts}</span>'
                                f'<span style="color:#8A8D9A;font-size:0.78rem;">· {era}</span>'
                                f'</div>'
                                f'<div style="margin-top:4px;display:flex;gap:12px;">'
                                f'<span style="color:#2ECC71;font-size:0.75rem;">⚔️ {wb} battles</span>'
                                f'<span style="color:#4A90D9;font-size:0.75rem;">📦 {gg} goods</span>'
                                f'</div>'
                            )

                        # Medal / round wins
                        wins_row = wins_df[wins_df["Player_ID"] == pid] if not wins_df.empty else pd.DataFrame()
                        gbg_wins = int(wins_row["gbg_wins"].iloc[0]) if not wins_row.empty else 0
                        qi_wins  = int(wins_row["qi_wins"].iloc[0])  if not wins_row.empty else 0
                        medals = ""
                        if gbg_wins > 0:
                            medals += f'<span style="color:#FFD700;font-size:0.75rem;font-weight:700;margin-left:6px;">🥇{gbg_wins}× GBG</span>'
                        if qi_wins > 0:
                            medals += f'<span style="color:#C0C0C0;font-size:0.75rem;font-weight:700;margin-left:6px;">🥇{qi_wins}× QI</span>'

                        st.markdown(f"""
                        <div class="{card_class}">
                          <div style="display:flex;align-items:flex-start;gap:14px;">
                            {avatar_html}
                            <div style="flex:1;min-width:0;">
                              <div class="{name_class}">{prow['Player']}{former_tag}{medals}</div>
                              <div style="margin-top:4px;">{badges}</div>
                              {stats_html}
                            </div>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button("View Profile", key=f"btn_{pid}"):
                            st.session_state.selected_player = pid
                            st.rerun()

        # ── Profile view or grid ──────────────────────────────────────────
        if st.session_state.selected_player is None:
            total = len(curr_filtered) + len(former_filtered)
            st.markdown(f"**{total} players found**")

            # Current members
            if not curr_filtered.empty:
                render_player_grid(curr_filtered, is_former=False)

            # Former members
            if not former_filtered.empty:
                st.markdown(
                    '<div class="former-section-header">🚪 Previous Guild Members</div>',
                    unsafe_allow_html=True,
                )
                st.caption("These players do not appear in the latest season data. Records are kept for if they rejoin.")
                render_player_grid(former_filtered, is_former=True)

        else:
            # ── Individual profile ────────────────────────────────────────
            pid = st.session_state.selected_player
            if st.button("← Back to Players"):
                st.session_state.selected_player = None
                st.rerun()

            profile     = get_player_profile(pid, gbg_df, qi_df, members_df)
            avatar_html = get_avatar_html(profile["player_name"], size=80)
            former_tag  = '<span class="former-badge" style="font-size:0.75rem;vertical-align:middle;margin-left:8px;">LEFT GUILD</span>' if profile["is_former"] else ""

            mem   = profile.get("member_stats", {})
            wins  = profile.get("wins", {})
            gbg_w = wins.get("gbg_wins", 0)
            qi_w  = wins.get("qi_wins", 0)

            # Pre-format all values to avoid nested f-string conflicts
            pts_str  = f"{mem['points']:,}"      if mem else ""
            era_str  = mem.get("eraName", "")    if mem else ""
            wb_str   = f"{mem['won_battles']:,}" if mem else ""
            gg_str   = f"{mem['guildgoods']:,}"  if mem else ""
            rank_str = f"#{mem['rank']}"         if mem else ""
            snap_str = mem.get("snapshot", "")   if mem else ""

            medal_html = ""
            if gbg_w > 0:
                medal_html += f'<span style="background:#2A2000;color:#FFD700;padding:3px 10px;border-radius:20px;font-size:0.78rem;font-weight:700;margin-left:8px;">🥇{gbg_w}× GBG</span>'
            if qi_w > 0:
                medal_html += f'<span style="background:#1A1A2A;color:#C0C0C0;padding:3px 10px;border-radius:20px;font-size:0.78rem;font-weight:700;margin-left:6px;">🥇{qi_w}× QI</span>'

            stats_block = ""
            if mem:
                stats_block = f"""
                <div style="display:flex;flex-wrap:wrap;gap:28px;margin-top:14px;padding-top:14px;
                            border-top:1px solid #2A2D3A;">
                  <div>
                    <div style="color:#8A8D9A;font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;">Points</div>
                    <div style="color:#FFD700;font-size:1.1rem;font-weight:800;">{pts_str}</div>
                  </div>
                  <div>
                    <div style="color:#8A8D9A;font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;">Era</div>
                    <div style="color:#E8E8E8;font-size:1.0rem;font-weight:700;">{era_str}</div>
                  </div>
                  <div>
                    <div style="color:#8A8D9A;font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;">Won Battles</div>
                    <div style="color:#2ECC71;font-size:1.0rem;font-weight:700;">{wb_str}</div>
                  </div>
                  <div>
                    <div style="color:#8A8D9A;font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;">Guild Goods Daily</div>
                    <div style="color:#4A90D9;font-size:1.0rem;font-weight:700;">{gg_str}</div>
                  </div>
                  <div>
                    <div style="color:#8A8D9A;font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;">Guild Rank</div>
                    <div style="color:#E8E8E8;font-size:1.0rem;font-weight:700;">{rank_str}</div>
                  </div>
                </div>
                <div style="margin-top:8px;color:#5A5D6A;font-size:0.7rem;">As of: {snap_str}</div>
                """

            st.markdown(f"""
            <div class="profile-hero">
              <div style="display:flex;align-items:flex-start;gap:22px;">
                {avatar_html}
                <div style="flex:1;">
                  <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;">
                    <span class="{'profile-name-former' if profile['is_former'] else 'profile-name'}">{profile['player_name']}</span>
                    {former_tag}{medal_html}
                  </div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if mem:
                st.markdown(f"""
                <div style="background:#1A1D27;border:1px solid #2A2D3A;border-radius:12px;
                            padding:16px 22px;margin-top:-8px;margin-bottom:16px;">
                  <div style="display:flex;flex-wrap:wrap;gap:28px;">
                    <div>
                      <div style="color:#8A8D9A;font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;">Points</div>
                      <div style="color:#FFD700;font-size:1.1rem;font-weight:800;">{pts_str}</div>
                    </div>
                    <div>
                      <div style="color:#8A8D9A;font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;">Era</div>
                      <div style="color:#E8E8E8;font-size:1.0rem;font-weight:700;">{era_str}</div>
                    </div>
                    <div>
                      <div style="color:#8A8D9A;font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;">Won Battles</div>
                      <div style="color:#2ECC71;font-size:1.0rem;font-weight:700;">{wb_str}</div>
                    </div>
                    <div>
                      <div style="color:#8A8D9A;font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;">Guild Goods Daily</div>
                      <div style="color:#4A90D9;font-size:1.0rem;font-weight:700;">{gg_str}</div>
                    </div>
                    <div>
                      <div style="color:#8A8D9A;font-size:0.68rem;text-transform:uppercase;letter-spacing:1px;">Guild Rank</div>
                      <div style="color:#E8E8E8;font-size:1.0rem;font-weight:700;">{rank_str}</div>
                    </div>
                  </div>
                  <div style="margin-top:8px;color:#5A5D6A;font-size:0.7rem;">As of: {snap_str}</div>
                </div>
                """, unsafe_allow_html=True)

            tab_gbg_p, tab_qi_p = st.tabs([
                f"{'⚔️' if not gbg_icon() else ''} GBG History",
                f"{'🌀' if not qi_icon() else ''} QI History",
            ])

            with tab_gbg_p:
                gbg_hist = profile["gbg_history"]
                gbg_chg  = profile["gbg_changes"]
                if gbg_hist.empty:
                    st.info("No GBG data for this player.")
                else:
                    if gbg_chg:
                        s_c = gbg_chg.get("season_current", "")
                        s_p = gbg_chg.get("season_previous", "")
                        st.markdown(f"**{s_c} vs {s_p}**")
                        ci1, ci2, ci3 = st.columns(3)
                        for ci, metric in zip([ci1, ci2, ci3], ["Fights", "Negotiations", "Total"]):
                            if metric in gbg_chg:
                                d = gbg_chg[metric]
                                sign = "+" if d["delta"] >= 0 else ""
                                with ci:
                                    st.metric(
                                        label=metric,
                                        value=f"{d['current']:,}",
                                        delta=f"{sign}{d['delta']:,} ({sign}{d['pct']:.2f}%)",
                                    )
                    st.markdown("---")
                    st.markdown('<div class="section-title">Season History</div>', unsafe_allow_html=True)
                    st.dataframe(
                        hide_pid(gbg_hist)[["season", "Fights", "Negotiations", "Total"]].set_index("season"),
                        width="stretch",
                    )
                    st.plotly_chart(gbg_player_trend(gbg_hist, profile["player_name"]), width="stretch")

            with tab_qi_p:
                qi_hist = profile["qi_history"]
                qi_chg  = profile["qi_changes"]
                if qi_hist.empty:
                    st.info("No QI data for this player.")
                else:
                    if qi_chg:
                        s_c = qi_chg.get("season_current", "")
                        s_p = qi_chg.get("season_previous", "")
                        st.markdown(f"**{s_c} vs {s_p}**")
                        qc1, qc2 = st.columns(2)
                        for ci, metric in zip([qc1, qc2], ["Actions", "Progress"]):
                            if metric in qi_chg:
                                d = qi_chg[metric]
                                sign = "+" if d["delta"] >= 0 else ""
                                with ci:
                                    st.metric(
                                        label=metric,
                                        value=f"{d['current']:,}",
                                        delta=f"{sign}{d['delta']:,} ({sign}{d['pct']:.2f}%)",
                                    )
                    st.markdown("---")
                    st.markdown('<div class="section-title">Season History</div>', unsafe_allow_html=True)
                    st.dataframe(
                        hide_pid(qi_hist)[["season", "Actions", "Progress"]].set_index("season"),
                        width="stretch",
                    )
                    st.plotly_chart(qi_player_trend(qi_hist, profile["player_name"]), width="stretch")

            st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: DATA IMPORT  (password-protected)
# ══════════════════════════════════════════════════════════════════════════
elif page == "📥 Data Import":
    st.title("📥 Data Import")

    # ── Password gate ─────────────────────────────────────────────────────
    if not st.session_state.import_authenticated:
        st.markdown("### 🔒 Import area is password protected")
        pwd_input = st.text_input("Enter import password", type="password", key="import_pwd")
        if st.button("Unlock"):
            if pwd_input == IMPORT_PASS:
                st.session_state.import_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.info("Contact your guild administrator for the import password.")
        st.stop()

    # Authenticated ────────────────────────────────────────────────────────
    st.success("🔓 Import unlocked")
    if st.button("🔒 Lock import"):
        st.session_state.import_authenticated = False
        st.rerun()

    tab_gbg_imp, tab_qi_imp, tab_mem_imp, tab_manage, tab_sample = st.tabs(
        ["⚔️ Import GBG", "🌀 Import QI", "👥 Import Members", "🗂️ Manage Seasons", "📄 Sample CSVs"]
    )

    with tab_gbg_imp:
        st.subheader("Import GBG Season")
        st.markdown("**Required columns:** `Player_ID`, `Player`, `Negotiations`, `Fights`, `Total`")
        gbg_season_name = st.text_input("Season name", placeholder="e.g. GBG_S1", key="gbg_season_input")
        gbg_file = st.file_uploader("Upload GBG CSV", type=["csv"], key="gbg_upload")
        if gbg_file and gbg_season_name:
            try:
                df_preview = pd.read_csv(gbg_file)
                st.dataframe(df_preview.head(), width="stretch", hide_index=True)
                if st.button("✅ Confirm Import", key="gbg_confirm"):
                    gbg_file.seek(0)
                    ok, msg = import_gbg(pd.read_csv(gbg_file), gbg_season_name.strip())
                    st.success(msg) if ok else st.error(msg)
                    if ok:
                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        elif gbg_file:
            st.warning("Enter a season name first.")

    with tab_qi_imp:
        st.subheader("Import QI Season")
        st.markdown("**Required columns:** `Player_ID`, `Player`, `Actions`, `Progress`")
        qi_season_name = st.text_input("Season name", placeholder="e.g. QI_S1", key="qi_season_input")
        qi_file = st.file_uploader("Upload QI CSV", type=["csv"], key="qi_upload")
        if qi_file and qi_season_name:
            try:
                df_preview = pd.read_csv(qi_file)
                st.dataframe(df_preview.head(), width="stretch", hide_index=True)
                if st.button("✅ Confirm Import", key="qi_confirm"):
                    qi_file.seek(0)
                    ok, msg = import_qi(pd.read_csv(qi_file), qi_season_name.strip())
                    st.success(msg) if ok else st.error(msg)
                    if ok:
                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        elif qi_file:
            st.warning("Enter a season name first.")

    with tab_mem_imp:
        st.subheader("Import Guild Member Snapshot")
        st.markdown(
            "**Required columns:** `member_id`, `member`, `points`, `eraName`, `guildgoods`, `won_battles`  \n"
            "Optional: `rank`, `eraID`"
        )
        mem_snapshot_name = st.text_input(
            "Snapshot name", placeholder="e.g. 29 Jan - 09 Feb 2026", key="mem_snapshot_input",
            help="Use the same date format as your GBG/QI seasons for consistent sorting"
        )
        mem_file = st.file_uploader("Upload Members CSV", type=["csv"], key="mem_upload")
        if mem_file and mem_snapshot_name:
            try:
                df_preview = pd.read_csv(mem_file)
                st.dataframe(df_preview.head(), width="stretch", hide_index=True)
                if st.button("✅ Confirm Import", key="mem_confirm"):
                    mem_file.seek(0)
                    ok, msg = import_members(pd.read_csv(mem_file), mem_snapshot_name.strip())
                    st.success(msg) if ok else st.error(msg)
                    if ok:
                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        elif mem_file:
            st.warning("Enter a snapshot name first.")

    with tab_manage:
        st.subheader("Manage Imported Seasons")
        all_seas = get_all_seasons()
        col_g, col_q, col_m = st.columns(3)
        with col_g:
            st.markdown("**GBG Seasons**")
            for s in all_seas.get("gbg", []):
                c1, c2 = st.columns([3, 1])
                c1.write(s)
                if c2.button("🗑️", key=f"del_gbg_{s}"):
                    st.success(delete_season("gbg", s))
                    st.rerun()
            if not all_seas.get("gbg"):
                st.info("None imported.")
        with col_q:
            st.markdown("**QI Seasons**")
            for s in all_seas.get("qi", []):
                c1, c2 = st.columns([3, 1])
                c1.write(s)
                if c2.button("🗑️", key=f"del_qi_{s}"):
                    st.success(delete_season("qi", s))
                    st.rerun()
            if not all_seas.get("qi"):
                st.info("None imported.")
        with col_m:
            st.markdown("**Member Snapshots**")
            for s in all_seas.get("members", []):
                c1, c2 = st.columns([3, 1])
                c1.write(s)
                if c2.button("🗑️", key=f"del_mem_{s}"):
                    st.success(delete_season("members", s))
                    st.rerun()
            if not all_seas.get("members"):
                st.info("None imported.")

    with tab_sample:
        st.subheader("Download Sample CSV Templates")
        gbg_sample = "Player_ID,Player,Negotiations,Fights,Total\n854681998,Zodman,0,7097,7097\n1234051,Devils Deciple.,0,5744,5744\n7954450,Bloody Pastor,116,5451,5683\n"
        qi_sample  = "Player_ID,Player,Actions,Progress\n705849,lasherbob,4262800,12150\n853267111,Kuniggsbog,3855900,11000\n854719004,soldier00,3843900,10950\n"
        mem_sample = "rank,member_id,member,points,eraID,eraName,guildgoods,won_battles\n1,705849,lasherbob,9073312254,23,SASH,40000,1001205\n2,2277993,Crusaderx,8203612815,23,SASH,27040,1377990\n3,10593569,Badvok the Bold,7465202419,23,SASH,31400,914082\n"
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button("⬇️ GBG Template", gbg_sample, "gbg_template.csv", "text/csv")
            st.code(gbg_sample)
        with c2:
            st.download_button("⬇️ QI Template", qi_sample, "qi_template.csv", "text/csv")
            st.code(qi_sample)
        with c3:
            st.download_button("⬇️ Members Template", mem_sample, "members_template.csv", "text/csv")
            st.code(mem_sample)
