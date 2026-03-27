from mountaineer import ConfigBase
from iceaxe.mountaineer import DatabaseConfig
from pydantic_settings import SettingsConfigDict

class AppConfig(ConfigBase, DatabaseConfig):
    PACKAGE: str | None = "example_app"

    model_config = SettingsConfigDict(env_file=(".env",))