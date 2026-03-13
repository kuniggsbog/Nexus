"""
player_profile.py - Player profile aggregation with former-member detection
"""

import pandas as pd
from modules.comparisons import sort_seasons, compute_change, format_change
from modules.gbg_analysis import player_gbg_history
from modules.qi_analysis import player_qi_history


def get_latest_member_stats(members_df: pd.DataFrame, player_id: str) -> dict:
    """Return the most recent member snapshot stats for a player."""
    if members_df.empty:
        return {}
    pid_rows = members_df[members_df["Player_ID"].astype(str) == str(player_id)]
    if pid_rows.empty:
        return {}
    snaps = sort_seasons(pid_rows["snapshot"].unique().tolist(), descending=True)
    latest = pid_rows[pid_rows["snapshot"] == snaps[0]].iloc[0]
    return {
        "points":      int(latest.get("points", 0)),
        "eraName":     str(latest.get("eraName", "—")),
        "guildgoods":  int(latest.get("guildgoods", 0)),
        "won_battles": int(latest.get("won_battles", 0)),
        "rank":        int(latest.get("rank", 0)),
        "snapshot":    snaps[0],
    }


def get_all_players(gbg_df: pd.DataFrame, qi_df: pd.DataFrame, members_df: pd.DataFrame = None) -> dict:
    """
    Return current and former player lists.
    If members_df provided, current players are sorted by points descending.
    """
    latest_pids = set()

    for df in [gbg_df, qi_df]:
        if not df.empty:
            seasons = sort_seasons(df["season"].unique().tolist())
            latest_season = seasons[-1]
            pids = df[df["season"] == latest_season]["Player_ID"].astype(str).tolist()
            latest_pids.update(pids)

    # Also consider players in latest member snapshot as current
    if members_df is not None and not members_df.empty:
        snaps = sort_seasons(members_df["snapshot"].unique().tolist(), descending=True)
        latest_snap_pids = members_df[members_df["snapshot"] == snaps[0]]["Player_ID"].astype(str).tolist()
        latest_pids.update(latest_snap_pids)

    all_rows = []
    for df in [gbg_df, qi_df]:
        if not df.empty:
            all_rows.append(df[["Player_ID", "Player"]].drop_duplicates())
    if members_df is not None and not members_df.empty:
        mem_cols = members_df[["Player_ID", "Player"]].drop_duplicates()
        all_rows.append(mem_cols)

    if not all_rows:
        return {"current": pd.DataFrame(columns=["Player_ID", "Player"]),
                "former":  pd.DataFrame(columns=["Player_ID", "Player"])}

    combined = pd.concat(all_rows).drop_duplicates(subset=["Player_ID"])
    combined["Player_ID"] = combined["Player_ID"].astype(str)

    current = combined[combined["Player_ID"].isin(latest_pids)].copy()
    former  = combined[~combined["Player_ID"].isin(latest_pids)].copy()

    # Sort current players by points descending if member data available
    if members_df is not None and not members_df.empty and not current.empty:
        snaps = sort_seasons(members_df["snapshot"].unique().tolist(), descending=True)
        latest_mem = members_df[members_df["snapshot"] == snaps[0]][["Player_ID", "points"]].copy()
        latest_mem["Player_ID"] = latest_mem["Player_ID"].astype(str)
        current = current.merge(latest_mem, on="Player_ID", how="left")
        current["points"] = pd.to_numeric(current["points"], errors="coerce").fillna(0)
        current = current.sort_values("points", ascending=False).drop(columns=["points"])
    else:
        current = current.sort_values("Player")

    former = former.sort_values("Player").reset_index(drop=True)
    current = current.reset_index(drop=True)

    return {"current": current, "former": former}


def get_player_profile(player_id: str, gbg_df: pd.DataFrame, qi_df: pd.DataFrame,
                       members_df: pd.DataFrame = None) -> dict:
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
        "member_stats": get_latest_member_stats(members_df, pid) if members_df is not None else {},
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
