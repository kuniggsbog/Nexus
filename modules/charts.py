"""
charts.py - Plotly chart builders for Guild Tracker
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from modules.comparisons import sort_seasons

# ── Colour palette ──────────────────────────────────────────────────────────
GOLD   = "#FFD700"
SILVER = "#C0C0C0"
BRONZE = "#CD7F32"
BLUE   = "#4A90D9"
GREEN  = "#2ECC71"
RED    = "#E74C3C"
PURPLE = "#9B59B6"
BG     = "#0E1117"
CARD   = "#1A1D27"
TEXT   = "#E8E8E8"

LAYOUT_BASE = dict(
    paper_bgcolor=BG,
    plot_bgcolor=CARD,
    font=dict(color=TEXT, family="Inter, sans-serif"),
    margin=dict(l=40, r=20, t=50, b=40),
    xaxis=dict(gridcolor="#2A2D3A", linecolor="#2A2D3A"),
    yaxis=dict(gridcolor="#2A2D3A", linecolor="#2A2D3A"),
)


def _medal_colors(n: int) -> list[str]:
    colors = [GOLD, SILVER, BRONZE]
    return colors[:min(n, 3)] + [BLUE] * max(0, n - 3)


# ── GBG Charts ────────────────────────────────────────────────────────────

def gbg_fights_leaderboard(df: pd.DataFrame, season: str = None, top_n: int = 20) -> go.Figure:
    if df.empty:
        return go.Figure()
    if season:
        data = df[df["season"] == season]
    else:
        seasons = sort_seasons(df["season"].unique().tolist())
        data = df[df["season"] == seasons[-1]] if seasons else df

    data = data.nlargest(top_n, "Fights").sort_values("Fights")
    colors = _medal_colors(len(data))[::-1]

    fig = go.Figure(go.Bar(
        x=data["Fights"],
        y=data["Player"],
        orientation="h",
        marker=dict(color=colors),
        text=data["Fights"].apply(lambda v: f"{v:,}"),
        textposition="outside",
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text=f"⚔️ GBG Fights Leaderboard — {data['season'].iloc[-1] if not data.empty else ''}", font=dict(size=16)),
        height=max(400, top_n * 30),
        showlegend=False,
    )
    return fig


def gbg_total_contribution_chart(df: pd.DataFrame, season: str = None, top_n: int = 20) -> go.Figure:
    if df.empty:
        return go.Figure()
    if season:
        data = df[df["season"] == season]
    else:
        seasons = sort_seasons(df["season"].unique().tolist())
        data = df[df["season"] == seasons[-1]] if seasons else df

    data = data.nlargest(top_n, "Total").sort_values("Total", ascending=False)

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Fights", x=data["Player"], y=data["Fights"], marker_color=BLUE))
    fig.add_trace(go.Bar(name="Negotiations", x=data["Player"], y=data["Negotiations"], marker_color=PURPLE))
    fig.update_layout(
        **LAYOUT_BASE,
        barmode="stack",
        title=dict(text="🏆 GBG Total Contribution (Stacked)", font=dict(size=16)),
        height=450,
        legend=dict(bgcolor=CARD, bordercolor="#2A2D3A"),
    )
    return fig


def gbg_guild_trend(totals_df: pd.DataFrame) -> go.Figure:
    if totals_df.empty:
        return go.Figure()
    seasons = sort_seasons(totals_df["season"].unique().tolist())
    data = totals_df.set_index("season").loc[seasons].reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["season"], y=data["total_fights"],
        mode="lines+markers+text",
        name="Total Fights",
        line=dict(color=BLUE, width=2),
        marker=dict(size=8),
        text=data["total_fights"].apply(lambda v: f"{v:,}"),
        textposition="top center",
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="📈 Guild GBG Fights Over Seasons", font=dict(size=16)),
        height=380,
    )
    return fig


def gbg_player_trend(history_df: pd.DataFrame, player_name: str) -> go.Figure:
    if history_df.empty:
        return go.Figure()
    seasons = sort_seasons(history_df["season"].unique().tolist())
    data = history_df.set_index("season").loc[seasons].reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["season"], y=data["Fights"],
        mode="lines+markers", name="Fights",
        line=dict(color=BLUE, width=2), marker=dict(size=9),
    ))
    fig.add_trace(go.Scatter(
        x=data["season"], y=data["Total"],
        mode="lines+markers", name="Total",
        line=dict(color=GOLD, width=2, dash="dot"), marker=dict(size=7),
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text=f"⚔️ {player_name} — GBG Performance", font=dict(size=15)),
        height=350,
        legend=dict(bgcolor=CARD),
    )
    return fig


# ── QI Charts ─────────────────────────────────────────────────────────────

def qi_progress_leaderboard(df: pd.DataFrame, season: str = None, top_n: int = 20) -> go.Figure:
    if df.empty:
        return go.Figure()
    if season:
        data = df[df["season"] == season]
    else:
        seasons = sort_seasons(df["season"].unique().tolist())
        data = df[df["season"] == seasons[-1]] if seasons else df

    data = data.nlargest(top_n, "Progress").sort_values("Progress")
    colors = _medal_colors(len(data))[::-1]

    fig = go.Figure(go.Bar(
        x=data["Progress"],
        y=data["Player"],
        orientation="h",
        marker=dict(color=colors),
        text=data["Progress"].apply(lambda v: f"{v:,}"),
        textposition="outside",
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text=f"🌀 QI Progress Leaderboard — {data['season'].iloc[-1] if not data.empty else ''}", font=dict(size=16)),
        height=max(400, top_n * 30),
        showlegend=False,
    )
    return fig


def qi_guild_trend(totals_df: pd.DataFrame) -> go.Figure:
    if totals_df.empty:
        return go.Figure()
    seasons = sort_seasons(totals_df["season"].unique().tolist())
    data = totals_df.set_index("season").loc[seasons].reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["season"], y=data["total_progress"],
        mode="lines+markers+text", name="Total Progress",
        line=dict(color=PURPLE, width=2), marker=dict(size=8),
        text=data["total_progress"].apply(lambda v: f"{v:,}"),
        textposition="top center",
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="📈 Guild QI Progress Over Seasons", font=dict(size=16)),
        height=380,
    )
    return fig


def qi_player_trend(history_df: pd.DataFrame, player_name: str) -> go.Figure:
    if history_df.empty:
        return go.Figure()
    seasons = sort_seasons(history_df["season"].unique().tolist())
    data = history_df.set_index("season").loc[seasons].reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["season"], y=data["Progress"],
        mode="lines+markers", name="Progress",
        line=dict(color=PURPLE, width=2), marker=dict(size=9),
    ))
    fig.add_trace(go.Scatter(
        x=data["season"], y=data["Actions"],
        mode="lines+markers", name="Actions",
        line=dict(color=GREEN, width=2, dash="dot"), marker=dict(size=7),
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text=f"🌀 {player_name} — QI Performance", font=dict(size=15)),
        height=350,
        legend=dict(bgcolor=CARD),
    )
    return fig


# ── Comparison Charts ──────────────────────────────────────────────────────

def comparison_waterfall(comp_df: pd.DataFrame, metric: str, title: str) -> go.Figure:
    """Show top improvers and decliners as a waterfall/bar."""
    if comp_df.empty:
        return go.Figure()
    col = f"{metric}_change"
    if col not in comp_df.columns:
        return go.Figure()

    data = comp_df.sort_values(col, ascending=False)
    colors = [GREEN if v >= 0 else RED for v in data[col]]

    fig = go.Figure(go.Bar(
        x=data["Player"],
        y=data[col],
        marker=dict(color=colors),
        text=data[col].apply(lambda v: f"+{v:,}" if v >= 0 else f"{v:,}"),
        textposition="outside",
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text=title, font=dict(size=15)),
        height=420,
        showlegend=False,
    )
    return fig
