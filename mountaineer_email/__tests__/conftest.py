from os import environ
from pathlib import Path
from warnings import filterwarnings

import pytest

from mountaineer import AppController, PostCSSBundler

from mountaineer_email.__tests__ import conf_models as models
from mountaineer_email.registry import clear_email_registry as _clear_email_registry


@pytest.fixture
def view_root(tmp_path: Path):
    view_path = tmp_path / "views"
    view_path.mkdir()
    return view_path


@pytest.fixture
def email_app_controller(view_root: Path):
    return AppController(
        view_root=view_root,
    )


@pytest.fixture
def config() -> models.AppConfig:
    return models.AppConfig(
        RESEND_API_KEY="test-api-key",
        RESEND_BASE_URL="https://api.resend.test",
    )


@pytest.fixture
def app_controller(view_root: Path, config: models.AppConfig):
    return AppController(
        view_root=view_root,
        custom_builders=[PostCSSBundler()],
        config=config,
    )


@pytest.fixture(autouse=True)
def clear_email_registry():
    """
    Allow us to re-register controllers with the same name when
    running in the same testing session.

    """
    _clear_email_registry()


@pytest.fixture(autouse=True)
def clear_config():
    """Clear the global config before each test."""
    import mountaineer.config as config_module

    # Store original config
    original_config = config_module.APP_CONFIG

    # Clear for test
    config_module.APP_CONFIG = None

    yield

    # Restore original config
    config_module.APP_CONFIG = original_config


@pytest.fixture(autouse=True)
def enable_async_debug():
    # Allows for easier debugging of our async code
    environ["PYTHONASYNCIODEBUG"] = "1"
    try:
        yield
    finally:
        del environ["PYTHONASYNCIODEBUG"]


@pytest.fixture(autouse=True)
def silence_socket_warnings():
    filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)


@pytest.fixture(autouse=True)
def ignore_httpx_deprecation_warnings():
    # Ignore httpx deprecation warnings until fastapi updates its internal test constructor
    # https://github.com/encode/httpx/blame/master/httpx/_client.py#L678
    filterwarnings("ignore", category=DeprecationWarning, module="httpx.*")
