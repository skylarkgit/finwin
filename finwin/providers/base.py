"""Base provider class and registry for finwin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Types of data providers."""
    
    NEWS = "news"
    FINANCIALS = "financials"
    WEB = "web"
    API = "api"
    SEARCH = "search"


class ProviderResult(BaseModel):
    """
    Result from a data provider.
    
    Providers return structured data and optionally raw text
    for LLM consumption.
    """
    
    provider_name: str
    provider_type: ProviderType
    success: bool = True
    error: Optional[str] = None
    
    # Structured data (provider-specific)
    data: Dict[str, Any] = Field(default_factory=dict)
    
    # Raw text for LLM context
    raw_texts: List[str] = Field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_context_text(self) -> str:
        """Convert result to text suitable for LLM context."""
        if not self.raw_texts:
            return ""
        return "\n\n---\n\n".join(self.raw_texts)


class BaseProvider(ABC):
    """
    Abstract base class for all data providers.
    
    Providers fetch data from external sources (APIs, web, etc.)
    and return structured results.
    
    To create a new provider:
    1. Subclass BaseProvider
    2. Set `name` and `provider_type` class attributes
    3. Implement `gather()` method
    4. Optionally implement `close()` for cleanup
    5. Use `@register_provider` decorator to auto-register
    
    Example:
        ```python
        @register_provider("my_api")
        class MyAPIProvider(BaseProvider):
            name = "my_api"
            provider_type = ProviderType.API
            
            async def gather(self, symbol=None, query=None, **kwargs):
                # Fetch data from API
                return ProviderResult(
                    provider_name=self.name,
                    provider_type=self.provider_type,
                    data={"key": "value"},
                    raw_texts=["Some text for LLM"],
                )
        ```
    """
    
    name: str = "base"
    provider_type: ProviderType = ProviderType.WEB
    
    # Provider capabilities - useful for agent tool selection
    supports_symbol: bool = True
    supports_query: bool = True
    supports_batch: bool = False
    
    @abstractmethod
    async def gather(
        self,
        symbol: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs: Any,
    ) -> ProviderResult:
        """
        Gather data from this provider.
        
        Args:
            symbol: Stock symbol (e.g., "TCS.NS", "AAPL")
            query: Search query (e.g., company name)
            **kwargs: Additional provider-specific arguments
            
        Returns:
            ProviderResult with gathered data and raw texts
        """
        pass
    
    async def close(self) -> None:
        """Cleanup resources. Override if needed."""
        pass
    
    def get_tool_description(self) -> str:
        """
        Get description for LLM tool use.
        
        Override to provide better descriptions for agents.
        """
        return f"{self.name} provider ({self.provider_type.value})"
    
    def get_tool_parameters(self) -> Dict[str, Any]:
        """
        Get parameter schema for LLM tool use.
        
        Returns JSON Schema for the gather() parameters.
        """
        params = {
            "type": "object",
            "properties": {},
            "required": [],
        }
        
        if self.supports_symbol:
            params["properties"]["symbol"] = {
                "type": "string",
                "description": "Stock symbol (e.g., TCS.NS, AAPL)",
            }
        
        if self.supports_query:
            params["properties"]["query"] = {
                "type": "string", 
                "description": "Search query (e.g., company name)",
            }
            
        return params


class ProviderRegistry:
    """
    Registry for discovering and managing data providers.
    
    Supports scoped registries for testing isolation.
    """
    
    _global_providers: Dict[str, Type[BaseProvider]] = {}
    
    def __init__(self) -> None:
        """Create a new registry (for testing isolation)."""
        self._providers: Dict[str, Type[BaseProvider]] = {}
    
    @classmethod
    def register(cls, name: str, provider_class: Type[BaseProvider]) -> None:
        """Register a provider class globally."""
        cls._global_providers[name] = provider_class
    
    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseProvider]]:
        """Get a provider class by name from global registry."""
        return cls._global_providers.get(name)
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """List all registered provider names."""
        return list(cls._global_providers.keys())
    
    @classmethod
    def list_by_type(cls, provider_type: ProviderType) -> List[str]:
        """List providers of a specific type."""
        return [
            name for name, prov_cls in cls._global_providers.items()
            if prov_cls.provider_type == provider_type
        ]
    
    @classmethod
    def create(cls, name: str, **kwargs: Any) -> Optional[BaseProvider]:
        """Create a provider instance by name."""
        provider_class = cls._global_providers.get(name)
        if provider_class:
            return provider_class(**kwargs)
        return None
    
    @classmethod
    def create_all(
        cls, 
        names: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[BaseProvider]:
        """
        Create multiple provider instances.
        
        Args:
            names: Provider names to create. If None, creates all.
            **kwargs: Arguments passed to all providers.
        """
        if names is None:
            names = cls.list_providers()
        
        providers = []
        for name in names:
            provider = cls.create(name, **kwargs)
            if provider:
                providers.append(provider)
        return providers


def register_provider(name: str):
    """
    Decorator to register a provider class.
    
    Usage:
        @register_provider("my_provider")
        class MyProvider(BaseProvider):
            ...
    """
    def decorator(cls: Type[BaseProvider]) -> Type[BaseProvider]:
        cls.name = name
        ProviderRegistry.register(name, cls)
        return cls
    return decorator
