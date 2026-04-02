from __future__ import annotations

from datetime import timedelta
from inspect import isclass
from typing import Any, Generic, TypeVar, cast

from pydantic import BaseModel, EmailStr, field_validator, model_validator
from waymark import Depend, RetryPolicy, Workflow, action, workflow

from mountaineer_cloud.primitives import EmailBody, EmailMessage, EmailRecipient
from mountaineer_cloud.providers_common.email import EmailProviderCore

from mountaineer_email.controller import EmailControllerBase
from mountaineer_email.deps import get_email_core
from mountaineer_email.registry import (
    SerializedEmailController,
    deserialize_controller,
    deserialize_controller_class,
    serialize_controller,
)

RenderInput = TypeVar("RenderInput", bound=BaseModel)

#
# Workflow
#


class SendEmailInput(BaseModel, Generic[RenderInput]):
    """
    Portable payload for handing email rendering off to backend workflows.

    The main app can fully mount email controllers into the Mountaineer graph and
    resolve their asset paths on disk, but the background workflow process does
    not have that graph available. We therefore serialize both the controller
    identity and its known on-disk locations so the workflow can reload the
    controller module and render with the same resolved assets later.
    """

    email_controller: (
        SerializedEmailController[RenderInput]
        | type[EmailControllerBase[RenderInput]]
        | EmailControllerBase[RenderInput]
    )
    email_input: RenderInput | BaseModel | dict[str, Any]
    to_email: EmailStr
    to_name: str | None = None
    from_email: EmailStr
    from_name: str | None = None

    @field_validator("email_controller", mode="before")
    @classmethod
    def serialize_email_controller_reference(cls, value: Any) -> Any:
        """Normalize controller inputs into a serialized controller payload."""
        return _normalize_email_controller_reference(value)

    @model_validator(mode="after")
    def validate_email_input_matches_controller(self) -> "SendEmailInput[RenderInput]":
        """Coerce `email_input` into the controller's declared input model."""
        serialized_controller = _normalize_email_controller_reference(
            self.email_controller
        )
        self.email_controller = serialized_controller
        input_model = _get_controller_input_model(serialized_controller)
        if isinstance(self.email_input, input_model):
            return self

        if isinstance(self.email_input, BaseModel):
            raw_input = self.email_input.model_dump(mode="json")
        else:
            raw_input = self.email_input

        self.email_input = cast(
            RenderInput,
            input_model.model_validate(raw_input),
        )
        return self


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


#
# Actions
#


class ConstructedEmail(BaseModel):
    to_email: EmailStr
    to_name: str | None = None
    from_email: EmailStr
    from_name: str | None = None
    subject: str
    html_body: str


class SendEmailResult(BaseModel):
    message_id: str


@action
async def construct_email(
    email_controller: SerializedEmailController[Any],
    email_input: BaseModel | dict[str, Any],
    to_email: str,
    from_email: str,
    to_name: str | None = None,
    from_name: str | None = None,
) -> ConstructedEmail:
    """Render an email controller into a concrete email payload."""
    payload = SendEmailInput(
        email_controller=email_controller,
        email_input=email_input,
        to_email=to_email,
        to_name=to_name,
        from_email=from_email,
        from_name=from_name,
    )
    controller_instance = deserialize_controller(
        _normalize_email_controller_reference(payload.email_controller)
    )
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
    core: EmailProviderCore[Any] = Depend(get_email_core),
) -> SendEmailResult:
    """Send a rendered email payload through the configured provider."""
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


#
# Helpers
#


def _normalize_email_controller_reference(
    value: SerializedEmailController[RenderInput]
    | type[EmailControllerBase[RenderInput]]
    | EmailControllerBase[RenderInput],
) -> SerializedEmailController[RenderInput]:
    if (isclass(value) and issubclass(value, EmailControllerBase)) or isinstance(
        value, EmailControllerBase
    ):
        return serialize_controller(value)

    return value


def _get_controller_input_model(
    controller: SerializedEmailController[Any],
) -> type[BaseModel]:
    controller_cls = deserialize_controller_class(controller)
    _, input_model = controller_cls().get_input_model()
    return input_model
