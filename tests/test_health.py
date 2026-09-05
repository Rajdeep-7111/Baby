from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["app"] == "Baby"


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_tools_endpoint_lists_registered_tools() -> None:
    response = client.get("/tools")

    assert response.status_code == 200

    assert [tool["name"] for tool in response.json()["tools"]] == [
        "calculator",
        "datetime",
        "file_reader",
        "web_search",
        "web_fetch",
                "calendar",
    ]