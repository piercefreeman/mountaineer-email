import subprocess

from fastapi.testclient import TestClient

from mountaineer.cli import handle_build

from mountaineer_email.plugin import plugin
from mountaineer_email.views import get_email_view_path


def test_plugin_boots_with_mountaineer() -> None:
    component = plugin.to_webserver()

    with TestClient(component.app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/admin/email/" in response.json()["paths"]


def test_plugin_frontend_builds() -> None:
    view_root = get_email_view_path("")
    subprocess.run(["npm", "ci"], cwd=view_root, check=True)

    handle_build(webcontroller="mountaineer_email.cli:app")

    for relative_path in (
        ".mountaineer/static/email_main.css",
        ".mountaineer/static/email_home_controller.js",
        ".mountaineer/ssr/email_home_controller.js",
    ):
        output = view_root / relative_path
        assert output.is_file() and output.stat().st_size > 0
