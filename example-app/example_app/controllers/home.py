from fastapi.responses import RedirectResponse
from starlette import status

from mountaineer import ControllerBase, Metadata, RenderBase


class HomeRender(RenderBase):
    pass


class HomeController(ControllerBase):
    url = "/"
    view_path = "/app/home/page.tsx"

    async def render(self) -> HomeRender:
        return HomeRender(
            metadata=Metadata(
                title="Email Preview",
                explicit_response=RedirectResponse(
                    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                    url="/admin/email/",
                ),
            ),
        )
