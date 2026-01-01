"""Base LLM abstraction for finwin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of a message in a conversation."""
    
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """A message in a conversation."""
    
    role: MessageRole
    content: str
    name: Optional[str] = None  # For tool messages
    tool_call_id: Optional[str] = None  # For tool results
    
    @classmethod
    def system(cls, content: str) -> "Message":
        """Create a system message."""
        return cls(role=MessageRole.SYSTEM, content=content)
    
    @classmethod
    def user(cls, content: str) -> "Message":
        """Create a user message."""
        return cls(role=MessageRole.USER, content=content)
    
    @classmethod
    def assistant(cls, content: str) -> "Message":
        """Create an assistant message."""
        return cls(role=MessageRole.ASSISTANT, content=content)
    
    @classmethod
    def tool(
        cls, 
        content: str, 
        tool_call_id: str, 
        name: Optional[str] = None
    ) -> "Message":
        """Create a tool result message."""
        return cls(
            role=MessageRole.TOOL,
            content=content,
            tool_call_id=tool_call_id,
            name=name,
        )


class ToolCall(BaseModel):
    """A tool call from the LLM."""
    
    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Response from an LLM."""
    
    content: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    finish_reason: Optional[str] = None
    
    # Usage statistics
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    
    # Provider-specific metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return len(self.tool_calls) > 0


class BaseLLM(ABC):
    """
    Abstract base class for LLM providers.
    
    Provides a unified interface for different LLM backends
    (OpenAI, Anthropic, Bedrock, Ollama, etc.)
    
    To create a new LLM provider:
    1. Subclass BaseLLM
    2. Set `provider_name` class attribute
    3. Implement `complete()` method
    4. Optionally implement `stream()` for streaming
    
    Example:
        ```python
        class MyLLM(BaseLLM):
            provider_name = "my_provider"
            
            async def complete(self, messages, **kwargs):
                # Call your LLM API
                return LLMResponse(content="Hello!")
        ```
    """
    
    provider_name: str = "base"
    
    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ):
        """
        Initialize LLM.
        
        Args:
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Provider-specific arguments
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs
    
    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a completion.
        
        Args:
            messages: Conversation messages
            tools: Optional tool definitions for function calling
            **kwargs: Additional provider-specific arguments
            
        Returns:
            LLMResponse with content and/or tool calls
        """
        pass
    
    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream a completion.
        
        Default implementation falls back to non-streaming.
        Override for true streaming support.
        
        Args:
            messages: Conversation messages
            tools: Optional tool definitions
            **kwargs: Additional arguments
            
        Yields:
            Text chunks
        """
        response = await self.complete(messages, tools, **kwargs)
        if response.content:
            yield response.content
    
    async def close(self) -> None:
        """Cleanup resources. Override if needed."""
        pass
    
    def format_tools(
        self, 
        tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Format tools for this provider.
        
        Override to transform tool definitions for specific providers.
        
        Args:
            tools: Generic tool definitions
            
        Returns:
            Provider-specific tool format
        """
        return tools
    
    async def __aenter__(self) -> "BaseLLM":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
