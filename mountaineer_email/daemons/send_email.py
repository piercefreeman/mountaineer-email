from datetime import timedelta
from typing import Any, Type, TypeVar

import aioboto3
from pydantic import BaseModel
from waymark import (  # ty: ignore[unresolved-import]
    Depend,
    RetryPolicy,
    Workflow,
    action,
    workflow,
)

from mountaineer import CoreDependencies
from mountaineer_cloud.aws import AWSDependencies  # ty: ignore[unresolved-import]

from mountaineer_email.config import EmailConfig
from mountaineer_email.controller import EmailControllerBase
from mountaineer_email.registry import controller_to_registry_id, get_email_controller
from mountaineer_email.render import FilledOutEmail

RenderInput = TypeVar("RenderInput", bound=BaseModel)


class SendEmailInput(BaseModel):
    # Store as a dictionary instead of a FilledOutEmail, since we need to support
    # different types and re-hydrate these in the background daemon
    # BaseModel by default doesn't serialize with dynamic typing
    # See `model_dump_recursive` for a workaround (but since we control the creation
    # of this method we can just dump to a dict early)
    email_input: dict[str, Any]
    registry_id: str

    @classmethod
    def from_email_input(
        cls,
        controller: Type[EmailControllerBase[RenderInput]],
        *,
        email_input: RenderInput,
    ):
        return cls(
            email_input=email_input.model_dump(),
            registry_id=controller_to_registry_id(controller),
        )


class SendEmailResponse(BaseModel):
    success: bool
    message_id: str | None = None
    permanent_failure: str | None = None


@workflow
class SendEmail(Workflow):
    """
    Given a rendered email `FilledOutEmail` output of an EmailController, sends
    the email through SES. Non-permanent errors about account status or quotas will
    be retried since the underlying email payload is valid. Permanent errors like a malformed
    email will be terminated since the problematic payload will never be modified in the
    backoff loop.

    Make sure your account is configured correctly. Quoting from the AWS docs:

    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ses/client/send_email.html

    - The message must be sent from a verified email address or domain. If you attempt
        to send email using a non-verified address or domain, the operation results in
        an "Email address not verified" error.
    - If your account is still in the Amazon SES sandbox, you may only send to verified addresses
        or domains, or to email addresses associated with the Amazon SES Mailbox Simulator. For more
        information, see Verifying Email Addresses and Domains in the Amazon SES Developer Guide.
    - The maximum message size is 10 MB.
    - The message must include at least one recipient email address. The recipient address can be a To: address,
        a CC: address, or a BCC: address. If a recipient email address is invalid (that is, it is not in the format
        UserName@[SubDomain.]Domain.TopLevelDomain), the entire message is rejected, even if the message contains other
        recipients that are valid.

    """

    async def run(  # type: ignore[override]
        self,
        *args,
        email_input: dict[str, Any],
        registry_id: str,
        **kwargs,
    ) -> None:
        request = SendEmailInput(email_input=email_input, registry_id=registry_id)

        rendered_email = await self.run_action(
            render_email(request),
            retry=RetryPolicy(attempts=3, backoff_seconds=5),
            timeout=timedelta(seconds=60),
        )

        success_response = await self.run_action(
            send_email(rendered_email),
            retry=RetryPolicy(attempts=3, backoff_seconds=5),
            timeout=timedelta(seconds=60),
        )
        if not success_response.success:
            raise Exception(
                f"Permanent email failure: {success_response.permanent_failure}"
            )


@action
async def render_email(payload: SendEmailInput) -> FilledOutEmail:
    # Hydrated / instantiated email controller
    email_controller = get_email_controller(payload.registry_id)
    _, email_model = email_controller.get_input_model()
    email_input = email_model.model_validate(payload.email_input)

    return await email_controller._generate_email(email_input)


def get_email_config():
    """Dependency provider for EmailConfig."""
    return CoreDependencies.get_config_with_type(EmailConfig)()


def get_aws_session():
    """Dependency provider for AWS session."""
    return AWSDependencies.get_aws_session()


@action
async def send_email(
    payload: FilledOutEmail,
    config: EmailConfig = Depend(get_email_config),  # type: ignore[assignment]
    aws_session: aioboto3.Session = Depend(get_aws_session),  # type: ignore[assignment]
) -> SendEmailResponse:
    async with aws_session.client("ses") as client:
        # Construct the email
        try:
            response = await client.send_email(
                Source=f"{config.EMAIL_SENDER_NAME} <{config.EMAIL_SENDER_ADDRESS}>",
                Destination={
                    "ToAddresses": [
                        payload.to_email,
                    ],
                },
                Message={
                    "Subject": {
                        "Data": payload.subject,
                    },
                    "Body": {
                        "Html": {
                            "Data": payload.html_body,
                        },
                    },
                },
            )
        except client.exceptions.MessageRejected as e:
            # Permanent failure - return back to the client
            # For any others, we let them raise and get auto-retried
            return SendEmailResponse(
                success=False,
                permanent_failure=e.response["Error"]["Message"],
            )

    return SendEmailResponse(success=True, message_id=response["MessageId"])
