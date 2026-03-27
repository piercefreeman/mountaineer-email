from mountaineer.client_compiler.postcss import PostCSSBundler
from mountaineer.plugin import BuildConfig, MountaineerPlugin

from mountaineer_email import controllers
from mountaineer_email.views import get_email_view_path

plugin = MountaineerPlugin(
    name="mountaineer-email",
    controllers=[
        controllers.EmailHomeController,
        controllers.EmailDetailController,
    ],
    view_root=get_email_view_path(""),
    build_config=BuildConfig(custom_builders=[PostCSSBundler()]),
)
