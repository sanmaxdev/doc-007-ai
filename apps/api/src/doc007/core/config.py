"""Application settings, loaded from environment variables.

Single source of truth for configuration. Import the cached `settings`
instance (via `get_settings()`) everywhere rather than reading os.environ.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_name: str = "DOC-007-AI"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # ---- Security ----
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ---- CORS (comma-separated) ----
    cors_origins: str = "http://localhost:3000"

    # ---- Database ----
    database_url: str = "postgresql+asyncpg://doc007:doc007@localhost:5432/doc007"

    # ---- Redis / Celery ----
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ---- Qdrant ----
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "doc_chunks"
    vector_dim: int = 1536

    # ---- AI providers (server-side only) ----
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openai/gpt-4o-mini"
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"

    # ---- RAG tuning ----
    chunk_size_tokens: int = 700
    chunk_overlap_tokens: int = 80
    retrieval_top_k: int = 6
    retrieval_min_score: float = 0.25
    # Hybrid retrieval: dense (vector) + lexical (keyword) fused with RRF.
    hybrid_enabled: bool = True
    dense_top_n: int = 20
    lexical_top_n: int = 20
    rrf_k: int = 60

    # ---- Storage ----
    storage_backend: str = "local"
    storage_local_path: str = "/data/uploads"
    max_upload_mb: int = 25

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
