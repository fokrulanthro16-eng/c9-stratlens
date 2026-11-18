from __future__ import annotations

import pathlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.core.sample_aggregates import FALLBACK_SERIES_LIST
from app.core.tactical_engine import build_tactical_report
from app.services.grid_streamer import list_valorant_series

STATIC_DIR = pathlib.Path(__file__).parent / "static"

app = FastAPI(
    title="C9 StratLens — VALORANT & Game Changers Tactical Scouting Engine",
    version="1.0.0",
    description="Deterministic GRID telemetry & 3D ability vector scouting platform built with JetBrains PyCharm Pro.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def serve_dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "C9 StratLens Python 3.14 GRID Streamer"}


@app.get("/api/v1/series")
def get_series(limit: int = 40, cloud9_only: bool = False) -> dict[str, object]:
    items = list_valorant_series(limit=limit, cloud9_only=cloud9_only)
    if not items:
        items = FALLBACK_SERIES_LIST
    return {"count": len(items), "series": items}


@app.get("/api/v1/scout/full/{series_id}")
def scout_full(series_id: str, map_name: str | None = None) -> dict[str, object]:
    return build_tactical_report(series_id, map_filter=map_name)


@app.get("/api/v1/scout/utility/{series_id}")
def scout_utility(series_id: str, map_name: str | None = None) -> dict[str, object]:
    report = build_tactical_report(series_id, map_filter=map_name)
    return {
        "series_id": series_id,
        "source": report["source"],
        "selected_map": report["selected_map"],
        "metadata": report["metadata"],
        "utility_analysis": report["utility_analysis"],
    }


@app.get("/api/v1/scout/operator/{series_id}")
def scout_operator(series_id: str, map_name: str | None = None) -> dict[str, object]:
    report = build_tactical_report(series_id, map_filter=map_name)
    return {
        "series_id": series_id,
        "source": report["source"],
        "selected_map": report["selected_map"],
        "metadata": report["metadata"],
        "operator_profiler": report["operator_profiler"],
    }


@app.get("/api/v1/scout/anti-strat/{series_id}")
def scout_anti_strat(series_id: str, map_name: str | None = None) -> dict[str, object]:
    report = build_tactical_report(series_id, map_filter=map_name)
    return {
        "series_id": series_id,
        "source": report["source"],
        "selected_map": report["selected_map"],
        "metadata": report["metadata"],
        "anti_strat_playbook": report["anti_strat_playbook"],
    }
