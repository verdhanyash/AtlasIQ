"""Application configuration management.

Loads configuration from configs/default.yaml, with environment variable overrides.
All configurable values are defined here as Pydantic models — no hardcoded values
exist elsewhere in the codebase.

Environment variables use the prefix ATLASIQ_ with double-underscore nesting:
    ATLASIQ_DATABASE__HOST=localhost  →  settings.database.host = "localhost"
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Project root is 3 levels up from this file: atlasiq/backend/core/config.py → project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "default.yaml"


def _load_yaml_config(path: Path) -> dict[str, Any]:
    """Load configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Dictionary of configuration values, or empty dict if file not found.
    """
    if not path.exists():
        logger.warning("Config file not found at %s, using defaults", path)
        return {}

    with open(path) as f:
        data = yaml.safe_load(f)

    return data if isinstance(data, dict) else {}


class ServerConfig(BaseSettings):
    """HTTP server configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_SERVER__")

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"


class DatabaseConfig(BaseSettings):
    """PostgreSQL connection configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_DATABASE__")

    host: str = "localhost"
    port: int = 5432
    name: str = "atlasiq"
    user: str = "atlasiq"
    password: str = "atlasiq"
    pool_min_size: int = 2
    pool_max_size: int = 10

    @property
    def dsn(self) -> str:
        """Build PostgreSQL connection string."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_dsn(self) -> str:
        """Build synchronous PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class QdrantConfig(BaseSettings):
    """Qdrant vector database configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_QDRANT__")

    host: str = "localhost"
    port: int = 6333
    collection_name: str = "atlasiq_chunks"
    vector_size: int = 768


class IngestionConfig(BaseSettings):
    """Document ingestion configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_INGESTION__")

    watched_folder: str = "./watched_documents"
    supported_formats: list[str] = Field(
        default=[".pdf", ".docx", ".md", ".txt"]
    )
    max_file_size_mb: int = 50


class ChunkingConfig(BaseSettings):
    """Text chunking configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_CHUNKING__")

    chunk_size: int = 512
    chunk_overlap: int = 50
    separators: list[str] = Field(default=["\n\n", "\n", ". ", " "])


class EmbeddingConfig(BaseSettings):
    """Embedding model configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_EMBEDDING__")

    model_name: str = "nomic-ai/nomic-embed-text-v1.5"
    batch_size: int = 32
    device: str = "cpu"


class RetrievalConfig(BaseSettings):
    """Retrieval pipeline configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_RETRIEVAL__")

    dense_top_k: int = 20
    bm25_top_k: int = 20
    hybrid_top_k: int = 20
    rerank_top_k: int = 5
    rrf_k: int = 60


class RerankerConfig(BaseSettings):
    """Reranker model configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_RERANKER__")

    model_name: str = "BAAI/bge-reranker-v2-m3"
    device: str = "cpu"


class LLMConfig(BaseSettings):
    """LLM provider configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_LLM__")

    provider: str = "ollama"
    model: str = "gemma3:4b"
    temperature: float = 0.3
    max_tokens: int = 1024
    timeout_seconds: int = 60

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Ensure the LLM provider is one of the supported options."""
        allowed = {"ollama", "nvidia", "openai"}
        if v not in allowed:
            msg = f"LLM provider must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v


class OllamaConfig(BaseSettings):
    """Ollama provider configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_OLLAMA__")

    base_url: str = "http://localhost:11434"


class NvidiaConfig(BaseSettings):
    """NVIDIA Build provider configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_NVIDIA__")

    base_url: str = "https://integrate.api.nvidia.com/v1"
    api_key: str = ""


class OpenAIConfig(BaseSettings):
    """OpenAI provider configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_OPENAI__")

    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""


class PromptsConfig(BaseSettings):
    """Prompt template configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_PROMPTS__")

    directory: str = "prompts"
    qa_template: str = "qa_prompt.txt"
    citation_template: str = "citation_prompt.txt"
    system_template: str = "system_prompt.txt"


class CacheConfig(BaseSettings):
    """Query cache configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_CACHE__")

    enabled: bool = True
    max_size: int = 100
    ttl_seconds: int = 3600


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(env_prefix="ATLASIQ_LOGGING__")

    level: str = "INFO"
    format: str = "json"


class Settings(BaseSettings):
    """Root application settings.

    Aggregates all configuration sections. Values are loaded from:
    1. configs/default.yaml (base defaults)
    2. Environment variables (override)

    Environment variables use the ATLASIQ_ prefix with double-underscore nesting.
    """

    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    nvidia: NvidiaConfig = Field(default_factory=NvidiaConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_settings(config_path: Path | None = None) -> Settings:
    """Load application settings from YAML config and environment variables.

    Args:
        config_path: Path to the YAML config file. Defaults to configs/default.yaml.

    Returns:
        Fully resolved Settings object.
    """
    path = config_path or DEFAULT_CONFIG_PATH
    yaml_data = _load_yaml_config(path)

    # Build nested config objects from YAML, allowing env vars to override
    section_map: dict[str, type[BaseSettings]] = {
        "server": ServerConfig,
        "database": DatabaseConfig,
        "qdrant": QdrantConfig,
        "ingestion": IngestionConfig,
        "chunking": ChunkingConfig,
        "embedding": EmbeddingConfig,
        "retrieval": RetrievalConfig,
        "reranker": RerankerConfig,
        "llm": LLMConfig,
        "ollama": OllamaConfig,
        "nvidia": NvidiaConfig,
        "openai": OpenAIConfig,
        "prompts": PromptsConfig,
        "cache": CacheConfig,
        "logging": LoggingConfig,
    }

    import os
    kwargs: dict[str, Any] = {}
    for section_name, config_cls in section_map.items():
        section_data = yaml_data.get(section_name, {})
        if isinstance(section_data, dict):
            # Clean section data to let environment variables override YAML keys
            filtered_data = {}
            for k, v in section_data.items():
                env_var = f"ATLASIQ_{section_name.upper()}__{k.upper()}"
                if env_var not in os.environ:
                    filtered_data[k] = v
            kwargs[section_name] = config_cls(**filtered_data)
        else:
            kwargs[section_name] = config_cls()

    settings = Settings(**kwargs)
    logger.info("Configuration loaded from %s", path)
    return settings


# Module-level singleton — initialized once at import time, used throughout the app.
# For testing, use load_settings() directly with a custom config path.
settings = load_settings()
