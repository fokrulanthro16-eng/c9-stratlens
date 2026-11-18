from __future__ import annotations

from typing import Any

FALLBACK_SERIES_LIST: list[dict[str, Any]] = [
    {
        "series_id": "2748746",
        "event": "VCT Americas - Kickoff 2025",
        "stage": "Group Stage",
        "scheduled_start": "2025-01-18T00:00:00Z",
        "teams": "NRG vs Cloud9",
        "is_cloud9": True,
        "has_supplement": True,
    },
    {
        "series_id": "2767056",
        "event": "VCT Americas - Stage 1 2025",
        "stage": "Regular Season",
        "scheduled_start": "2025-03-29T21:00:00Z",
        "teams": "Cloud9 vs Sentinels",
        "is_cloud9": True,
        "has_supplement": True,
    },
]


def get_fallback_report(series_id: str) -> dict[str, Any]:
    return {
        "series_id": series_id,
        "source": "derived_aggregate_fallback",
        "metadata": {
            "series_id": series_id,
            "event": "VCT Americas - Kickoff 2025",
            "stage": "Main Stage",
            "teams": "NRG vs Cloud9",
            "games": [{"game_number": 1, "map": "haven", "team1_name": "NRG", "team1_score": 11, "team2_name": "Cloud9", "team2_score": 13}],
        },
        "utility_analysis": {
            "total_casts": 148,
            "supplement_3d_match_rate": 96.6,
            "primary_map": "haven",
            "slot_distribution": {"ABILITY_1": 52, "ABILITY_2": 46, "GRENADE": 34, "ULTIMATE": 16},
            "top_abilities": [
                {"ability": "dark-cover", "agent": "Omen", "count": 28, "avg_aim_yaw_deg": 42.5},
                {"ability": "paranoia", "agent": "Omen", "count": 19, "avg_aim_yaw_deg": 38.0},
                {"ability": "recon-bolt", "agent": "Sova", "count": 24, "avg_aim_yaw_deg": -18.4},
            ],
            "heatmap_points": [
                {"norm_x": 28.4, "norm_y": 64.2, "ability": "dark-cover", "team": "NRG", "aim_dx": 0.68, "aim_dy": 0.73},
                {"norm_x": 74.1, "norm_y": 58.9, "ability": "recon-bolt", "team": "NRG", "aim_dx": -0.45, "aim_dy": 0.89},
                {"norm_x": 51.0, "norm_y": 49.5, "ability": "paranoia", "team": "Cloud9", "aim_dx": 0.12, "aim_dy": -0.99},
            ],
            "detected_gaps": [
                "Opponent delayed A-Link smoke timing by >14s on 68% of default rounds, leaving Garage-to-C rotation exposed.",
                "Predictable Sova Recon Bolt vector from A-Lobby lands high back-site 75% of the time without front-site clear.",
            ],
        },
        "operator_profiler": {
            "net_operator_buys": 7,
            "undone_purchases_reverted": 1,
            "primary_snipers": [
                {"player": "opponent_awper", "team": "NRG", "net_buys": 5, "opening_duel_win_rate": 61.5, "preferred_zones": ["C-Long", "A-Long"]},
            ],
            "opening_duels_tracked": 24,
            "sniper_hotspots": [
                {"norm_x": 82.0, "norm_y": 31.5, "player": "opponent_awper", "outcome": "first_blood"},
                {"norm_x": 19.5, "norm_y": 36.0, "player": "opponent_awper", "outcome": "traded"},
            ],
        },
        "anti_strat_playbook": [
            {
                "priority": "HIGH",
                "category": "Operator Counter-Protocol",
                "trigger": "Opponent invests in Operator on >= 4,700 credit gun rounds with 61.5% opening pick rate on C-Long.",
                "recommended_c9_counter": "Pair Omen Paranoia across C-Long cubby with early Sova Owl Drone tag before dry-peeking; force sniper off initial line within 12s.",
            },
            {
                "priority": "HIGH",
                "category": "Utility Gap Exploitation",
                "trigger": "75% of opponent A-site executes commit early Recon Bolt without Mid/Garage denial.",
                "recommended_c9_counter": "Hold a fast Garage crunch on early A-Lobby audio cue to pinch A-Short defenders before post-plant smokes bloom.",
            },
        ],
    }
