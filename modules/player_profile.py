"""
player_profile.py - Player profile aggregation with former-member detection
"""

import pandas as pd
from modules.comparisons import sort_seasons, compute_change, format_change
from modules.gbg_analysis import player_gbg_history
from modules.qi_analysis import player_qi_history


def get_all_players(gbg_df: pd.DataFrame, qi_df: pd.DataFrame) -> dict:
    """
    Return two lists:
      - current_players: seen in latest season of either section
      - former_players:  have historical data but not in any latest season
    Both sorted by Player name. Player_ID is kept internal only.
    """
    latest_pids = set()

    for df in [gbg_df, qi_df]:
        if not df.empty:
            seasons = sort_seasons(df["season"].unique().tolist())
            latest_season = seasons[-1]
            pids = df[df["season"] == latest_season]["Player_ID"].astype(str).tolist()
            latest_pids.update(pids)

    all_rows = []
    for df in [gbg_df, qi_df]:
        if not df.empty:
            all_rows.append(df[["Player_ID", "Player"]].drop_duplicates())

    if not all_rows:
        return {"current": pd.DataFrame(columns=["Player_ID", "Player"]),
                "former": pd.DataFrame(columns=["Player_ID", "Player"])}

    combined = pd.concat(all_rows).drop_duplicates(subset=["Player_ID"])
    combined["Player_ID"] = combined["Player_ID"].astype(str)

    current = combined[combined["Player_ID"].isin(latest_pids)].sort_values("Player").reset_index(drop=True)
    former  = combined[~combined["Player_ID"].isin(latest_pids)].sort_values("Player").reset_index(drop=True)

    return {"current": current, "former": former}


def get_player_profile(player_id: str, gbg_df: pd.DataFrame, qi_df: pd.DataFrame) -> dict:
    """Build a full profile dict for a given player_id."""
    pid = str(player_id)

    gbg_hist = player_gbg_history(gbg_df, pid)
    qi_hist  = player_qi_history(qi_df, pid)

    player_name = "Unknown"
    if not gbg_hist.empty:
        player_name = gbg_hist["Player"].iloc[-1]
    elif not qi_hist.empty:
        player_name = qi_hist["Player"].iloc[-1]

    # Determine if former member
    is_former = True
    for df in [gbg_df, qi_df]:
        if not df.empty:
            seasons = sort_seasons(df["season"].unique().tolist())
            latest = seasons[-1]
            if pid in df[df["season"] == latest]["Player_ID"].astype(str).values:
                is_former = False
                break

    profile = {
        "player_id": pid,
        "player_name": player_name,
        "is_former": is_former,
        "gbg_history": gbg_hist,
        "qi_history": qi_hist,
        "gbg_changes": {},
        "qi_changes": {},
    }

    if len(gbg_hist) >= 2:
        latest = gbg_hist.iloc[-1]
        prev   = gbg_hist.iloc[-2]
        for col in ["Fights", "Negotiations", "Total"]:
            delta, pct = compute_change(latest[col], prev[col])
            profile["gbg_changes"][col] = {
                "current": int(latest[col]),
                "previous": int(prev[col]),
                "delta": int(delta),
                "pct": pct,
                "formatted": format_change(delta, pct),
                "positive": delta >= 0,
            }
        profile["gbg_changes"]["season_current"]  = latest["season"]
        profile["gbg_changes"]["season_previous"] = prev["season"]

    if len(qi_hist) >= 2:
        latest = qi_hist.iloc[-1]
        prev   = qi_hist.iloc[-2]
        for col in ["Actions", "Progress"]:
            delta, pct = compute_change(latest[col], prev[col])
            profile["qi_changes"][col] = {
                "current": int(latest[col]),
                "previous": int(prev[col]),
                "delta": int(delta),
                "pct": pct,
                "formatted": format_change(delta, pct),
                "positive": delta >= 0,
            }
        profile["qi_changes"]["season_current"]  = latest["season"]
        profile["qi_changes"]["season_previous"] = prev["season"]

    return profile


def get_most_consistent_players(gbg_df: pd.DataFrame, qi_df: pd.DataFrame, section: str = "GBG") -> pd.DataFrame:
    df = gbg_df if section == "GBG" else qi_df
    if df.empty:
        return pd.DataFrame()
    counts = (df.groupby(["Player_ID", "Player"])["season"]
                .nunique()
                .reset_index()
                .rename(columns={"season": "seasons_active"})
                .sort_values("seasons_active", ascending=False))
    return counts[["Player", "seasons_active"]]
