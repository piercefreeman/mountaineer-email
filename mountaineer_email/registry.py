from typing import Type

from mountaineer_email.controller import EmailControllerBase

EMAIL_CONTROLLER_CACHE: dict[str, "EmailControllerBase"] | None = None
INSTANCE_REGISTRY: dict[str, "EmailControllerBase"] = {}

# Simple registry for tracking email controller classes
# Maps registry_id -> controller class
EMAIL_CLASS_REGISTRY: dict[str, Type["EmailControllerBase"]] = {}


def controller_to_registry_id(controller: Type["EmailControllerBase"]) -> str:
    """
    Returns the registry id for the given controller.
    Format: {module}.{class_name}

    """
    return f"{controller.__module__}.{controller.__name__}"


def register_email_controller_class(controller: Type["EmailControllerBase"]) -> None:
    """
    Register an email controller class in the global registry.
    This is called automatically by the EmailControllerMetaclass.

    """
    registry_id = controller_to_registry_id(controller)
    EMAIL_CLASS_REGISTRY[registry_id] = controller


def get_registered_email_controllers() -> dict[str, Type["EmailControllerBase"]]:
    """
    Returns all registered email controller classes.

    """
    return EMAIL_CLASS_REGISTRY.copy()


def get_email_controller(registry_id: str) -> "EmailControllerBase":
    """
    Returns the email controller of the given type.

    """
    return INSTANCE_REGISTRY[registry_id]


def register_email_controller_instance(controller: "EmailControllerBase") -> None:
    """
    Register an email controller instance in the global registry.

    """
    registry_id = controller_to_registry_id(controller.__class__)
    INSTANCE_REGISTRY[registry_id] = controller


def register_email_controller(controller: Type["EmailControllerBase"]) -> None:
    """
    Register an email controller instance in the instance registry.
    This is used for testing and daemon workflows.

    """
    register_email_controller_instance(controller())


def clear_email_controller_cache() -> None:
    """
    Clears the email controller cache.

    """
    global EMAIL_CONTROLLER_CACHE
    EMAIL_CONTROLLER_CACHE = None


def clear_email_registry() -> None:
    """
    Clears the email registry. Used for testing.

    """
    global EMAIL_CONTROLLER_CACHE
    EMAIL_CONTROLLER_CACHE = None
    INSTANCE_REGISTRY.clear()
    EMAIL_CLASS_REGISTRY.clear()
