import asyncio
import shutil
import subprocess
from json import loads as json_loads
from pathlib import Path
from typing import cast

import pytest
from fastapi import Depends
from pydantic import BaseModel
from pytest_httpx import HTTPXMock  # pyright: ignore[reportMissingImports]

from mountaineer import AppController, LinkAttribute, Metadata
from mountaineer.cli import handle_build
from mountaineer.dependencies import isolate_dependency_only_function
from mountaineer_cloud.primitives import (  # pyright: ignore[reportMissingImports]
    EmailBody,
    EmailMessage,
    EmailRecipient,
)
from mountaineer_cloud.providers.resend import (  # pyright: ignore[reportMissingImports]
    ResendCore,
    ResendDependencies,
)

from mountaineer_email.controller import (
    EmailControllerBase,
    FilledOutEmail,
    resolve_email_dependencies,
)
from mountaineer_email.deps import get_email_template
from mountaineer_email.render import EmailMetadata, EmailRenderBase


class InjectedTemplatePayload(BaseModel):
    recipient_name: str
    message: str


class InjectedTemplateRender(EmailRenderBase):
    recipient_name: str
    message: str


def get_message_suffix() -> str:
    return " Sent with a render dependency."


class InjectedTemplateController(EmailControllerBase):
    view_path = "/emails/dependency_injection/page.tsx"

    async def render(
        self,
        payload: InjectedTemplatePayload,
        message_suffix: str = Depends(get_message_suffix),
    ) -> InjectedTemplateRender:
        return InjectedTemplateRender(
            recipient_name=payload.recipient_name,
            message=f"{payload.message}{message_suffix}",
            email_metadata=EmailMetadata(
                subject=f"Hello {payload.recipient_name}",
            ),
            metadata=Metadata(
                links=[
                    LinkAttribute(rel="stylesheet", href="/static/emails_main.css"),
                ]
            ),
        )


def get_integration_fixture_root() -> Path:
    return Path(__file__).parent / "fixtures" / "dependency_injection_views"


def copy_integration_view(view_root: Path) -> Path:
    fixture_root = get_integration_fixture_root()

    for path_name in ["package.json", "postcss.config.mjs", "emails"]:
        fixture_path = fixture_root / path_name
        destination_path = view_root / path_name
        if fixture_path.is_dir():
            shutil.copytree(fixture_path, destination_path)
        else:
            shutil.copy(fixture_path, destination_path)

    return view_root


_BUILD_COMPONENT: AppController | None = None


async def build_email_views(app_controller: AppController) -> None:
    global _BUILD_COMPONENT
    _BUILD_COMPONENT = app_controller
    try:
        await asyncio.to_thread(
            handle_build,
            webcontroller=f"{__name__}:_BUILD_COMPONENT",
        )
    finally:
        _BUILD_COMPONENT = None


async def render_with_injected_template(
    payload: InjectedTemplatePayload,
    template: InjectedTemplateController = Depends(
        get_email_template(InjectedTemplateController)
    ),
) -> FilledOutEmail:
    return cast(FilledOutEmail, await template.render(payload))


async def send_with_injected_template_and_provider(
    payload: InjectedTemplatePayload,
    template: InjectedTemplateController = Depends(
        get_email_template(InjectedTemplateController)
    ),
    resend: ResendCore = Depends(ResendDependencies.get_resend_core),
) -> str:
    filled_email = cast(FilledOutEmail, await template.render(payload))

    message = EmailMessage[ResendCore](
        sender=EmailRecipient(
            email="noreply@example.com",
            display_name="Example App",
        ),
        recipient=EmailRecipient(email="ada@example.com"),
        subject=filled_email.subject,
        body=EmailBody(html=filled_email.html_body),
    )

    return await message.send(resend)


@pytest.mark.asyncio
async def test_dependency_injection_renders_email_template(
    view_root: Path,
    app_controller: AppController,
) -> None:
    integration_view_root = copy_integration_view(view_root)
    subprocess.run(["npm", "install"], cwd=integration_view_root, check=True)

    template_controller = InjectedTemplateController()
    app_controller.register(template_controller)

    await build_email_views(app_controller)
    payload = InjectedTemplatePayload(
        recipient_name="Ada",
        message="Integration coverage for dependency injection.",
    )

    async with resolve_email_dependencies(
        callable=isolate_dependency_only_function(render_with_injected_template),
    ) as dependency_values:
        assert isinstance(dependency_values["template"], InjectedTemplateController)
        assert dependency_values["template"] is not template_controller
        assert (
            dependency_values["template"].get_view_root()
            == template_controller.get_view_root()
        )
        result = await render_with_injected_template(
            payload=payload,
            **dependency_values,
        )

    assert isinstance(result, FilledOutEmail)
    assert result.subject == "Hello Ada"
    assert "Hello" in result.html_body
    assert "Ada" in result.html_body
    assert (
        "Integration coverage for dependency injection. Sent with a render dependency."
        in result.html_body
    )


@pytest.mark.asyncio
async def test_dependency_injection_sends_email_with_provider(
    view_root: Path,
    app_controller: AppController,
    httpx_mock: HTTPXMock,
) -> None:
    integration_view_root = copy_integration_view(view_root)
    subprocess.run(["npm", "install"], cwd=integration_view_root, check=True)

    template_controller = InjectedTemplateController()
    app_controller.register(template_controller)

    await build_email_views(app_controller)
    httpx_mock.add_response(
        method="POST",
        url="https://api.resend.test/emails",
        json={"id": "email_123"},
    )

    payload = InjectedTemplatePayload(
        recipient_name="Ada",
        message="Integration coverage for dependency injection.",
    )

    async with resolve_email_dependencies(
        callable=isolate_dependency_only_function(
            send_with_injected_template_and_provider
        ),
    ) as dependency_values:
        assert isinstance(dependency_values["template"], InjectedTemplateController)
        assert dependency_values["template"] is not template_controller
        assert (
            dependency_values["template"].get_view_root()
            == template_controller.get_view_root()
        )
        provider_message_id = await send_with_injected_template_and_provider(
            payload=payload,
            **dependency_values,
        )

    requests = httpx_mock.get_requests(url="https://api.resend.test/emails")
    assert len(requests) == 1

    request_body = json_loads(requests[0].content.decode())
    assert provider_message_id == "email_123"
    assert request_body["from"] == "Example App <noreply@example.com>"
    assert request_body["to"] == ["ada@example.com"]
    assert request_body["subject"] == "Hello Ada"
    assert (
        "Integration coverage for dependency injection. Sent with a render dependency."
        in request_body["html"]
    )
