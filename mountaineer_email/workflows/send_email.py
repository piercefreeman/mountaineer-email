from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import timedelta
from inspect import isclass
from typing import Any, Generic, TypeVar, cast

from pydantic import BaseModel, EmailStr, field_validator, model_validator
from waymark import Depend, RetryPolicy, Workflow, action, workflow

from mountaineer.config import get_config
from mountaineer.dependencies import get_function_dependencies
from mountaineer_cloud.primitives import EmailBody, EmailMessage, EmailRecipient
from mountaineer_cloud.providers.definition import resolve_cloud_by_config
from mountaineer_cloud.providers_common.email import EmailProviderCore

from mountaineer_email.controller import EmailControllerBase
from mountaineer_email.registry import (
    SerializedEmailController,
    deserialize_controller,
    deserialize_controller_class,
    serialize_controller,
)

RenderInput = TypeVar("RenderInput", bound=BaseModel)


def _get_controller_input_model(
    controller: SerializedEmailController[Any],
) -> type[BaseModel]:
    controller_cls = deserialize_controller_class(controller)
    _, input_model = controller_cls().get_input_model()
    return input_model


def _specialize_send_email_input_model(
    input_model: type[BaseModel],
) -> type["SendEmailInput[Any]"]:
    return cast(type[SendEmailInput[Any]], cast(Any, SendEmailInput)[input_model])


class SendEmailInput(BaseModel, Generic[RenderInput]):
    email_controller: SerializedEmailController[RenderInput]
    email_input: RenderInput
    to_email: EmailStr
    to_name: str | None = None
    from_email: EmailStr
    from_name: str | None = None

    @field_validator("email_controller", mode="before")
    @classmethod
    def serialize_email_controller_reference(cls, value: Any) -> Any:
        if (isclass(value) and issubclass(value, EmailControllerBase)) or isinstance(
            value, EmailControllerBase
        ):
            return serialize_controller(value)

        return value

    @model_validator(mode="after")
    def validate_email_input_matches_controller(self) -> "SendEmailInput[RenderInput]":
        input_model = _get_controller_input_model(self.email_controller)
        if isinstance(self.email_input, input_model):
            return self

        self.email_input = cast(
            RenderInput,
            input_model.model_validate(self.email_input.model_dump(mode="json")),
        )
        return self

    @classmethod
    def from_controller_input(
        cls,
        controller: type[EmailControllerBase[RenderInput]]
        | EmailControllerBase[RenderInput],
        *,
        email_input: RenderInput,
        to_email: str,
        to_name: str | None = None,
        from_email: str,
        from_name: str | None = None,
    ) -> "SendEmailInput[RenderInput]":
        payload_cls = cast(
            type[SendEmailInput[RenderInput]],
            _specialize_send_email_input_model(email_input.__class__),
        )
        return payload_cls.model_validate(
            {
                "email_controller": controller,
                "email_input": email_input,
                "to_email": to_email,
                "to_name": to_name,
                "from_email": from_email,
                "from_name": from_name,
            }
        )

    @classmethod
    def from_email_input(
        cls,
        controller: type[EmailControllerBase[RenderInput]]
        | EmailControllerBase[RenderInput],
        *,
        email_input: RenderInput,
        to_email: str,
        to_name: str | None = None,
        from_email: str,
        from_name: str | None = None,
    ) -> "SendEmailInput[RenderInput]":
        return cls.from_controller_input(
            controller,
            email_input=email_input,
            to_email=to_email,
            to_name=to_name,
            from_email=from_email,
            from_name=from_name,
        )

    @classmethod
    def from_serialized_input(
        cls,
        *,
        email_controller: SerializedEmailController[Any],
        email_input: BaseModel | dict[str, Any],
        to_email: str,
        to_name: str | None = None,
        from_email: str,
        from_name: str | None = None,
    ) -> "SendEmailInput[Any]":
        input_model = _get_controller_input_model(email_controller)
        payload_cls = _specialize_send_email_input_model(input_model)
        return payload_cls.model_validate(
            {
                "email_controller": email_controller,
                "email_input": email_input,
                "to_email": to_email,
                "to_name": to_name,
                "from_email": from_email,
                "from_name": from_name,
            }
        )


class ConstructedEmail(BaseModel):
    to_email: EmailStr
    to_name: str | None = None
    from_email: EmailStr
    from_name: str | None = None
    subject: str
    html_body: str


class SendEmailResult(BaseModel):
    message_id: str


async def get_email_core() -> AsyncGenerator[EmailProviderCore[Any], None]:
    config = get_config()
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
    return


@action
async def construct_email(
    email_controller: SerializedEmailController[Any],
    email_input: BaseModel | dict[str, Any],
    to_email: str,
    from_email: str,
    to_name: str | None = None,
    from_name: str | None = None,
) -> ConstructedEmail:
    payload = SendEmailInput.from_serialized_input(
        email_controller=email_controller,
        email_input=email_input,
        to_email=to_email,
        to_name=to_name,
        from_email=from_email,
        from_name=from_name,
    )
    controller_instance = deserialize_controller(payload.email_controller)
    rendered_email = await controller_instance.render_obj(payload.email_input)

    return ConstructedEmail(
        to_email=payload.to_email,
        to_name=payload.to_name,
        from_email=payload.from_email,
        from_name=payload.from_name,
        subject=rendered_email.subject,
        html_body=rendered_email.html_body,
    )


@action
async def send_constructed_email(
    payload: ConstructedEmail,
    core: EmailProviderCore[Any] = Depend(get_email_core),  # type: ignore[assignment]
) -> SendEmailResult:
    message = EmailMessage[Any](
        sender=EmailRecipient(
            email=str(payload.from_email),
            display_name=payload.from_name,
        ),
        recipient=EmailRecipient(
            email=str(payload.to_email),
            display_name=payload.to_name,
        ),
        subject=payload.subject,
        body=EmailBody(html=payload.html_body),
    )
    message_id = await message.send(core)
    return SendEmailResult(message_id=message_id)


@workflow
class SendEmail(Workflow):
    async def run(
        self,
        email_controller: SerializedEmailController[Any],
        email_input: BaseModel | dict[str, Any],
        to_email: str,
        from_email: str,
        to_name: str | None = None,
        from_name: str | None = None,
    ) -> SendEmailResult:
        constructed_email = await self.run_action(
            construct_email(
                email_controller=email_controller,
                email_input=email_input,
                to_email=to_email,
                to_name=to_name,
                from_email=from_email,
                from_name=from_name,
            ),
            retry=RetryPolicy(attempts=2, backoff_seconds=1),
            timeout=timedelta(seconds=60),
        )

        return await self.run_action(
            send_constructed_email(constructed_email),
            retry=RetryPolicy(attempts=3, backoff_seconds=5),
            timeout=timedelta(seconds=60),
        )
