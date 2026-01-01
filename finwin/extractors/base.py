"""Base extractor class for finwin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Union


class BaseExtractor(ABC):
    """
    Abstract base class for content extractors.
    
    Extractors convert raw content (HTML, PDF, etc.) into plain text
    suitable for LLM consumption.
    
    To create a new extractor:
    1. Subclass BaseExtractor
    2. Set `name` and `supported_types` class attributes
    3. Implement `extract()` method
    
    Example:
        ```python
        class MarkdownExtractor(BaseExtractor):
            name = "markdown"
            supported_types = ["text/markdown", "text/x-markdown"]
            
            async def extract(self, content, source_url=None):
                # Process markdown content
                return clean_text, None
        ```
    """
    
    name: str = "base"
    supported_types: list[str] = []
    
    @abstractmethod
    async def extract(
        self,
        content: Union[str, bytes],
        source_url: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text from content.
        
        Args:
            content: Raw content (string for text, bytes for binary)
            source_url: Optional source URL for context
            
        Returns:
            Tuple of (extracted_text, error_message)
            - If successful: (text, None)
            - If failed: (None, error_message)
        """
        pass
    
    def can_handle(self, content_type: str) -> bool:
        """
        Check if this extractor can handle the given content type.
        
        Args:
            content_type: MIME type string
            
        Returns:
            True if this extractor supports the content type
        """
        ct_lower = content_type.lower()
        return any(st in ct_lower for st in self.supported_types)
