from typing import Callable, TypeVar, cast

from mountaineer_email.controller import EmailControllerBase
from mountaineer_email.registry import deserialize_controller, serialize_controller

EmailControllerType = TypeVar("EmailControllerType", bound=EmailControllerBase)


def get_email_template(
    controller: type[EmailControllerType],
) -> Callable[[], EmailControllerType]:
    """
    Resolve a fresh typed email controller instance for dependency injection.

    """

    def dependency() -> EmailControllerType:
        serialized_controller = serialize_controller(controller)
        return cast(EmailControllerType, deserialize_controller(serialized_controller))

    return dependency
