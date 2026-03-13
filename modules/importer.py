"""
importer.py - Data import, validation, and persistence for Guild Tracker
"""

import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime

GBG_REQUIRED_COLS     = {"Player_ID", "Player", "Negotiations", "Fights", "Total"}
QI_REQUIRED_COLS      = {"Player_ID", "Player", "Actions", "Progress"}
MEMBER_REQUIRED_COLS  = {"member_id", "member", "points", "eraName", "guildgoods", "won_battles"}

MASTER_PATH = Path("data/processed/master.json")


def validate_gbg(df: pd.DataFrame) -> tuple[bool, str]:
    missing = GBG_REQUIRED_COLS - set(df.columns)
    if missing:
        return False, f"Missing columns: {missing}"
    return True, "OK"


def validate_qi(df: pd.DataFrame) -> tuple[bool, str]:
    missing = QI_REQUIRED_COLS - set(df.columns)
    if missing:
        return False, f"Missing columns: {missing}"
    return True, "OK"


def validate_members(df: pd.DataFrame) -> tuple[bool, str]:
    missing = MEMBER_REQUIRED_COLS - set(df.columns)
    if missing:
        return False, f"Missing columns: {missing}"
    return True, "OK"


def load_master() -> dict:
    if MASTER_PATH.exists():
        with open(MASTER_PATH, "r") as f:
            return json.load(f)
    return {"gbg": [], "qi": [], "members": [], "meta": {"last_updated": None}}


def save_master(master: dict):
    MASTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    master["meta"]["last_updated"] = datetime.now().isoformat()
    with open(MASTER_PATH, "w") as f:
        json.dump(master, f, indent=2)


def import_gbg(df: pd.DataFrame, season: str) -> tuple[bool, str]:
    ok, msg = validate_gbg(df)
    if not ok:
        return False, msg
    master = load_master()
    master["gbg"] = [r for r in master["gbg"] if r.get("season") != season]
    df = df.copy()
    df["Player_ID"]   = df["Player_ID"].astype(str)
    df["season"]      = season
    df["section"]     = "GBG"
    df["imported_at"] = datetime.now().isoformat()
    for col in ["Negotiations", "Fights", "Total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    records = df.to_dict(orient="records")
    master["gbg"].extend(records)
    save_master(master)
    return True, f"Imported {len(records)} GBG records for season '{season}'"


def import_qi(df: pd.DataFrame, season: str) -> tuple[bool, str]:
    ok, msg = validate_qi(df)
    if not ok:
        return False, msg
    master = load_master()
    master["qi"] = [r for r in master["qi"] if r.get("season") != season]
    df = df.copy()
    df["Player_ID"]   = df["Player_ID"].astype(str)
    df["season"]      = season
    df["section"]     = "QI"
    df["imported_at"] = datetime.now().isoformat()
    for col in ["Actions", "Progress"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    records = df.to_dict(orient="records")
    master["qi"].extend(records)
    save_master(master)
    return True, f"Imported {len(records)} QI records for season '{season}'"


def import_members(df: pd.DataFrame, snapshot: str) -> tuple[bool, str]:
    """Import a guild member snapshot (points, era, goods, battles)."""
    ok, msg = validate_members(df)
    if not ok:
        return False, msg
    master = load_master()
    if "members" not in master:
        master["members"] = []
    master["members"] = [r for r in master["members"] if r.get("snapshot") != snapshot]
    df = df.copy()
    # Normalise column names — accept both member_id/Player_ID, member/Player
    col_map = {}
    if "member_id" in df.columns: col_map["member_id"] = "Player_ID"
    if "member"    in df.columns: col_map["member"]    = "Player"
    df = df.rename(columns=col_map)
    df["Player_ID"]   = df["Player_ID"].astype(str)
    df["snapshot"]    = snapshot
    df["imported_at"] = datetime.now().isoformat()
    for col in ["points", "guildgoods", "won_battles"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    # keep rank if present
    if "rank" in df.columns:
        df["rank"] = pd.to_numeric(df["rank"], errors="coerce").fillna(0).astype(int)
    records = df.to_dict(orient="records")
    master["members"].extend(records)
    save_master(master)
    return True, f"Imported {len(records)} member records for snapshot '{snapshot}'"


def get_gbg_df() -> pd.DataFrame:
    master = load_master()
    if not master["gbg"]:
        return pd.DataFrame(columns=["Player_ID", "Player", "Negotiations", "Fights", "Total", "season"])
    df = pd.DataFrame(master["gbg"])
    df["Player_ID"] = df["Player_ID"].astype(str)
    return df


def get_qi_df() -> pd.DataFrame:
    master = load_master()
    if not master["qi"]:
        return pd.DataFrame(columns=["Player_ID", "Player", "Actions", "Progress", "season"])
    df = pd.DataFrame(master["qi"])
    df["Player_ID"] = df["Player_ID"].astype(str)
    return df


def get_members_df() -> pd.DataFrame:
    master = load_master()
    if not master.get("members"):
        return pd.DataFrame(columns=["Player_ID", "Player", "points", "eraName", "guildgoods", "won_battles", "snapshot"])
    df = pd.DataFrame(master["members"])
    df["Player_ID"] = df["Player_ID"].astype(str)
    return df


def get_member_snapshots() -> list[str]:
    master = load_master()
    if not master.get("members"):
        return []
    from modules.comparisons import sort_seasons
    snaps = list({r["snapshot"] for r in master["members"]})
    return sort_seasons(snaps, descending=True)


def get_all_seasons() -> dict:
    master = load_master()
    from modules.comparisons import sort_seasons
    gbg_seasons  = sort_seasons(list({r["season"]   for r in master["gbg"]}))      if master["gbg"]              else []
    qi_seasons   = sort_seasons(list({r["season"]   for r in master["qi"]}))       if master["qi"]               else []
    mem_snaps    = sort_seasons(list({r["snapshot"] for r in master.get("members",[])}), descending=True) if master.get("members") else []
    return {"gbg": gbg_seasons, "qi": qi_seasons, "members": mem_snaps}


def delete_season(section: str, season: str) -> str:
    master = load_master()
    key    = section.lower()
    if key == "members":
        before = len(master.get("members", []))
        master["members"] = [r for r in master.get("members", []) if r.get("snapshot") != season]
        removed = before - len(master["members"])
    else:
        before  = len(master[key])
        master[key] = [r for r in master[key] if r.get("season") != season]
        removed = before - len(master[key])
    save_master(master)
    return f"Removed {removed} records for {section} '{season}'"
