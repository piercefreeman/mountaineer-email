from mountaineer import ConfigBase
from mountaineer_cloud.aws.config import AWSConfig  # ty: ignore[unresolved-import]

from mountaineer_email.config import EmailConfig


class AppConfig(EmailConfig, AWSConfig, ConfigBase):
    pass
