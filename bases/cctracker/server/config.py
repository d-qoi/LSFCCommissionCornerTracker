from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    log_file: str | None = Field(alias="log", default="./logs/bifrons.log")
    log_level: str = Field(alias="level", default="warn")


config = Settings()
