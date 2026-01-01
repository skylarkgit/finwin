"""Base source class and registry for finwin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from finwin.models.context import SourceResult


class BaseSource(ABC):
    """
    Abstract base class for all data sources.
    
    Subclasses must implement the `gather` method.
    """
    
    name: str = "base"
    
    @abstractmethod
    async def gather(
        self,
        symbol: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs: Any,
    ) -> SourceResult:
        """
        Gather data from this source.
        
        Args:
            symbol: Stock symbol (e.g., "TCS.NS")
            query: Search query (e.g., company name)
            **kwargs: Additional source-specific arguments
            
        Returns:
            SourceResult with gathered data and raw texts
        """
        pass
    
    async def close(self) -> None:
        """Cleanup resources. Override if needed."""
        pass


class SourceRegistry:
    """Registry for discovering and managing data sources."""
    
    _sources: Dict[str, Type[BaseSource]] = {}
    
    @classmethod
    def register(cls, name: str, source_class: Type[BaseSource]) -> None:
        """Register a source class."""
        cls._sources[name] = source_class
    
    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseSource]]:
        """Get a source class by name."""
        return cls._sources.get(name)
    
    @classmethod
    def list_sources(cls) -> List[str]:
        """List all registered source names."""
        return list(cls._sources.keys())
    
    @classmethod
    def create(cls, name: str, **kwargs: Any) -> Optional[BaseSource]:
        """Create a source instance by name."""
        source_class = cls._sources.get(name)
        if source_class:
            return source_class(**kwargs)
        return None


def register_source(name: str):
    """Decorator to register a source class."""
    def decorator(cls: Type[BaseSource]) -> Type[BaseSource]:
        cls.name = name
        SourceRegistry.register(name, cls)
        return cls
    return decorator
