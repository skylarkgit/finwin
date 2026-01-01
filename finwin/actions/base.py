"""Base action class for finwin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Types of actions."""
    
    ALERT = "alert"
    REPORT = "report"
    NOTIFICATION = "notification"
    WEBHOOK = "webhook"
    LOG = "log"


class ActionResult(BaseModel):
    """Result of an action execution."""
    
    action_name: str
    action_type: ActionType
    success: bool = True
    error: Optional[str] = None
    
    # Action-specific result data
    data: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAction(ABC):
    """
    Abstract base class for actions.
    
    Actions are side effects that agents can trigger,
    such as sending alerts, generating reports, or webhooks.
    
    To create a new action:
    1. Subclass BaseAction
    2. Set `name` and `action_type` class attributes
    3. Implement `execute()` method
    
    Example:
        ```python
        class SlackAlertAction(BaseAction):
            name = "slack_alert"
            action_type = ActionType.ALERT
            
            async def execute(self, message: str, **kwargs):
                # Send to Slack
                return ActionResult(
                    action_name=self.name,
                    action_type=self.action_type,
                    success=True,
                )
        ```
    """
    
    name: str = "base"
    action_type: ActionType = ActionType.LOG
    
    def __init__(self, **kwargs: Any):
        """Initialize action with optional configuration."""
        self.config = kwargs
    
    @abstractmethod
    async def execute(
        self,
        **kwargs: Any,
    ) -> ActionResult:
        """
        Execute the action.
        
        Args:
            **kwargs: Action-specific arguments
            
        Returns:
            ActionResult with execution status
        """
        pass
    
    def get_tool_description(self) -> str:
        """Get description for LLM tool use."""
        return f"{self.name} action ({self.action_type.value})"
    
    def get_tool_parameters(self) -> Dict[str, Any]:
        """Get parameter schema for LLM tool use."""
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }
