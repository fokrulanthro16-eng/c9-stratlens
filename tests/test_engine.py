from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_and_dashboard():
    """Test health endpoint and dashboard HTML rendering"""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    ui = client.get("/")
    assert ui.status_code == 200
    assert "C9 StratLens" in ui.text


def test_series_and_scouting_report():
    """Test series listing and full tactical report generation"""
    s = client.get("/api/v1/series?limit=5&cloud9_only=true")
    assert s.status_code == 200
    data = s.json()
    assert data["count"] >= 1
    sid = data["series"][0]["series_id"]
    rep = client.get(f"/api/v1/scout/full/{sid}")
    assert rep.status_code == 200
    body = rep.json()
    assert "utility_analysis" in body
    assert "operator_profiler" in body
    assert "anti_strat_playbook" in body
    assert len(body["anti_strat_playbook"]) >= 1
    assert "available_maps" in body
    assert "selected_map" in body


def test_per_map_filtering():
    """Test per-map filtering with map_name query parameter"""
    s = client.get("/api/v1/series?limit=5")
    assert s.status_code == 200
    data = s.json()
    assert data["count"] >= 1
    sid = data["series"][0]["series_id"]

    full_rep = client.get(f"/api/v1/scout/full/{sid}")
    assert full_rep.status_code == 200
    full_body = full_rep.json()

    if full_body.get("available_maps") and len(full_body["available_maps"]) > 0:
        map_name = full_body["available_maps"][0]
        filtered_rep = client.get(f"/api/v1/scout/full/{sid}?map_name={map_name}")
        assert filtered_rep.status_code == 200
        filtered_body = filtered_rep.json()
        assert filtered_body["selected_map"] == map_name

        for point in filtered_body["utility_analysis"]["heatmap_points"]:
            assert point["map"] == map_name


def test_heatmap_points_metadata():
    """Test that heatmap points include required per-point metadata"""
    s = client.get("/api/v1/series?limit=5")
    assert s.status_code == 200
    data = s.json()
    assert data["count"] >= 1
    sid = data["series"][0]["series_id"]

    rep = client.get(f"/api/v1/scout/full/{sid}")
    assert rep.status_code == 200
    body = rep.json()

    points = body["utility_analysis"]["heatmap_points"]
    if len(points) > 0:
        p = points[0]
        assert "round" in p
        assert "player" in p
        assert "agent" in p
        assert "team" in p
        assert "norm_x" in p
        assert "norm_y" in p
        assert "aim_dx" in p
        assert "aim_dy" in p


def test_operator_detection():
    """Test operator detection from multiple sources"""
    s = client.get("/api/v1/series?limit=5")
    assert s.status_code == 200
    data = s.json()
    assert data["count"] >= 1
    sid = data["series"][0]["series_id"]

    rep = client.get(f"/api/v1/scout/operator/{sid}")
    assert rep.status_code == 200
    body = rep.json()
    assert "operator_profiler" in body
    profiler = body["operator_profiler"]
    assert "net_operator_buys" in profiler
    assert "primary_snipers" in profiler
    assert "opening_duels_tracked" in profiler


def test_utility_and_anti_strat_endpoints():
    """Test utility-only and anti-strat-only endpoints"""
    s = client.get("/api/v1/series?limit=5")
    assert s.status_code == 200
    data = s.json()
    assert data["count"] >= 1
    sid = data["series"][0]["series_id"]

    util = client.get(f"/api/v1/scout/utility/{sid}")
    assert util.status_code == 200
    util_body = util.json()
    assert "utility_analysis" in util_body
    assert "operator_profiler" not in util_body

    anti = client.get(f"/api/v1/scout/anti-strat/{sid}")
    assert anti.status_code == 200
    anti_body = anti.json()
    assert "anti_strat_playbook" in anti_body
