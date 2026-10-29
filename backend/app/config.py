from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://meeting:meeting@localhost:3306/meetings"
    chroma_path: str = "./chroma_data"

    embedding_backend: str = "auto"  # auto | sentence-transformers | hash
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    chunk_words: int = 200
    chunk_overlap_words: int = 40
    top_k: int = 6
    min_similarity: float | None = None

    cors_origins: str = "http://localhost:5173"

    @field_validator("min_similarity", mode="before")
    @classmethod
    def _blank_is_none(cls, v):
        return None if isinstance(v, str) and not v.strip() else v


@lru_cache
def get_settings() -> Settings:
    return Settings()
