from pydantic import Field, HttpUrl, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    dev_mode: bool = Field(default=False)
    log_file: str | None = Field(default="./logs/bifrons.log")
    log_level: str = Field(default="warn")
    keycloak_server: HttpUrl = HttpUrl("http://localhost:8080")
    keycloak_client: str = "cctracker_server"
    keycloak_realm: str = "cctracker"
    keycloak_key: str = "cctracker-secret-key"
    db_conn_string: PostgresDsn = PostgresDsn("postgresql+asyncpg://webserver_user:cctracker_pass@localhost:5432/cctracker")
    dev_db: bool = Field(default=False)
    valkey_url: str = "valkey://localhost:6379"
    minio_url: str = "localhost:9000"
    minio_access_key: str = "2ZH021DFCBKYQ7AOR01R"
    minio_secret_key: str = "1Yh1M+VF5nKhMTppH4ezE2gqLTk6z0RrgeYNmyJU"
    minio_bucket: str = "cctracker"
    signing_key: str = "TheItsDangerousSigningKey"


config = Settings()
