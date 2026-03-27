from mountaineer import ConfigBase
from mountaineer_cloud.providers.resend.config import (  # pyright: ignore[reportMissingImports]
    ResendConfig,
)


class AppConfig(ConfigBase, ResendConfig):
    pass
