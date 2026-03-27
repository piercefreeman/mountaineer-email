import pytest
from pydantic import BaseModel

from mountaineer import AppController

from mountaineer_email.config import EmailConfig
from mountaineer_email.controller import EmailControllerBase
from mountaineer_email.registry import (
    clear_email_controller_cache,
    controller_to_registry_id,
    get_email_controller,
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
                to_email="test@example.com",
            ),
        )


class AnotherSampleEmailController(EmailControllerBase):
    view_path = "/emails/another/page.tsx"

    async def render(self, data: EmailData) -> EmailRender:
        return EmailRender(
            message=f"Another: {data.message}",
            email_metadata=EmailMetadata(
                subject="Another Test Subject",
                to_email="another@example.com",
            ),
        )


@pytest.fixture(autouse=True)
def clear_cache_before_test():
    """Clear the email controller cache before each test."""
    clear_email_controller_cache()
    yield
    clear_email_controller_cache()


def test_controller_to_registry_id():
    """Test that controller_to_registry_id returns the correct registry ID."""
    # Get the registry ID
    registry_id = controller_to_registry_id(SampleEmailController)

    # Verify it's a string and matches what we expect from the registry
    assert isinstance(registry_id, str)
    assert (
        registry_id == "mountaineer_email.__tests__.test_registry.SampleEmailController"
    )


def test_clear_email_controller_cache():
    """Test that clear_email_controller_cache properly clears the global cache."""
    import mountaineer_email.registry as registry_module

    # Set up some fake cache data
    registry_module.EMAIL_CONTROLLER_CACHE = {"test_id": SampleEmailController()}
    assert registry_module.EMAIL_CONTROLLER_CACHE is not None

    # Clear the cache
    clear_email_controller_cache()

    # Verify it's been cleared
    assert registry_module.EMAIL_CONTROLLER_CACHE is None


def test_get_email_controller_builds_cache_on_first_call(
    email_app_controller: AppController, config: EmailConfig
):
    """Test that get_email_controller builds the cache on first call."""
    # Create and register test controllers
    test_controller = SampleEmailController()
    another_controller = AnotherSampleEmailController()

    email_app_controller.register(test_controller)
    email_app_controller.register(another_controller)

    # Get registry IDs for our controllers
    test_registry_id = controller_to_registry_id(SampleEmailController)

    # Call get_email_controller
    result = get_email_controller(test_registry_id, config)

    # Verify the result
    assert result == test_controller

    # Verify the cache was built
    import mountaineer_email.registry as registry_module

    assert registry_module.EMAIL_CONTROLLER_CACHE is not None
    assert len(registry_module.EMAIL_CONTROLLER_CACHE) == 2
    assert registry_module.EMAIL_CONTROLLER_CACHE[test_registry_id] == test_controller


def test_get_email_controller_uses_existing_cache(
    email_app_controller: AppController, config: EmailConfig
):
    """Test that get_email_controller uses existing cache on subsequent calls."""
    # Create a test controller
    test_controller = SampleEmailController()
    test_registry_id = controller_to_registry_id(SampleEmailController)

    # Pre-populate the cache
    import mountaineer_email.registry as registry_module

    registry_module.EMAIL_CONTROLLER_CACHE = {test_registry_id: test_controller}

    # Call get_email_controller
    result = get_email_controller(test_registry_id, config)

    # Verify the result
    assert result == test_controller

    # Verify the cache was used (no controllers should be registered on the app controller)
    assert len(email_app_controller.graph.controllers) == 0


def test_get_email_controller_filters_non_email_controllers(
    email_app_controller: AppController, config: EmailConfig
):
    """Test that get_email_controller only caches EmailControllerBase instances."""
    from mountaineer import ControllerBase
    from mountaineer.render import RenderBase

    class NonEmailController(ControllerBase):
        url = "/test"
        view_path = "/test/page.tsx"  # Add required view_path

        async def render(self) -> RenderBase:
            return RenderBase()

    # Create and register controllers
    test_controller = SampleEmailController()
    non_email_controller = NonEmailController()

    email_app_controller.register(test_controller)
    email_app_controller.register(non_email_controller)

    # Get registry ID for our email controller
    test_registry_id = controller_to_registry_id(SampleEmailController)

    # Call get_email_controller
    result = get_email_controller(test_registry_id, config)

    # Verify the result
    assert result == test_controller

    # Verify only the EmailControllerBase was cached
    import mountaineer_email.registry as registry_module

    assert registry_module.EMAIL_CONTROLLER_CACHE is not None
    assert len(registry_module.EMAIL_CONTROLLER_CACHE) == 1
    assert registry_module.EMAIL_CONTROLLER_CACHE[test_registry_id] == test_controller


def test_get_email_controller_raises_key_error_for_missing_controller(
    email_app_controller: AppController, config: EmailConfig
):
    """Test that get_email_controller raises KeyError for non-existent registry ID."""
    # Don't register any controllers

    # Try to get a non-existent controller
    with pytest.raises(KeyError):
        get_email_controller("non_existent_id", config)
