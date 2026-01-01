"""Base agent class for finwin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from finwin.llm.base import BaseLLM, Message
from finwin.providers.base import BaseProvider


class Tool(BaseModel):
    """A tool that an agent can use."""
    
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Reference to the actual callable
    provider: Optional[str] = None  # Provider name if this wraps a provider
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class AgentResponse(BaseModel):
    """Response from an agent execution."""
    
    content: str
    tool_calls_made: List[str] = Field(default_factory=list)
    iterations: int = 0
    
    # Data gathered during execution
    gathered_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Conversation history
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Any errors encountered
    errors: List[str] = Field(default_factory=list)


class BaseAgent(ABC):
    """
    Abstract base class for AI agents.
    
    Agents orchestrate LLM interactions with tools (providers, actions)
    to accomplish complex tasks.
    
    To create a new agent:
    1. Subclass BaseAgent
    2. Implement `run()` method
    3. Optionally override `_build_system_prompt()` and `_get_tools()`
    
    Example:
        ```python
        class ResearchAgent(BaseAgent):
            name = "research"
            
            async def run(self, query: str, **kwargs):
                # Use self.llm and self.tools
                response = await self.llm.complete(...)
                return AgentResponse(content=response.content)
        ```
    """
    
    name: str = "base"
    description: str = "Base agent"
    
    def __init__(
        self,
        llm: BaseLLM,
        providers: Optional[List[BaseProvider]] = None,
        max_iterations: int = 10,
        **kwargs: Any,
    ):
        """
        Initialize agent.
        
        Args:
            llm: LLM instance to use
            providers: Data providers available as tools
            max_iterations: Maximum tool use iterations
            **kwargs: Additional arguments
        """
        self.llm = llm
        self.providers = providers or []
        self.max_iterations = max_iterations
        self.kwargs = kwargs
        
        # Build tools from providers
        self._tools: List[Tool] = self._build_tools()
    
    def _build_tools(self) -> List[Tool]:
        """Build tool definitions from providers."""
        tools = []
        for provider in self.providers:
            tools.append(Tool(
                name=f"get_{provider.name}",
                description=provider.get_tool_description(),
                parameters=provider.get_tool_parameters(),
                provider=provider.name,
            ))
        return tools
    
    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the agent.
        
        Override to customize agent behavior.
        """
        return (
            "You are a helpful financial research assistant. "
            "Use the available tools to gather information and answer questions."
        )
    
    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Get tool definitions in LLM-compatible format."""
        return [tool.to_openai_format() for tool in self._tools]
    
    async def execute_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> str:
        """
        Execute a tool call.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            
        Returns:
            String result of the tool execution
        """
        # Find the provider for this tool
        provider_name = tool_name.replace("get_", "", 1)
        
        for provider in self.providers:
            if provider.name == provider_name:
                result = await provider.gather(**arguments)
                
                if result.success:
                    return result.to_context_text() or str(result.data)
                else:
                    return f"Error: {result.error}"
        
        return f"Unknown tool: {tool_name}"
    
    @abstractmethod
    async def run(
        self,
        query: str,
        context: Optional[str] = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Run the agent.
        
        Args:
            query: User query or task
            context: Optional additional context
            **kwargs: Additional arguments
            
        Returns:
            AgentResponse with results
        """
        pass
    
    async def close(self) -> None:
        """Cleanup resources."""
        await self.llm.close()
        for provider in self.providers:
            await provider.close()
    
    async def __aenter__(self) -> "BaseAgent":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
