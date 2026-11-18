from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from app.core.sample_aggregates import get_fallback_report
from app.services.grid_streamer import stream_series_telemetry


def _normalize_coord(val: float, min_v: float, max_v: float) -> float:
    span = max_v - min_v
    if span <= 0:
        return 50.0
    pct = ((val - min_v) / span) * 100.0
    return round(max(2.0, min(98.0, pct)), 2)


def build_tactical_report(series_id: str, map_filter: str | None = None) -> dict[str, Any]:
    raw = stream_series_telemetry(series_id)
    if raw is None or (not raw["ability_casts"] and not raw["opening_kills"]):
        return get_fallback_report(series_id)

    meta = raw["metadata"]
    available_maps = list(dict.fromkeys(
        [g["map"] for g in meta.get("games", []) if g.get("map")]
        + [c["map"] for c in raw["ability_casts"] if c.get("map")]
    ))
    selected_map = map_filter if (map_filter and map_filter != "all") else (available_maps[0] if available_maps else "haven")

    casts = [c for c in raw["ability_casts"] if c.get("map") == selected_map] if map_filter != "all" else raw["ability_casts"]
    op_events = [o for o in raw["operator_events"] if o.get("map") == selected_map] if map_filter != "all" else raw["operator_events"]
    kills = [k for k in raw["opening_kills"] if k.get("map") == selected_map] if map_filter != "all" else raw["opening_kills"]

    if not casts and not kills:
        casts = raw["ability_casts"]
        op_events = raw["operator_events"]
        kills = raw["opening_kills"]
        selected_map = "all"

    total_casts = len(casts)
    supp_matched = sum(1 for c in casts if c.get("supplement_matched"))
    match_rate = round((supp_matched / total_casts) * 100.0, 1) if total_casts else 0.0

    slot_counts = Counter(c["slot"] for c in casts)
    ability_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for c in casts:
        ability_groups[(c["ability"], c["agent"])].append(c)

    top_abilities = []
    for (ab, ag), items in sorted(ability_groups.items(), key=lambda x: len(x[1]), reverse=True)[:8]:
        yaws = [
            math.degrees(math.atan2(i["view"]["y"], i["view"]["x"]))
            for i in items
            if i["view"]["x"] != 0.0 or i["view"]["y"] != 0.0
        ]
        avg_yaw = round(sum(yaws) / len(yaws), 1) if yaws else 0.0
        top_abilities.append({
            "ability": ab,
            "agent": ag,
            "count": len(items),
            "avg_aim_yaw_deg": avg_yaw,
        })

    heatmap_points = []
    for c in casts[:260]:
        b = c["bounds"]
        nx = _normalize_coord(c["position"]["x"], b["min"]["x"], b["max"]["x"])
        ny = _normalize_coord(c["position"]["y"], b["min"]["y"], b["max"]["y"])
        heatmap_points.append({
            "norm_x": nx,
            "norm_y": ny,
            "round": c["round"],
            "player": c["player_name"],
            "ability": c["ability"],
            "agent": c["agent"],
            "team": c["team_name"],
            "map": c["map"],
            "aim_dx": round(c["view"]["x"], 3),
            "aim_dy": round(c["view"]["y"], 3),
        })

    net_buys_by_player: dict[tuple[str, str], int] = defaultdict(int)
    reverted_count = 0
    for ev in op_events:
        if ev["delta"] < 0:
            reverted_count += 1
        net_buys_by_player[(ev["player_name"], ev["team_name"])] += ev["delta"]

    opening_duels = [k for k in kills if k["is_opening_duel"]]
    fb_wins = Counter(k["killer_name"] for k in opening_duels)
    fb_losses = Counter(k["victim_name"] for k in opening_duels)

    primary_snipers = []
    for (pname, tname), buys in sorted(net_buys_by_player.items(), key=lambda x: x[1], reverse=True):
        if buys <= 0:
            continue
        wins = fb_wins[pname]
        losses = fb_losses[pname]
        total_duels = wins + losses
        win_rate = round((wins / total_duels) * 100.0, 1) if total_duels else 50.0
        primary_snipers.append({
            "player": pname,
            "team": tname,
            "net_buys": buys,
            "opening_duel_win_rate": win_rate,
            "opening_first_bloods": wins,
        })

    sniper_hotspots = []
    for k in opening_duels[:60]:
        b = k["bounds"]
        pos = k["killer_pos"]
        sniper_hotspots.append({
            "norm_x": _normalize_coord(float(pos.get("x", 0.0)), b["min"]["x"], b["max"]["x"]),
            "norm_y": _normalize_coord(float(pos.get("y", 0.0)), b["min"]["y"], b["max"]["y"]),
            "round": k["round"],
            "player": k["killer_name"],
            "victim": k["victim_name"],
            "team": k["killer_team"],
            "map": k["map"],
            "outcome": "first_blood",
        })

    detected_gaps = []
    if top_abilities:
        lead = top_abilities[0]
        share = round((lead["count"] / max(1, total_casts)) * 100.0, 1)
        detected_gaps.append(
            f"Heavy utility concentration on {lead['agent']} ({lead['ability']}: {lead['count']} casts, {share}% of map utility) creates predictable execute timing."
        )
    if len(opening_duels) >= 3:
        top_fb = fb_wins.most_common(1)[0]
        detected_gaps.append(
            f"{top_fb[0]} secured {top_fb[1]} opening first-blood kills across {len(opening_duels)} tracked rounds on {selected_map.upper()}."
        )

    playbook = []
    if primary_snipers:
        s = primary_snipers[0]
        playbook.append({
            "priority": "HIGH",
            "category": "Operator Tendency Counter",
            "trigger": f"{s['player']} ({s['team']}) held an Operator in {s['net_buys']} rounds with a {s['opening_duel_win_rate']}% opening duel win rate.",
            "recommended_c9_counter": f"Deny early dry-peek sightlines against {s['player']} using pre-round flash/recon utility and double-swing off-angles within the first 15 seconds.",
        })
    if top_abilities:
        lead = top_abilities[0]
        playbook.append({
            "priority": "HIGH",
            "category": "Utility & Vector Exploit",
            "trigger": f"Recurring {lead['ability']} casts ({lead['count']}x, mean yaw {lead['avg_aim_yaw_deg']} deg) on {selected_map.upper()} signal telegraphed site hits.",
            "recommended_c9_counter": "Trigger counter-flank pinch immediately when initial signature utility is expended rather than conceding full site control.",
        })

    return {
        "series_id": series_id,
        "source": raw["source"],
        "rolled_back_games_excluded": len(raw["rolled_back_game_ids"]),
        "available_maps": available_maps,
        "selected_map": selected_map,
        "metadata": meta,
        "utility_analysis": {
            "total_casts": total_casts,
            "supplement_3d_match_rate": match_rate,
            "primary_map": selected_map,
            "slot_distribution": dict(slot_counts),
            "top_abilities": top_abilities,
            "heatmap_points": heatmap_points,
            "detected_gaps": detected_gaps,
        },
        "operator_profiler": {
            "net_operator_buys": sum(s["net_buys"] for s in primary_snipers),
            "undone_purchases_reverted": reverted_count,
            "primary_snipers": primary_snipers,
            "opening_duels_tracked": len(opening_duels),
            "sniper_hotspots": sniper_hotspots,
        },
        "anti_strat_playbook": playbook,
    }
