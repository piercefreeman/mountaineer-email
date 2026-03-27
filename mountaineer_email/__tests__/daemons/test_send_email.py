import pytest
from pydantic import BaseModel
from waymark import provide_dependencies  # ty: ignore[unresolved-import]

from mountaineer_cloud.test_utilities import MockAWS

from mountaineer_email.__tests__.conf_models import AppConfig
from mountaineer_email.controller import EmailControllerBase
from mountaineer_email.daemons.send_email import (
    SendEmailInput,
    render_email,
    send_email,
)
from mountaineer_email.registry import register_email_controller
from mountaineer_email.render import EmailMetadata, EmailRenderBase, FilledOutEmail


class MockEmailInput(BaseModel):
    pass


class MockEmailRender(EmailRenderBase):
    pass


class MockEmailController(EmailControllerBase[MockEmailInput]):
    async def render(self, payload: MockEmailInput) -> MockEmailRender:
        return MockEmailRender(
            email_metadata=EmailMetadata(
                to_email="mock@example.com", subject="MOCK_SUBJECT"
            )
        )

    async def _generate_email(self, *args, **kwargs) -> FilledOutEmail:
        # Stub out value so we can test the workflow without having
        # to test the email flows
        return FilledOutEmail(
            to_email="mock@example.com",
            subject="MOCK_SUBJECT",
            html_body="MOCK_BODY",
        )


@pytest.mark.asyncio
async def test_render_email_action(config: AppConfig):
    """Test the render_email action individually."""
    # Make sure it's registered. This usually happens on __init_subclass__ but our
    # test harness clears the registry state between tests
    register_email_controller(MockEmailController)

    # Build the input
    email_input = SendEmailInput.from_email_input(
        controller=MockEmailController,
        email_input=MockEmailInput(),
    )

    # Test the render_email action with provide_dependencies
    async with provide_dependencies(render_email, {"payload": email_input}) as deps:
        result = await render_email(**deps)

    # Verify the rendered email
    assert result.to_email == "mock@example.com"
    assert result.subject == "MOCK_SUBJECT"
    assert result.html_body == "MOCK_BODY"


@pytest.mark.asyncio
async def test_send_email_action(mock_aws: MockAWS, config: AppConfig):
    """Test the send_email action individually."""
    # Verify the email address in the mock SES environment before sending so we don't
    # get rejected by the mocked API
    await mock_aws.mock_ses.verify_email_identity(EmailAddress="mock@example.com")
    await mock_aws.mock_ses.verify_email_identity(EmailAddress="test@example.com")

    # Create the rendered email to send
    rendered_email = FilledOutEmail(
        to_email="mock@example.com",
        subject="MOCK_SUBJECT",
        html_body="MOCK_BODY",
    )

    # Test the send_email action with provide_dependencies
    async with provide_dependencies(
        send_email,
        {
            "payload": rendered_email,
            "config": config,
            "aws_session": mock_aws.session,
        },
    ) as deps:
        result = await send_email(**deps)

    # Verify the result
    assert result.success is True
    assert result.message_id is not None

    # Verify the email was sent by checking SES statistics
    send_statistics = await mock_aws.mock_ses.get_send_statistics()
    assert len(send_statistics["SendDataPoints"]) > 0
