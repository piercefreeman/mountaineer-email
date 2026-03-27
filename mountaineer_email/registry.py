from typing import TYPE_CHECKING, Type, overload

from mountaineer import CoreDependencies

from mountaineer_email.controller import EmailControllerBase

if TYPE_CHECKING:
    from mountaineer_email.config import EmailConfig


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


@overload
def get_email_controller(registry_id: str) -> "EmailControllerBase": ...


@overload
def get_email_controller(
    registry_id: str, config: "EmailConfig"
) -> "EmailControllerBase": ...


def get_email_controller(registry_id: str, config: "EmailConfig | None" = None):
    """
    Returns the email controller of the given type.

    """
    global EMAIL_CONTROLLER_CACHE

    # If no config provided, try to get it from dependencies and use instance registry
    if config is None:
        if registry_id in INSTANCE_REGISTRY:
            return INSTANCE_REGISTRY[registry_id]

        # Try to get config from dependencies
        try:
            from mountaineer_email.config import EmailConfig

            config = CoreDependencies.get_config_with_type(EmailConfig)()
        except Exception:
            raise ValueError(
                f"No config provided and could not get config from dependencies for registry_id: {registry_id}"
            )

    if EMAIL_CONTROLLER_CACHE is None:
        EMAIL_CONTROLLER_CACHE = {}

        # Create a new AppController to house the cached email controllers
        # that are mounted
        cached_app_controller = config.EMAIL_CONTROLLER_CONTEXT()

        for controller_definition in cached_app_controller.graph.controllers:
            if isinstance(controller_definition.controller, EmailControllerBase):
                controller_registry_id = controller_to_registry_id(
                    controller_definition.controller.__class__
                )
                EMAIL_CONTROLLER_CACHE[controller_registry_id] = (
                    controller_definition.controller
                )

    return EMAIL_CONTROLLER_CACHE[registry_id]


def register_email_controller(controller: Type["EmailControllerBase"]) -> None:
    """
    Register an email controller instance in the instance registry.
    This is used for testing and daemon workflows.

    """
    registry_id = controller_to_registry_id(controller)
    INSTANCE_REGISTRY[registry_id] = controller()
    # Also register the class
    register_email_controller_class(controller)


def clear_email_controller_cache():
    """
    Clears the email controller cache and forces a re-build of the cache.

    """
    global EMAIL_CONTROLLER_CACHE
    EMAIL_CONTROLLER_CACHE = None


def clear_email_registry():
    """
    Clears the email registry. Used for testing.

    """
    global EMAIL_CONTROLLER_CACHE
    EMAIL_CONTROLLER_CACHE = None
    INSTANCE_REGISTRY.clear()
    EMAIL_CLASS_REGISTRY.clear()
