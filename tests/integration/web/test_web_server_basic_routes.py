from fastapi.testclient import TestClient
from codesage.config.web import WebConsoleConfig
from codesage.web.server import create_app

def test_project_summary_route():
    config = WebConsoleConfig(snapshot_path="tests/fixtures/snapshot.yaml", report_path="tests/fixtures/report.json")
    app = create_app(config)
    client = TestClient(app)

    response = client.get("/api/project/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "test-project"
