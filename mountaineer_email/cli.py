from mountaineer.cli import handle_build

from mountaineer_email.plugin import plugin

app = plugin.to_webserver()


def build():
    handle_build(webcontroller="mountaineer_email.cli:app")
