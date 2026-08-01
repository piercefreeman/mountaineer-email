import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import Request
from pydantic import BaseModel

from mountaineer import AppController, LinkAttribute, Metadata
from mountaineer.cli import handle_build

from mountaineer_email.__tests__.fixtures import get_fixtures_path
from mountaineer_email.controller import (
    EmailControllerBase,
    FilledOutEmail,
)
from mountaineer_email.render import (
    EmailMetadata,
    EmailRenderBase,
)


class ExampleData(BaseModel):
    value: str


_BUILD_COMPONENT: AppController | None = None


async def simple_build(app_controller: AppController) -> None:
    global _BUILD_COMPONENT
    _BUILD_COMPONENT = app_controller
    try:
        await asyncio.to_thread(
            handle_build,
            webcontroller=f"{__name__}:_BUILD_COMPONENT",
        )
    finally:
        _BUILD_COMPONENT = None


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
    assert {
        path.name for path in (mock_application_view / ".mountaineer" / "ssr").iterdir()
    } == {
        "example_email_controller.js",
        "example_email_controller.js.map",
    }
    assert "emails_main.css" in [
        path.name
        for path in Path(mock_application_view / ".mountaineer" / "static").iterdir()
    ]

    # Check that this is a regular css definition file that has sniffed our contents and isn't
    # including every style from tailwind
    css_contents = (
        mock_application_view / ".mountaineer/static/emails_main.css"
    ).read_text()
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
    result = await email_controller._generate_email(
        initial_data=ExampleData(value="MY_DYNAMIC_VALUE"),
    )

    assert "MY_DYNAMIC_VALUE" in result.html_body


@pytest.mark.asyncio
async def test_render_helper_with_model_instance(
    mock_application_view: Path,
    app_controller: AppController,
):
    subprocess.run(["npm", "install"], cwd=mock_application_view, check=True)

    email_controller = ExampleEmailController()
    app_controller.register(email_controller)

    await simple_build(app_controller)
    result = await email_controller.render(ExampleData(value="POSITIONAL_VALUE"))

    assert isinstance(result, FilledOutEmail)
    assert "POSITIONAL_VALUE" in result.html_body


@pytest.mark.asyncio
async def test_render_obj_helper(
    mock_application_view: Path,
    app_controller: AppController,
):
    subprocess.run(["npm", "install"], cwd=mock_application_view, check=True)

    email_controller = ExampleEmailController()
    app_controller.register(email_controller)

    await simple_build(app_controller)
    result = await email_controller.render_obj({"value": "DICT_VALUE"})

    assert "DICT_VALUE" in result.html_body


@pytest.mark.asyncio
async def test_render_helper_with_dict_payload(
    mock_application_view: Path,
    app_controller: AppController,
):
    subprocess.run(["npm", "install"], cwd=mock_application_view, check=True)

    email_controller = ExampleEmailController()
    app_controller.register(email_controller)

    await simple_build(app_controller)
    result = await cast(Any, email_controller).render({"value": "DICT_RENDER_VALUE"})

    assert isinstance(result, FilledOutEmail)
    assert "DICT_RENDER_VALUE" in result.html_body


@pytest.mark.asyncio
async def test_render_with_kwargs_returns_render_model(
    mock_application_view: Path,
    app_controller: AppController,
):
    subprocess.run(["npm", "install"], cwd=mock_application_view, check=True)

    email_controller = ExampleEmailController()
    app_controller.register(email_controller)

    await simple_build(app_controller)
    result = await email_controller.render(
        initial_data=ExampleData(value="KWARG_VALUE")
    )

    assert isinstance(result, ExampleEmailRender)
    assert result.initial_value == "KWARG_VALUE"


@pytest.mark.asyncio
async def test_generate_email_with_request_scope(
    mock_application_view: Path,
    app_controller: AppController,
):
    subprocess.run(["npm", "install"], cwd=mock_application_view, check=True)

    email_controller = ExampleEmailController()
    app_controller.register(email_controller)

    await simple_build(app_controller)
    request = Request(
        scope={
            "type": "http",
            "path": "/admin/email/example_email",
            "path_params": {},
            "query_string": b"",
            "headers": [],
        }
    )
    result = await email_controller._generate_email_with_request(
        request,
        initial_data=ExampleData(value="REQUEST_VALUE"),
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
