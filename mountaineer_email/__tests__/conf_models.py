from mountaineer import ConfigBase
from mountaineer_cloud.aws.config import AWSConfig

from mountaineer_email.config import EmailConfig


class AppConfig(EmailConfig, AWSConfig, ConfigBase):
    pass
