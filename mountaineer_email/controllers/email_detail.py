from json import loads as json_loads
from typing import cast

from fastapi import Request
from inflection import underscore
from lxml.html import fromstring as html_fromstring, tostring as html_tostring
from pydantic import BaseModel

from mountaineer import (
    ControllerBase,
    LinkAttribute,
    ManagedViewPath,
    Metadata,
    RenderBase,
)

from mountaineer_email.controller import (
    EmailControllerBase,
    FilledOutEmail,
)
from mountaineer_email.registry import get_registered_email_controllers
from mountaineer_email.views import get_email_view_path


class SimpleSchemaField(BaseModel):
    field_name: str
    required: bool


class SimpleSchema(BaseModel):
    title: str
    fields: list[SimpleSchemaField]


class EmailDetailRender(RenderBase):
    email_short: str
    render_json_schema: SimpleSchema | None

    # If mock body values are provided, the user wants to render
    # the email with those values
    mock_body_echo: dict[str, str] | None
    rendered: FilledOutEmail | None
    exception: str | None


class EmailDetailController(ControllerBase):
    """
    Show a preview of the email and lets admins render examples. Assumes:
    - The render() either has one BaseModel doesn't have any BaseModel

    """

    url = "/admin/email/{email_short}"
    view_path = (
        ManagedViewPath.from_view_root(get_email_view_path(""), package_root_link=None)
        / "email/detail/page.tsx"
    )

    def __init__(self):
        super().__init__()

    async def render(
        self,
        request: Request,
        email_short: str,
        mock_body: str | None = None,
    ) -> EmailDetailRender:
        """
        Render the given email, optionally with mocked body values that will
        be used to populate the email. We use a GET parameter to serialize this body
        request to allow clients to auto-refresh the email preview as the contents
        change without losing their seed variables on reload.

        """
        email = self.get_email(email_short)
        variable_key, variable_input = email.get_input_model()
        simple_schema: SimpleSchema | None = None

        mock_body_echo: dict[str, str] | None = None
        rendered: FilledOutEmail | None = None
        exception: str | None = None

        # If this email body accepts a parameter input, return the JSON schema
        # to clients so we can show the field inputs
        if variable_input:
            json_schema = variable_input.model_json_schema()
            simple_schema = SimpleSchema(
                title=json_schema["title"],
                fields=[
                    SimpleSchemaField(
                        field_name=property_name,
                        required=property_name in json_schema.get("required", []),
                    )
                    for property_name, property in json_schema["properties"].items()
                ],
            )

        # If the mock body was provided, try to parse it as our schema
        # Otherwise the user hasn't submitted a body request yet
        if mock_body:
            try:
                mock_body_echo = json_loads(mock_body)
                parsed_email_body = (
                    variable_input.model_validate(mock_body_echo)
                    if variable_input
                    else None
                )
                # Our wrapped render will be async, even if the render() method
                rendered = await email._generate_email_with_request(
                    request,
                    **({variable_key: parsed_email_body} if variable_key else {}),
                )

                # Re-parse the HTML to make it more readable
                rendered.html_body = html_tostring(
                    html_fromstring(rendered.html_body), pretty_print=True
                )
            except Exception as e:
                exception = str(e)

        return EmailDetailRender(
            email_short=email_short,
            render_json_schema=simple_schema,
            mock_body_echo=mock_body_echo,
            rendered=rendered,
            exception=exception,
            metadata=Metadata(
                title=f"Email | {email.__class__.__name__}",
                links=[
                    LinkAttribute(
                        rel="stylesheet", href=f"{self._scripts_prefix}/email_main.css"
                    ),
                ],
                ignore_global_metadata=True,
            ),
        )

    def get_email(self, email_short: str) -> EmailControllerBase:
        # Emails need to be registered to the email registry to be rendered by our
        # backend workers. We check for them here, parameterized by their short identifier
        registered_controllers = get_registered_email_controllers()
        emails = [
            email_cls
            for email_cls in registered_controllers.values()
            if (
                issubclass(email_cls, EmailControllerBase)
                and underscore(email_cls.__name__) == email_short
            )
        ]

        if not emails:
            raise ValueError(f"Email {email_short} not found")

        # For the view itself we rely on the entities registered to the AppController so we can
        # invalidate their SSR code and re-render when changes happen on disk. The daemon workflow is
        # intended to just be used with on-disk compiled files.
        if not self._definition:
            raise ValueError(
                f"Linked controller definition for {email_short} not found"
            )

        email_cls = emails[0]
        definitions = self._definition.graph.get_definitions_for_cls(email_cls)
        if not definitions:
            raise ValueError(
                f"Linked controller definition for {email_short} not found"
            )

        return cast(EmailControllerBase, definitions[0].controller)
