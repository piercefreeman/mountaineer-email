from collections.abc import AsyncGenerator, Callable
from typing import Any, TypeVar, cast

from mountaineer import CoreDependencies, Depends
from mountaineer.config import ConfigBase
from mountaineer.dependencies import get_function_dependencies
from mountaineer_cloud.providers.definition import resolve_cloud_by_config
from mountaineer_cloud.providers_common.email import EmailProviderCore

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


async def get_email_core() -> AsyncGenerator[EmailProviderCore[Any], None]:
    """
    Resolve the configured email provider core for dependency injection.

    """
    config: ConfigBase = Depends(CoreDependencies.get_config_with_type(ConfigBase))
    matching_providers = resolve_cloud_by_config(config, EmailProviderCore)

    if len(matching_providers) > 1:
        raise TypeError(
            "Config matches multiple email providers. "
            "Email workflows require exactly one configured email provider."
        )
    if not matching_providers:
        raise TypeError(
            "Config must expose exactly one mountaineer-cloud email provider."
        )

    provider = matching_providers[0]
    async with get_function_dependencies(callable=provider.injection_function) as deps:
        async for core in provider.injection_function(**deps):
            yield cast(EmailProviderCore[Any], core)
