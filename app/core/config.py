from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    GEMINI_API_KEY: str = Field(..., validation_alias="GEMINI_API_KEY")
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    CHROMA_DB_PATH: str = "./chroma_db"
    DATABASE_URL: str = "sqlite:///./incidents.db"


    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
