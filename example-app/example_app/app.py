from mountaineer.app import AppController
from mountaineer.client_compiler.postcss import PostCSSBundler
from mountaineer.render import LinkAttribute, Metadata


from example_app.controllers.detail import DetailController
from example_app.controllers.home import HomeController

from example_app.config import AppConfig

controller = AppController(
    config=AppConfig(), # type: ignore
    
    global_metadata=Metadata(
        links=[LinkAttribute(rel="stylesheet", href="/static/app_main.css")]
    ),
    custom_builders=[
        PostCSSBundler(),
    ],
    
)


controller.register(HomeController())
controller.register(DetailController())
