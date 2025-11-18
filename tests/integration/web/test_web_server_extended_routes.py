from fastapi.testclient import TestClient
from codesage.config.web import WebConsoleConfig
from codesage.web.server import create_app

def test_list_files_route():
    config = WebConsoleConfig(snapshot_path="tests/fixtures/snapshot.yaml", report_path="tests/fixtures/report.json")
    app = create_app(config)
    client = TestClient(app)

    response = client.get("/api/files")
    assert response.status_code == 200

def test_get_file_detail_route():
    config = WebConsoleConfig(snapshot_path="tests/fixtures/snapshot.yaml")
    app = create_app(config)
    client = TestClient(app)

    response = client.get("/api/files/a/b/c.py")
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "a/b/c.py"

def test_get_governance_plan_route():
    config = WebConsoleConfig(governance_plan_path="tests/fixtures/governance_plan.yaml")
    app = create_app(config)
    client = TestClient(app)

    response = client.get("/api/governance/plan")
    assert response.status_code == 200
    data = response.json()
    assert len(data["groups"]) == 1

def test_get_task_jules_prompt_route():
    config = WebConsoleConfig(snapshot_path="tests/fixtures/snapshot.yaml", governance_plan_path="tests/fixtures/governance_plan.yaml")
    app = create_app(config)
    client = TestClient(app)

    response = client.get("/api/governance/tasks/test-task-1/jules-prompt")
    assert response.status_code == 200
    data = response.json()
    assert "prompt" in data
