from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HelioScan"
    environment: str = "development"
    log_level: str = "INFO"
    nominatim_min_interval_seconds: float = Field(default=1.0, ge=1.0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
