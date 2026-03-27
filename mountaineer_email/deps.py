from typing import Callable, TypeVar, cast

from mountaineer_email.controller import EmailControllerBase
from mountaineer_email.registry import controller_to_registry_id, get_email_controller

EmailControllerType = TypeVar("EmailControllerType", bound=EmailControllerBase)


def get_email_template(
    controller: type[EmailControllerType],
) -> Callable[[], EmailControllerType]:
    """
    Resolve a typed email controller instance from the registry for dependency injection.

    """

    def dependency() -> EmailControllerType:
        registry_id = controller_to_registry_id(controller)
        return cast(EmailControllerType, get_email_controller(registry_id))

    return dependency
