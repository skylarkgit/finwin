"""Centralized settings management using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """Configuration for LLM providers."""
    
    model_config = SettingsConfigDict(
        env_prefix="FINWIN_LLM_",
        extra="ignore",
    )
    
    # Default provider: bedrock, openai, anthropic, ollama, etc.
    provider: str = "bedrock"
    
    # Model name (provider-specific)
    model: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    # AWS Bedrock specific
    aws_region: str = "us-east-1"
    aws_profile: Optional[str] = None
    
    # OpenAI specific
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    
    # Anthropic specific
    anthropic_api_key: Optional[str] = None
    
    # Ollama specific
    ollama_base_url: str = "http://localhost:11434"
    
    # Common settings
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120


class ProviderConfig(BaseSettings):
    """Configuration for data providers (APIs, scrapers, etc.)."""
    
    model_config = SettingsConfigDict(
        env_prefix="FINWIN_PROVIDER_",
        extra="ignore",
    )
    
    # Default enabled providers
    enabled_providers: List[str] = Field(
        default=["google_news", "yfinance", "web"]
    )
    
    # API Keys (future providers)
    alpha_vantage_api_key: Optional[str] = None
    polygon_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    
    # Rate limiting
    requests_per_minute: int = 60
    
    # Timeouts
    http_timeout: int = 30


class CacheConfig(BaseSettings):
    """Configuration for caching."""
    
    model_config = SettingsConfigDict(
        env_prefix="FINWIN_CACHE_",
        extra="ignore",
    )
    
    # Cache backend: memory, redis, dynamodb
    backend: Literal["memory", "redis", "dynamodb"] = "memory"
    
    # TTL in seconds
    default_ttl: int = 300
    
    # Redis settings
    redis_url: Optional[str] = None
    
    # DynamoDB settings
    dynamodb_table: Optional[str] = None
    dynamodb_region: Optional[str] = None


class ServerConfig(BaseSettings):
    """Configuration for FastAPI server."""
    
    model_config = SettingsConfigDict(
        env_prefix="FINWIN_SERVER_",
        extra="ignore",
    )
    
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    
    # CORS
    cors_origins: List[str] = Field(default=["*"])
    
    # API settings
    api_prefix: str = "/api"


class Settings(BaseSettings):
    """
    Main settings class aggregating all configuration.
    
    Environment variables are prefixed with FINWIN_.
    Example: FINWIN_DEBUG=true, FINWIN_LLM_PROVIDER=openai
    """
    
    model_config = SettingsConfigDict(
        env_prefix="FINWIN_",
        env_nested_delimiter="__",
        extra="ignore",
    )
    
    # General
    debug: bool = False
    log_level: str = "INFO"
    
    # Sub-configurations
    llm: LLMConfig = Field(default_factory=LLMConfig)
    providers: ProviderConfig = Field(default_factory=ProviderConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    
    def get_enabled_provider_names(self) -> List[str]:
        """Get list of enabled provider names."""
        return self.providers.enabled_providers
    
    def get_llm_kwargs(self) -> Dict[str, Any]:
        """Get kwargs for LLM client initialization."""
        base = {
            "temperature": self.llm.temperature,
            "max_tokens": self.llm.max_tokens,
        }
        
        if self.llm.provider == "bedrock":
            base["model_id"] = self.llm.model
            base["region_name"] = self.llm.aws_region
            if self.llm.aws_profile:
                base["profile_name"] = self.llm.aws_profile
        elif self.llm.provider == "openai":
            base["model"] = self.llm.model
            base["api_key"] = self.llm.openai_api_key
            if self.llm.openai_base_url:
                base["base_url"] = self.llm.openai_base_url
        elif self.llm.provider == "anthropic":
            base["model"] = self.llm.model
            base["api_key"] = self.llm.anthropic_api_key
        elif self.llm.provider == "ollama":
            base["model"] = self.llm.model
            base["base_url"] = self.llm.ollama_base_url
            
        return base


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache for singleton pattern - settings are loaded once.
    Call get_settings.cache_clear() to reload.
    """
    return Settings()
