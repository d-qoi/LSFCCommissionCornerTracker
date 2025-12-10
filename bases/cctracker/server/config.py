from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_file: str | None = Field(alias="log", default="./logs/bifrons.log")
    log_level: str = Field(alias="level", default="warn")
    keycloak_server: HttpUrl = HttpUrl("https://keycloak")
    keycloak_client: str = "cctracker_server"
    keycloak_realm: str = "cctracker"
    keycloak_key: str = "cctracker-secret-key"


config = Settings()
