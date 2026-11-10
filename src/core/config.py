from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_user: str = "postgres"
    db_password: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "chronos_flow"

    upload_dir: str = "uploads"
    max_upload_mb: int = 10

    # No default on purpose: the app refuses to start without a secret.
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    # The very first account can always be created; after that registration stays closed unless enabled.
    allow_registration: bool = False

    @property
    def database_url(self) -> URL:
        # URL.create escapes special characters in the password for us.
        return URL.create(
            "postgresql+asyncpg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


settings = Settings()
