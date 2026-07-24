from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_demo_creates_attempt_and_dashboard_log():
    with TestClient(app) as client:
        response = client.post("/api/attempts/demo?severity=3")
        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "demo"
        assert body["review"]["provider"] == "demo-policy-engine"
        assert body["review"]["validation_status"] == "DEMO_VALIDATED"
        assert body["worst_segments"]

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        assert dashboard.json()["total_attempts"] >= 1


def test_high_severity_routes_to_human_review():
    with TestClient(app) as client:
        response = client.post(
            "/api/attempts/demo",
            params={"severity": 9, "pain_description": "동작 중 통증이 심합니다"},
        )
        assert response.status_code == 200
        review = response.json()["review"]
        assert review["verdict"] == "REVIEW"
        assert review["requires_review"] is True

        tasks = client.get("/api/review-tasks").json()
        assert any(task["status"] == "OPEN" for task in tasks)

