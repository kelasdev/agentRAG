from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    qdrant_url: str = Field(alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    collection_name: str = Field(default="agentrag_memory", alias="COLLECTION_NAME")
    default_top_k_memory_query: int = Field(default=3, alias="DEFAULT_TOP_K_MEMORY_QUERY")

    embedding_provider: str = Field(default="fastembed", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(
        default="jinaai/jina-embeddings-v2-base-code", alias="EMBEDDING_MODEL"
    )
    llama_cpp_embed_model_path: str | None = Field(default=None, alias="LLAMA_CPP_EMBED_MODEL_PATH")
    llama_cpp_n_threads: int = Field(default=4, alias="LLAMA_CPP_N_THREADS")
    openai_compatible_base_url: str | None = Field(
        default=None, alias="OPENAI_COMPATIBLE_BASE_URL"
    )
    openai_compatible_api_key: str | None = Field(
        default=None, alias="OPENAI_COMPATIBLE_API_KEY"
    )
    embedding_request_timeout_seconds: float = Field(
        default=30.0, alias="EMBEDDING_REQUEST_TIMEOUT_SECONDS"
    )
    enable_dimension_preflight: bool = Field(default=True, alias="ENABLE_DIMENSION_PREFLIGHT")
    jina_reader_base_url: str = Field(default="https://r.jina.ai/", alias="JINA_READER_BASE_URL")
    web_fetch_timeout_seconds: float = Field(default=45.0, alias="WEB_FETCH_TIMEOUT_SECONDS")

    final_top_k: int = Field(default=3, alias="FINAL_TOP_K")


def get_settings() -> Settings:
    return Settings()
