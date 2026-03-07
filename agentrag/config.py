from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    qdrant_url: str = Field(alias="QDRANT_URL")
    qdrant_api_key: str = Field(alias="QDRANT_API_KEY")
    collection_name: str = Field(default="agentrag_memory", alias="COLLECTION_NAME")
    default_top_k_memory_query: int = Field(default=3, alias="DEFAULT_TOP_K_MEMORY_QUERY")

    embedding_provider: str = Field(default="openrouter", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="qwen/qwen3-embedding-8b", alias="EMBEDDING_MODEL")

    summarizer_provider: str = Field(default="openrouter", alias="SUMMARIZER_PROVIDER")
    summarizer_model: str = Field(default="openai/gpt-oss-20b:free", alias="SUMMARIZER_MODEL")

    enable_reasoning: bool = Field(default=True, alias="ENABLE_REASONING")
    reasoning_provider: str = Field(default="openrouter", alias="REASONING_PROVIDER")
    reasoning_model: str = Field(default="openai/gpt-oss-20b:free", alias="REASONING_MODEL")
    reasoning_max_steps: int = Field(default=3, alias="REASONING_MAX_STEPS")

    enable_reranker: bool = Field(default=True, alias="ENABLE_RERANKER")
    reranker_provider: str = Field(default="fastembed", alias="RERANKER_PROVIDER")
    reranker_model: str = Field(default="BAAI/bge-reranker-v2-m3", alias="RERANKER_MODEL")
    rerank_candidates: int = Field(default=20, alias="RERANK_CANDIDATES")
    final_top_k: int = Field(default=3, alias="FINAL_TOP_K")


def get_settings() -> Settings:
    return Settings()
