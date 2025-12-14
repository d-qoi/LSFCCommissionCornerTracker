from pydantic import Field, HttpUrl, PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_file: str | None = Field(alias="log", default="./logs/bifrons.log")
    log_level: str = Field(alias="level", default="warn")
    keycloak_server: HttpUrl = HttpUrl("https://keycloak")
    keycloak_client: str = "cctracker_server"
    keycloak_realm: str = "cctracker"
    keycloak_key: str = "cctracker-secret-key"
    db_conn_string: PostgresDsn = PostgresDsn("postgresql+asyncpg://webserver_user:cctracker_pass@db:5432/cctracker")
    valkey_url: str = "valkey"
    minio_url: str = "minio"
    minio_access_key: str = "2ZH021DFCBKYQ7AOR01R"
    minio_secret_key: str = "1Yh1M+VF5nKhMTppH4ezE2gqLTk6z0RrgeYNmyJU"
    minio_bucket: str = "cctracker"
    signing_key: str = "TheItsDangerousSigningKey"


config = Settings()
