# AI-Powered Workflow Story — Building C9 StratLens with JetBrains PyCharm Pro

## JetBrains Tooling Stack
- **IDE**: JetBrains PyCharm Pro (Python 3.14 virtual environment with native `compression.zstd` streaming).
- **AI Assistance**: JetBrains AI Assistant + Claude Code for type-annotated FastAPI endpoints, GRID event rollback state machines, spatial coordinate normalization, and interactive dashboard development.
- **Repository Evidence**: `.idea/` project configuration and run metadata committed directly to Git.

## Category 1 Features Delivered

### 1. Deep Operator Snapshot Parser (`app/services/grid_streamer.py`)
- **Zero-Disk Decompression**: Streams Python 3.14 `compression.zstd` from `../stl-hackathon-2026-grid-starter` without intermediate file extraction.
- **Multi-Source Operator Detection**:
  - `player-purchased-item` / `player-!purchased-item` events
  - Nested `inventory`, `weapons`, `loadout` fields in `seriesState.games[].teams[].players[]` and `actor.state`
  - `weapon` metadata on `player-killed-player` events
- **Rollback & Invalidation Guards**: Filters `series-!started-game` rollbacks and invalidated series (`2855902`).

### 2. Per-Map Filtering (`app/core/tactical_engine.py` + `app/main.py`)
- **API Query Parameter**: `/api/v1/scout/full/{series_id}?map_name=ascent` supports Best-of-3 map-by-map inspection.
- **Response Schema**: Returns `available_maps`, `selected_map`, and per-point metadata (`round`, `player`, `agent`, `team`, `norm_x`, `norm_y`, `aim_dx`, `aim_dy`).

### 3. Interactive War-Room Dashboard (`app/static/index.html`)
- **Game / Map Selector**: Dropdown populated from `available_maps` (Game 1, Game 2, Game 3).
- **Team Filter**: `Both Teams`, `Opponent Only`, `Cloud9 Only` with color coding:
  - Cyan = Cloud9
  - Pink = Opponent
  - Amber = Opening First-Blood Duels
- **Canvas Hover Tooltip**: Shows player name, team, agent, ability/kill info, and round number on mouse hover.
- **Copy Coach Brief**: One-click clipboard copy of tactical playbook summary.

### 4. Test Suite & Documentation
- **`pytest.ini`**: Configured with `pythonpath = .` for clean imports.
- **`tests/test_engine.py`**: 6 comprehensive tests covering health checks, per-map filtering, heatmap metadata, operator detection, and endpoint isolation.
- **`pytest -v`**: All tests pass with GRID data integrity validation.

## Engineering Challenges Solved
1. **Streaming 160 GB of Uncompressed Telemetry on an 8 GB RAM Laptop**: Single-pass generator pipeline in `app/services/grid_streamer.py` using Python 3.14's built-in `compression.zstd`.
2. **GRID Event Stream Edge Cases**: Handled invalidated series, abandoned/restarted maps (`series-!started-game`), and undone Operator purchases (`player-!purchased-item`).
3. **Multi-Level Operator Detection**: Deep inventory inspection across `seriesState` nested objects, event-driven purchase tracking, and kill-event weapon metadata.
