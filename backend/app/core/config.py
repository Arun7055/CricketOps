from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    DATABASE_URL: str = Field(..., validation_alias="DATABASE_URL")
    GROQ_API_KEY: str = Field(..., validation_alias="GROQ_API_KEY")
    RABBITMQ_URL: str

    # Fixed: Swapped SettingsConfigForm out for SettingsConfigDict
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()