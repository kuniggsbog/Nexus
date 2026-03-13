"""
comparisons.py - Season-over-season comparison calculations
"""

import pandas as pd
import numpy as np


def sort_seasons(seasons: list[str]) -> list[str]:
    """Sort seasons alphanumerically so S10 comes after S9."""
    import re
    def key(s):
        parts = re.split(r'(\d+)', s)
        return [int(p) if p.isdigit() else p.lower() for p in parts]
    return sorted(seasons, key=key)


def compute_change(current: float, previous: float) -> tuple[float, float]:
    """Return (absolute_change, percent_change)."""
    delta = current - previous
    if previous == 0:
        pct = 100.0 if delta > 0 else 0.0
    else:
        pct = (delta / previous) * 100
    return round(delta, 0), round(pct, 2)


def format_change(delta: float, pct: float) -> str:
    sign = "+" if delta >= 0 else ""
    return f"{sign}{int(delta):,} ({sign}{pct:.2f}%)"


def gbg_season_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Compare each player's latest GBG season vs previous."""
    if df.empty:
        return pd.DataFrame()

    seasons = sort_seasons(df["season"].unique().tolist())
    if len(seasons) < 2:
        return pd.DataFrame()

    latest = seasons[-1]
    previous = seasons[-2]

    curr = df[df["season"] == latest].set_index("Player_ID")
    prev = df[df["season"] == previous].set_index("Player_ID")

    rows = []
    for pid in curr.index:
        row = {"Player_ID": pid, "Player": curr.loc[pid, "Player"]}
        for col in ["Fights", "Negotiations", "Total"]:
            c_val = curr.loc[pid, col]
            p_val = prev.loc[pid, col] if pid in prev.index else 0
            delta, pct = compute_change(c_val, p_val)
            row[f"{col}_current"] = int(c_val)
            row[f"{col}_previous"] = int(p_val)
            row[f"{col}_change"] = int(delta)
            row[f"{col}_pct"] = pct
        row["season_current"] = latest
        row["season_previous"] = previous
        rows.append(row)

    return pd.DataFrame(rows)


def qi_season_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Compare each player's latest QI season vs previous."""
    if df.empty:
        return pd.DataFrame()

    seasons = sort_seasons(df["season"].unique().tolist())
    if len(seasons) < 2:
        return pd.DataFrame()

    latest = seasons[-1]
    previous = seasons[-2]

    curr = df[df["season"] == latest].set_index("Player_ID")
    prev = df[df["season"] == previous].set_index("Player_ID")

    rows = []
    for pid in curr.index:
        row = {"Player_ID": pid, "Player": curr.loc[pid, "Player"]}
        for col in ["Actions", "Progress"]:
            c_val = curr.loc[pid, col]
            p_val = prev.loc[pid, col] if pid in prev.index else 0
            delta, pct = compute_change(c_val, p_val)
            row[f"{col}_current"] = int(c_val)
            row[f"{col}_previous"] = int(p_val)
            row[f"{col}_change"] = int(delta)
            row[f"{col}_pct"] = pct
        row["season_current"] = latest
        row["season_previous"] = previous
        rows.append(row)

    return pd.DataFrame(rows)


def detect_player_status(gbg_df: pd.DataFrame, qi_df: pd.DataFrame) -> pd.DataFrame:
    """Detect new, returning, missing players per season."""
    results = []

    for section, df in [("GBG", gbg_df), ("QI", qi_df)]:
        if df.empty:
            continue
        seasons = sort_seasons(df["season"].unique().tolist())
        for i, season in enumerate(seasons):
            current_players = set(df[df["season"] == season]["Player_ID"].astype(str))
            if i == 0:
                for pid in current_players:
                    name = df[(df["season"] == season) & (df["Player_ID"].astype(str) == pid)]["Player"].values[0]
                    results.append({"section": section, "season": season, "Player_ID": pid, "Player": name, "status": "new"})
            else:
                prev_season = seasons[i - 1]
                prev_players = set(df[df["season"] == prev_season]["Player_ID"].astype(str))
                all_prev = set(df[df["season"].isin(seasons[:i])]["Player_ID"].astype(str))

                for pid in current_players:
                    name = df[(df["season"] == season) & (df["Player_ID"].astype(str) == pid)]["Player"].values[0]
                    if pid not in all_prev:
                        status = "new"
                    elif pid not in prev_players:
                        status = "returning"
                    else:
                        status = "active"
                    results.append({"section": section, "season": season, "Player_ID": pid, "Player": name, "status": status})

                for pid in prev_players - current_players:
                    name = df[(df["season"] == prev_season) & (df["Player_ID"].astype(str) == pid)]["Player"].values[0]
                    results.append({"section": section, "season": season, "Player_ID": pid, "Player": name, "status": "missing"})

    return pd.DataFrame(results) if results else pd.DataFrame()


def most_improved_gbg(df: pd.DataFrame, metric: str = "Total") -> pd.DataFrame:
    """Return players sorted by biggest improvement in a GBG metric."""
    comp = gbg_season_comparison(df)
    if comp.empty:
        return pd.DataFrame()
    return comp.sort_values(f"{metric}_pct", ascending=False).head(10)


def most_improved_qi(df: pd.DataFrame, metric: str = "Progress") -> pd.DataFrame:
    comp = qi_season_comparison(df)
    if comp.empty:
        return pd.DataFrame()
    return comp.sort_values(f"{metric}_pct", ascending=False).head(10)
