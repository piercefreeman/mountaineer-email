from typing import Callable

from pydantic_settings import BaseSettings

from mountaineer.app import AppController


class EmailConfig(BaseSettings):
    # Full email address account@example.com
    EMAIL_SENDER_ADDRESS: str

    # Name that appears in the "From" line
    EMAIL_SENDER_NAME: str

    # Context that we can use to customize the emails and mount our supported plugins
    EMAIL_CONTROLLER_CONTEXT: Callable[[], AppController]
