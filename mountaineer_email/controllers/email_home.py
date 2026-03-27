from fastapi import Request
from inflection import underscore
from pydantic import BaseModel

from mountaineer import (
    ControllerBase,
    LinkAttribute,
    ManagedViewPath,
    Metadata,
    RenderBase,
)

from mountaineer_email.controller import EmailControllerBase
from mountaineer_email.registry import get_registered_email_controllers
from mountaineer_email.views import get_email_view_path


class EmailDefinition(BaseModel):
    short_name: str
    full_name: str


class EmailHomeRender(RenderBase):
    emails: list[EmailDefinition] = []


class EmailHomeController(ControllerBase):
    url = "/admin/email/"
    view_path = (
        ManagedViewPath.from_view_root(get_email_view_path(""), package_root_link=None)
        / "email/home/page.tsx"
    )

    async def render(
        self,
        request: Request,
    ) -> EmailHomeRender:
        # Find all emails registered with the registry
        registered_controllers = get_registered_email_controllers()
        emails = [
            EmailDefinition(
                short_name=underscore(email_cls.__name__),
                full_name=email_cls.__name__,
            )
            for email_cls in registered_controllers.values()
            if issubclass(email_cls, EmailControllerBase)
        ]

        return EmailHomeRender(
            emails=emails,
            metadata=Metadata(
                title="Email | Home",
                links=[
                    LinkAttribute(
                        rel="stylesheet", href=f"{self._scripts_prefix}/email_main.css"
                    ),
                ],
                ignore_global_metadata=True,
            ),
        )
