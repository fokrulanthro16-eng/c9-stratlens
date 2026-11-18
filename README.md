# C9 StratLens — VALORANT & Game Changers Tactical Scouting Engine

Built for Cloud9 x JetBrains: Sky's The Limit Hackathon 2026 (Category 1: VALORANT Tactical Scouting, Utility Placement & Operator Profiler).

## Architecture
- Zero-Decompression Python 3.14 GRID .zst Streamer: Uses compression.zstd to stream official GRID match feeds and 3D ability aim/position supplements directly in memory.
- Deterministic Rules Engine ("Rules Decide, AI Explains"): Handles series-!started-game map rollbacks, player-!purchased-item purchase undos, 3D aim-vector clustering, and Operator opening-duel profiling to output actionable Cloud9 counter-playbooks.
- Strict Data Compliance: Proprietary GRID files remain outside this repository in ../stl-hackathon-2026-grid-starter and are excluded via .gitignore.

## Quick Start
Run: pip install -r requirements.txt
Run: uvicorn app.main:app --reload --port 8000
