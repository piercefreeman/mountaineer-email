from __future__ import annotations

from collections.abc import Iterator
from importlib import import_module
from inspect import isclass
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from mountaineer import ManagedViewPath

from mountaineer_email.controller import (
    HYDRATED_SCRIPTS_PREFIX_ATTR,
    HYDRATED_VIEW_BASE_ATTR,
    EmailControllerBase,
)


class SerializedEmailController(BaseModel):
    module: str
    key: str
    view_root: str | None = None
    scripts_prefix: str | None = None

    model_config = {
        "extra": "forbid",
        "frozen": True,
    }


def _controller_cls(
    controller: type["EmailControllerBase"] | "EmailControllerBase",
) -> type["EmailControllerBase"]:
    if isclass(controller) and issubclass(controller, EmailControllerBase):
        return controller

    return controller.__class__


def _controller_view_root(
    controller: type["EmailControllerBase"] | "EmailControllerBase",
    controller_cls: type["EmailControllerBase"],
) -> str | None:
    if (
        isinstance(controller, EmailControllerBase)
        and controller._view_base_path is not None
    ):
        return str(controller._view_base_path)

    hydrated_view_root = getattr(controller_cls, HYDRATED_VIEW_BASE_ATTR, None)
    if hydrated_view_root is not None:
        return str(hydrated_view_root)

    view_path = getattr(controller_cls, "view_path", None)
    if isinstance(view_path, ManagedViewPath):
        try:
            return str(view_path.get_root_link())
        except ValueError:
            return None

    return None


def _controller_scripts_prefix(
    controller: type["EmailControllerBase"] | "EmailControllerBase",
    controller_cls: type["EmailControllerBase"],
    view_root: str | None,
) -> str | None:
    if (
        isinstance(controller, EmailControllerBase)
        and controller._view_base_path is not None
    ):
        return controller._scripts_prefix

    hydrated_scripts_prefix = getattr(
        controller_cls, HYDRATED_SCRIPTS_PREFIX_ATTR, None
    )
    if hydrated_scripts_prefix is not None:
        return cast(str, hydrated_scripts_prefix)

    if view_root is not None:
        return controller_cls._scripts_prefix

    return None


def _payload_to_registry_key(payload: SerializedEmailController) -> str:
    return f"{payload.module}:{payload.key}"


def _iter_email_controller_classes(
    controller_cls: type["EmailControllerBase"] = EmailControllerBase,
) -> Iterator[type["EmailControllerBase"]]:
    for subclass in controller_cls.__subclasses__():
        yield subclass
        yield from _iter_email_controller_classes(subclass)


def serialize_controller(
    controller: type["EmailControllerBase"] | "EmailControllerBase",
) -> SerializedEmailController:
    """
    Serialize an email controller into a stable import reference.

    """
    controller_cls = _controller_cls(controller)
    view_root = _controller_view_root(controller, controller_cls)
    return SerializedEmailController(
        module=controller_cls.__module__,
        key=controller_cls.__qualname__,
        view_root=view_root,
        scripts_prefix=_controller_scripts_prefix(
            controller, controller_cls, view_root
        ),
    )


def deserialize_controller_class(
    payload: SerializedEmailController,
) -> type["EmailControllerBase"]:
    """
    Resolve an email controller class from a serialized import reference.

    """
    module = import_module(payload.module)
    controller_cls: Any = module

    for key_part in payload.key.split("."):
        if key_part == "<locals>":
            raise ValueError(
                f"Cannot deserialize local controller reference: {payload.key}"
            )
        controller_cls = getattr(controller_cls, key_part)

    if not isclass(controller_cls) or not issubclass(
        controller_cls, EmailControllerBase
    ):
        raise ValueError(
            f"Resolved controller {payload.module}.{payload.key} is not an EmailControllerBase"
        )

    return cast(type["EmailControllerBase"], controller_cls)


def deserialize_controller(payload: SerializedEmailController) -> "EmailControllerBase":
    """
    Instantiate an email controller from a serialized import reference.

    """
    controller = deserialize_controller_class(payload)()

    if payload.scripts_prefix is not None:
        controller._scripts_prefix = payload.scripts_prefix

    if payload.view_root is not None:
        controller.resolve_paths(Path(payload.view_root), force=True)

    return controller


def get_registered_email_controllers() -> dict[str, type["EmailControllerBase"]]:
    """
    Returns all imported email controller classes.

    """
    return {
        _payload_to_registry_key(serialize_controller(controller_cls)): controller_cls
        for controller_cls in _iter_email_controller_classes()
    }


def register_email_controller(controller: type["EmailControllerBase"]) -> None:
    """
    Backwards-compatible helper that instantiates a controller.

    """
    controller()


def clear_email_controller_cache() -> None:
    """
    Backwards-compatible no-op. Email controllers are no longer cached separately.

    """
    return None


def clear_email_registry() -> None:
    """
    Clears per-class hydration state for imported email controllers. Used for testing.

    """
    for controller_cls in _iter_email_controller_classes():
        for attr_name in (HYDRATED_VIEW_BASE_ATTR, HYDRATED_SCRIPTS_PREFIX_ATTR):
            if hasattr(controller_cls, attr_name):
                delattr(controller_cls, attr_name)
