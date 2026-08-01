from mountaineer.app import AppController
from mountaineer.render import LinkAttribute, Metadata

from example_app.config import AppConfig
from example_app.controllers.home import HomeController
from example_app.emails import WelcomePreviewEmail
from mountaineer_email.plugin import plugin as email_plugin

controller = AppController(
    config=AppConfig(),  # type: ignore
    global_metadata=Metadata(
        links=[LinkAttribute(rel="stylesheet", href="/static/app_main.css")],
    ),
)


controller.register(HomeController())
controller.register(email_plugin)
controller.register(WelcomePreviewEmail())
