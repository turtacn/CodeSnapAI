import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import yaml
from unittest.mock import patch

from codesage.config.web import WebConsoleConfig
from codesage.web.server import create_app
from tests.unit.org.test_aggregator import mock_project_artifacts


@pytest.fixture
def test_client(mock_project_artifacts, tmp_path: Path) -> TestClient:
    org_config = {
        "org": {
            "projects": [
                {
                    "id": f"proj{i}",
                    "name": f"proj{i}",
                    "tags": ["python"],
                    "snapshot_path": str(mock_project_artifacts[f"proj{i}"]["snapshot"]),
                    "report_path": str(mock_project_artifacts[f"proj{i}"]["report"]),
                    "governance_plan_path": str(mock_project_artifacts[f"proj{i}"]["governance"]),
                }
                for i in range(1, 3)
            ]
        }
    }

    config_path = tmp_path / ".codesage.yaml"
    config_path.write_text(yaml.dump(org_config))

    with patch("pathlib.Path.cwd", return_value=tmp_path):
        app = create_app(WebConsoleConfig())
        client = TestClient(app)
        yield client


def test_get_org_projects(test_client: TestClient):
    response = test_client.get("/api/org/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "proj2"  # Sorted by health score
    assert data[1]["name"] == "proj1"


def test_get_org_report(test_client: TestClient):
    response = test_client.get("/api/org/report")
    assert response.status_code == 200
    data = response.json()
    assert data["total_projects"] == 2
    assert "avg_health_score" in data
    assert len(data["projects"]) == 2
