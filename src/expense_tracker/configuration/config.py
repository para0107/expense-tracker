from functools import cache

from pydantic import BaseModel, PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    url: str


class LogSettings(BaseModel):
    level: str


class AuthSettings(BaseModel):
    jwt_secret_key: SecretStr
    jwt_algorithm: str
    access_token_expire_minutes: PositiveInt
    refresh_token_expire_days: PositiveInt


class CSVImportSettings(BaseModel):
    max_file_size_bytes: PositiveInt


class WorkerSettings(BaseModel):
    recurring_interval_minutes: PositiveInt


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__", env_file=".env")

    database: DatabaseSettings
    log: LogSettings
    auth: AuthSettings
    csv_import: CSVImportSettings
    worker: WorkerSettings


@cache
def get_settings() -> Settings:
    return Settings()
