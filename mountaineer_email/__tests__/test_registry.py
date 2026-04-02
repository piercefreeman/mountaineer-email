import pytest
from pydantic import BaseModel

from mountaineer import AppController

from mountaineer_email.controller import EmailControllerBase
from mountaineer_email.deps import get_email_template
from mountaineer_email.registry import (
    SerializedEmailController,
    clear_email_controller_cache,
    deserialize_controller,
    get_registered_email_controllers,
    serialize_controller,
)
from mountaineer_email.render import EmailMetadata, EmailRenderBase


class EmailData(BaseModel):
    message: str


class EmailRender(EmailRenderBase):
    message: str


class SampleEmailController(EmailControllerBase):
    view_path = "/emails/test/page.tsx"

    async def render(self, data: EmailData) -> EmailRender:
        return EmailRender(
            message=data.message,
            email_metadata=EmailMetadata(
                subject="Test Subject",
            ),
        )


class AnotherSampleEmailController(EmailControllerBase):
    view_path = "/emails/another/page.tsx"

    async def render(self, data: EmailData) -> EmailRender:
        return EmailRender(
            message=f"Another: {data.message}",
            email_metadata=EmailMetadata(
                subject="Another Test Subject",
            ),
        )


@pytest.fixture(autouse=True)
def clear_cache_before_test():
    clear_email_controller_cache()
    yield
    clear_email_controller_cache()


def test_serialize_controller():
    payload = serialize_controller(SampleEmailController)

    assert payload == SerializedEmailController(
        module="mountaineer_email.__tests__.test_registry",
        key="SampleEmailController",
        view_root=None,
        scripts_prefix=None,
    )


def test_deserialize_controller_requires_known_view_root_for_relative_paths():
    payload = serialize_controller(SampleEmailController)

    result = deserialize_controller(payload)

    assert isinstance(result, SampleEmailController)
    with pytest.raises(ValueError, match="view root is unknown"):
        result.hydrate_for_render()


def test_deserialize_controller_returns_fresh_hydrated_controller(
    email_app_controller: AppController,
) -> None:
    mounted_controller = SampleEmailController()
    email_app_controller.register(mounted_controller)

    payload = serialize_controller(SampleEmailController)
    result = deserialize_controller(payload)

    assert isinstance(result, SampleEmailController)
    assert result is not mounted_controller
    assert payload.view_root == str(mounted_controller._view_base_path)
    assert payload.scripts_prefix == mounted_controller._scripts_prefix
    assert result._view_base_path == mounted_controller._view_base_path
    assert result._ssr_path == mounted_controller._ssr_path


def test_get_registered_email_controllers_uses_imported_subclasses():
    registered_controllers = get_registered_email_controllers()

    assert SampleEmailController in registered_controllers.values()
    assert AnotherSampleEmailController in registered_controllers.values()


def test_deserialize_controller_raises_value_error_for_non_email_controller() -> None:
    with pytest.raises(ValueError):
        deserialize_controller(
            SerializedEmailController(
                module="pydantic",
                key="BaseModel",
            )
        )


def test_get_email_template_returns_fresh_hydrated_instance(
    email_app_controller: AppController,
) -> None:
    mounted_controller = SampleEmailController()
    email_app_controller.register(mounted_controller)

    dependency = get_email_template(SampleEmailController)
    result = dependency()

    assert isinstance(result, SampleEmailController)
    assert result is not mounted_controller
    assert result._view_base_path == mounted_controller._view_base_path
    assert result._ssr_path == mounted_controller._ssr_path
