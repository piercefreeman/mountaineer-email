import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi import Request
from inflection import underscore
from pydantic import BaseModel

from mountaineer import (
    AppController,
    LinkAttribute,
    Metadata,
    mountaineer as mountaineer_rs,  # ty: ignore[unresolved-import]
)
from mountaineer.client_builder.builder import APIBuilder
from mountaineer.client_compiler.compile import ClientCompiler
from mountaineer.static import get_static_path

from mountaineer_email.__tests__.fixtures import get_fixtures_path
from mountaineer_email.controller import (
    EmailControllerBase,
)
from mountaineer_email.render import (
    EmailMetadata,
    EmailRenderBase,
)


class ExampleData(BaseModel):
    value: str


async def simple_build(app_controller: AppController):
    """
    Simplified, in-code version of the build CLI.
    TODO: Refactor the actual CLI into a separate `build_controller` function
    since it doesn't depend on the hot reloader

    """
    js_compiler = APIBuilder(
        app_controller,
        live_reload_port=None,
    )
    client_compiler = ClientCompiler(app_controller)

    # Build the latest client support files (useServer)
    await js_compiler.build_all()
    await client_compiler.run_builder_plugins()

    ssr_output = app_controller._view_root.get_managed_ssr_dir()

    all_view_paths: list[list[str]] = []
    for controller_definition in app_controller.graph.controllers:
        all_view_paths += controller_definition.get_hierarchy_view_paths()

    # Now we go one-by-one to provide the SSR files, which will be consolidated
    # into a single runnable script for ease of use by the V8 engine
    result_scripts, _ = mountaineer_rs.compile_independent_bundles(
        all_view_paths,
        str(app_controller._view_root / "node_modules"),
        "production",
        0,
        str(get_static_path("live_reload.ts").resolve().absolute()),
        True,
    )

    for controller, script in zip(app_controller.graph.controllers, result_scripts):
        script_root = underscore(controller.controller.__class__.__name__)
        (ssr_output / f"{script_root}.js").write_text(script)


@pytest.fixture
def mock_application_view(view_root: Path):
    """
    Set up a fake application view
    """
    # Copy over our fixture to the tmp path
    for path_name in [
        "package.json",
        "postcss.config.mjs",
        "emails",
    ]:
        fixture_path = get_fixtures_path("test_views") / path_name
        if fixture_path.is_dir():
            shutil.copytree(fixture_path, view_root / path_name)
        else:
            shutil.copy(fixture_path, view_root / path_name)

    return view_root


class ExampleEmailRender(EmailRenderBase):
    initial_value: str


class ExampleEmailController(EmailControllerBase):
    view_path = "/emails/email1/page.tsx"

    async def render(
        self,
        initial_data: ExampleData,
    ) -> ExampleEmailRender:
        return ExampleEmailRender(
            initial_value=initial_data.value,
            email_metadata=EmailMetadata(
                subject=f"Hello, World! {initial_data.value}",
                to_email="user@example.com",
            ),
            metadata=Metadata(
                links=[
                    LinkAttribute(rel="stylesheet", href="/static/emails_main.css"),
                ]
            ),
        )


@pytest.mark.asyncio
async def test_build_email_controller(
    mock_application_view: Path,
    app_controller: AppController,
):
    """
    Ensure that we can add our email to our AppController, and it will
    successfully register with the builder logic.

    """
    # Init this directory with npm
    subprocess.run(["npm", "install"], cwd=mock_application_view, check=True)

    email_controller = ExampleEmailController()
    app_controller.register(email_controller)

    # Build the email SSR definitions
    await simple_build(app_controller)

    # Ensure that the builder has generated the expected files
    assert {path.name for path in (mock_application_view / "_ssr").iterdir()} == {
        "example_email_controller.js",
    }
    assert "emails_main.css" in [
        path.name for path in Path(mock_application_view / "_static").iterdir()
    ]

    # Check that this is a regular css definition file that has sniffed our contents and isn't
    # including every style from tailwind
    css_contents = (mock_application_view / "_static/emails_main.css").read_text()
    assert ".text-blue-500" in css_contents
    assert ".text-green-500" not in css_contents

    # We can also move this to a fixture for debugging
    # get_fixtures_path("example_tailwind.css").write_text(css_contents)


@pytest.mark.asyncio
async def test_generate_email(
    mock_application_view: Path,
    app_controller: AppController,
):
    # Init this directory with npm
    subprocess.run(["npm", "install"], cwd=mock_application_view, check=True)

    email_controller = ExampleEmailController()
    app_controller.register(email_controller)

    # Build the email SSR definitions
    await simple_build(app_controller)
    email_controller.resolve_paths(app_controller._view_root, force=True)

    result = await email_controller._generate_email(
        initial_data=ExampleData(value="MY_DYNAMIC_VALUE"),
    )

    assert "MY_DYNAMIC_VALUE" in result.html_body


@pytest.mark.asyncio
async def test_generate_email_with_request_scope(
    mock_application_view: Path,
    app_controller: AppController,
):
    subprocess.run(["npm", "install"], cwd=mock_application_view, check=True)

    email_controller = ExampleEmailController()
    app_controller.register(email_controller)

    await simple_build(app_controller)
    email_controller.resolve_paths(app_controller._view_root, force=True)

    request = Request(
        scope={
            "type": "http",
            "path": "/admin/email/example_email",
            "path_params": {},
            "query_string": b"",
            "headers": [],
        }
    )
    result = await email_controller._generate_email(
        initial_data=ExampleData(value="REQUEST_VALUE"),
        request=request,
    )

    assert "REQUEST_VALUE" in result.html_body


def test_get_input_model():
    controller = ExampleEmailController()
    assert controller.get_input_model() == ("initial_data", ExampleData)


# @pytest.mark.asyncio
# async def test_email_url_is_inaccessible(
#     app_controller: AppController,
#     mock_application_view: Path,
#     view_root: Path,
# ):
#     """
#     Email controllers shouldn't be directly accessible via our web router
#     """
#     # Init this directory with npm
#     subprocess.run(["npm", "install"], cwd=mock_application_view, check=True)

#     email_controller = ExampleEmailController()
#     app_controller.register(email_controller)

#     # Build the email SSR definitions
#     await simple_build(app_controller)

#     client = TestClient(app_controller.app)

#     # By default, the status code will be unprocessable entity
#     # because Mountaineer will sniff the render() method for its
#     # pydantic argument and fail since it's a regular GET request
#     # that doesn't include a JSON body
#     result = client.get(email_controller.url)
#     assert result.status_code == 422

#     # Also make sure that if we manipulate the Request to include
#     # a JSON body, it will still fail
#     response = client.request(
#         method="GET",
#         url=email_controller.url,
#         json=ExampleData(value="test").model_dump(),
#     )
#     assert response.status_code == 404
