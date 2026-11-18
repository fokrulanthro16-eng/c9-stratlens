from __future__ import annotations

import csv
import json
import os
import pathlib
from compression import zstd
from typing import Any

INVALIDATED_SERIES = {"2855902"}


def get_data_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("STL_DATA_DIR", "../stl-hackathon-2026-grid-starter"))


def read_jsonl_zst(path: pathlib.Path):
    with zstd.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def list_valorant_series(limit: int = 80, cloud9_only: bool = False) -> list[dict[str, Any]]:
    data_dir = get_data_dir()
    series_csv = data_dir / "val" / "series.csv"
    if not series_csv.exists():
        return []

    results: list[dict[str, Any]] = []
    with open(series_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = row.get("series_id", "")
            if sid in INVALIDATED_SERIES:
                continue
            teams = row.get("teams", "")
            is_c9 = "Cloud9" in teams
            if cloud9_only and not is_c9:
                continue
            results.append({
                "series_id": sid,
                "event": row.get("event", ""),
                "stage": row.get("stage", ""),
                "scheduled_start": row.get("scheduled_start", ""),
                "teams": teams,
                "is_cloud9": is_c9,
                "has_supplement": bool(row.get("ability_supplement")),
            })

    results.sort(key=lambda r: r["scheduled_start"], reverse=True)
    c9_first = [r for r in results if r["is_cloud9"]] + [r for r in results if not r["is_cloud9"]]
    return c9_first[:limit]


def load_series_metadata(series_id: str) -> dict[str, Any]:
    data_dir = get_data_dir()
    meta: dict[str, Any] = {
        "series_id": series_id,
        "event": "VCT Americas / Game Changers",
        "stage": "Main Stage",
        "teams": "Cloud9 vs Opponent",
        "games": [],
        "rosters": [],
    }
    series_csv = data_dir / "val" / "series.csv"
    if series_csv.exists():
        with open(series_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("series_id") == series_id:
                    meta["event"] = row.get("event", meta["event"])
                    meta["stage"] = row.get("stage", meta["stage"])
                    meta["teams"] = row.get("teams", meta["teams"])
                    break

    games_csv = data_dir / "meta" / "games.csv"
    if games_csv.exists():
        with open(games_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("title") == "val" and row.get("series_id") == series_id:
                    meta["games"].append({
                        "game_id": row.get("game_id"),
                        "game_number": int(row.get("game_number") or 1),
                        "map": row.get("map", "unknown"),
                        "team1_name": row.get("team1_name", ""),
                        "team1_score": int(row.get("team1_score") or 0),
                        "team2_name": row.get("team2_name", ""),
                        "team2_score": int(row.get("team2_score") or 0),
                    })

    rosters_csv = data_dir / "meta" / "rosters.csv"
    if rosters_csv.exists():
        with open(rosters_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("title") == "val" and row.get("series_id") == series_id:
                    meta["rosters"].append({
                        "team_name": row.get("team_name", ""),
                        "player_id": row.get("player_id", ""),
                        "player_name": row.get("player_name", ""),
                        "character_name": row.get("character_name", ""),
                    })
    return meta


def _state_has_operator(state: dict[str, Any]) -> bool:
    for key in ("inventory", "items", "weapons", "loadout"):
        seq = state.get(key)
        if not seq:
            continue
        if isinstance(seq, dict):
            seq = seq.values()
        for item in seq:
            label = str(item.get("name") or item.get("id") or "") if isinstance(item, dict) else str(item)
            if "operator" in label.lower():
                return True
    w = state.get("weapon")
    if isinstance(w, dict) and "operator" in str(w.get("name") or w.get("id") or "").lower():
        return True
    return False


def stream_series_telemetry(series_id: str) -> dict[str, Any] | None:
    if series_id in INVALIDATED_SERIES:
        return None
    data_dir = get_data_dir()
    feed_path = data_dir / "val" / f"events_{series_id}_grid.jsonl.zst"
    if not feed_path.exists():
        return None

    supp_path = data_dir / "val-ability-supplements" / f"{series_id}.jsonl.zst"
    supplements: dict[str, dict[str, Any]] = {}
    if supp_path.exists():
        for rec in read_jsonl_zst(supp_path):
            if rec.get("in_grid") and rec.get("grid_event_id"):
                supplements[rec["grid_event_id"]] = rec

    meta = load_series_metadata(series_id)
    roster_map = {r["player_id"]: r for r in meta["rosters"] if r.get("player_id")}

    rolled_back_games: set[str] = set()
    ability_casts: list[dict[str, Any]] = []
    operator_events: list[dict[str, Any]] = []
    opening_kills: list[dict[str, Any]] = []
    round_operator_holders: set[tuple[str, int, str]] = set()

    current_game_id = ""
    current_map = meta["games"][0]["map"] if meta["games"] else "haven"
    map_bounds = {"min": {"x": -10000.0, "y": -10000.0}, "max": {"x": 10000.0, "y": 10000.0}}
    round_num = 0
    round_had_first_kill = False

    for env in read_jsonl_zst(feed_path):
        occurred_at = env.get("occurredAt", "")
        for ev in env.get("events", []):
            etype = ev.get("type", "")
            actor = ev.get("actor") or {}
            target = ev.get("target") or {}
            actor_state = actor.get("state") or {}
            target_state = target.get("state") or {}
            s_state = ev.get("seriesState") or {}

            if s_state.get("games"):
                active_g = s_state["games"][-1]
                current_game_id = str(active_g.get("id") or current_game_id)
                m_info = active_g.get("map") or {}
                if m_info.get("name"):
                    current_map = m_info["name"]
                if m_info.get("bounds"):
                    map_bounds = m_info["bounds"]

                for t_obj in active_g.get("teams") or []:
                    t_name = t_obj.get("name") or ""
                    for p_obj in t_obj.get("players") or []:
                        p_id = str(p_obj.get("id") or "")
                        if p_id and _state_has_operator(p_obj):
                            key = (current_game_id, round_num, p_id)
                            if key not in round_operator_holders:
                                round_operator_holders.add(key)
                                r_info = roster_map.get(p_id, {})
                                operator_events.append({
                                    "game_id": current_game_id,
                                    "map": current_map,
                                    "round": round_num,
                                    "delta": 1,
                                    "player_name": p_obj.get("name") or r_info.get("player_name") or "Unknown",
                                    "team_name": t_name or r_info.get("team_name") or "Unknown",
                                    "agent": r_info.get("character_name") or "Agent",
                                    "money_before": p_obj.get("money"),
                                })

            if etype == "series-!started-game":
                rb_id = str(target.get("id") or current_game_id)
                if rb_id:
                    rolled_back_games.add(rb_id)
                continue

            if current_game_id and current_game_id in rolled_back_games:
                continue

            if etype == "game-started-round":
                round_num += 1
                round_had_first_kill = False

            pid = str(actor.get("id") or "")
            if pid and _state_has_operator(actor_state):
                key = (current_game_id, round_num, pid)
                if key not in round_operator_holders:
                    round_operator_holders.add(key)
                    r_info = roster_map.get(pid, {})
                    operator_events.append({
                        "game_id": current_game_id,
                        "map": current_map,
                        "round": round_num,
                        "delta": 1,
                        "player_name": actor_state.get("name") or r_info.get("player_name") or "Unknown",
                        "team_name": r_info.get("team_name") or "Unknown",
                        "agent": r_info.get("character_name") or "Agent",
                        "money_before": actor_state.get("money"),
                    })

            if etype == "player-used-ability":
                r_info = roster_map.get(pid, {})
                player_name = actor_state.get("name") or r_info.get("player_name") or "Unknown"
                team_name = r_info.get("team_name") or "Unknown"
                agent = r_info.get("character_name") or (actor_state.get("character") or {}).get("name") or "Agent"
                supp = supplements.get(ev.get("id", ""))

                pos = (supp.get("interpolated") or {}).get("position") if supp else actor_state.get("position")
                view = (supp.get("interpolated") or {}).get("view") if supp else {"x": 0.0, "y": 0.0, "z": 0.0}
                ability_name = (supp.get("ability") if supp else None) or target_state.get("name") or str(target.get("id") or "ability")
                slot = (supp.get("slot") if supp else None) or "ABILITY"

                if pos and "x" in pos and "y" in pos:
                    ability_casts.append({
                        "game_id": current_game_id,
                        "map": current_map,
                        "round": round_num,
                        "occurred_at": occurred_at,
                        "player_id": pid,
                        "player_name": player_name,
                        "team_name": team_name,
                        "agent": agent,
                        "ability": ability_name,
                        "slot": slot,
                        "position": {"x": float(pos["x"]), "y": float(pos["y"]), "z": float(pos.get("z", 0.0))},
                        "view": {"x": float(view.get("x", 0.0)), "y": float(view.get("y", 0.0)), "z": float(view.get("z", 0.0))},
                        "supplement_matched": bool(supp),
                        "bounds": map_bounds,
                    })

            elif etype in ("player-purchased-item", "player-!purchased-item"):
                item_label = f"{target_state.get('name', '')} {target.get('id', '')}".lower()
                if "operator" in item_label:
                    r_info = roster_map.get(pid, {})
                    key = (current_game_id, round_num, pid)
                    if etype == "player-!purchased-item":
                        round_operator_holders.discard(key)
                        operator_events.append({
                            "game_id": current_game_id,
                            "map": current_map,
                            "round": round_num,
                            "delta": -1,
                            "player_name": actor_state.get("name") or r_info.get("player_name") or "Unknown",
                            "team_name": r_info.get("team_name") or "Unknown",
                            "agent": r_info.get("character_name") or "Agent",
                            "money_before": actor_state.get("money"),
                        })
                    elif key not in round_operator_holders:
                        round_operator_holders.add(key)
                        operator_events.append({
                            "game_id": current_game_id,
                            "map": current_map,
                            "round": round_num,
                            "delta": 1,
                            "player_name": actor_state.get("name") or r_info.get("player_name") or "Unknown",
                            "team_name": r_info.get("team_name") or "Unknown",
                            "agent": r_info.get("character_name") or "Agent",
                            "money_before": actor_state.get("money"),
                        })

            elif etype == "player-killed-player":
                vid = str(target.get("id") or "")
                k_info = roster_map.get(pid, {})
                v_info = roster_map.get(vid, {})
                is_opening = not round_had_first_kill
                if is_opening:
                    round_had_first_kill = True
                weapon_used = str((ev.get("weapon") or {}).get("name") or (actor_state.get("weapon") or {}).get("name") or "")
                if "operator" in weapon_used.lower() and pid:
                    key = (current_game_id, round_num, pid)
                    if key not in round_operator_holders:
                        round_operator_holders.add(key)
                        operator_events.append({
                            "game_id": current_game_id,
                            "map": current_map,
                            "round": round_num,
                            "delta": 1,
                            "player_name": actor_state.get("name") or k_info.get("player_name") or "Unknown",
                            "team_name": k_info.get("team_name") or "Unknown",
                            "agent": k_info.get("character_name") or "Agent",
                            "money_before": actor_state.get("money"),
                        })
                opening_kills.append({
                    "game_id": current_game_id,
                    "map": current_map,
                    "round": round_num,
                    "is_opening_duel": is_opening,
                    "weapon": weapon_used,
                    "killer_name": actor_state.get("name") or k_info.get("player_name") or "Unknown",
                    "killer_team": k_info.get("team_name") or "Unknown",
                    "victim_name": target_state.get("name") or v_info.get("player_name") or "Unknown",
                    "victim_team": v_info.get("team_name") or "Unknown",
                    "killer_pos": actor_state.get("position") or {"x": 0.0, "y": 0.0},
                    "victim_pos": target_state.get("position") or {"x": 0.0, "y": 0.0},
                    "bounds": map_bounds,
                })

    if rolled_back_games:
        ability_casts = [c for c in ability_casts if c["game_id"] not in rolled_back_games]
        operator_events = [o for o in operator_events if o["game_id"] not in rolled_back_games]
        opening_kills = [k for k in opening_kills if k["game_id"] not in rolled_back_games]

    return {
        "source": "live_grid_zst_stream",
        "metadata": meta,
        "rolled_back_game_ids": sorted(rolled_back_games),
        "ability_casts": ability_casts,
        "operator_events": operator_events,
        "opening_kills": opening_kills,
    }
