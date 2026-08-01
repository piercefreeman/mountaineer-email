from mountaineer.plugin import MountaineerPlugin

from mountaineer_email import controllers
from mountaineer_email.views import get_email_view_path

plugin = MountaineerPlugin(
    name="mountaineer-email",
    controllers=[
        controllers.EmailHomeController,
        controllers.EmailDetailController,
    ],
    view_root=get_email_view_path(""),
)
