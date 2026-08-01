from fastapi.testclient import TestClient

from mountaineer_email.plugin import plugin


def test_plugin_boots_with_mountaineer() -> None:
    component = plugin.to_webserver()

    with TestClient(component.app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/admin/email/" in response.json()["paths"]
