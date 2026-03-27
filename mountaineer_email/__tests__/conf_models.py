from mountaineer import ConfigBase

from mountaineer_email.config import EmailConfig


class AppConfig(EmailConfig, ConfigBase):
    pass
