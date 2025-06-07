from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class AgentMessage(BaseModel):
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    actions_taken: List[str] = []


class BaseAgent(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.conversation_history: List[AgentMessage] = []

    @abstractmethod
    async def process_command(
        self, command: str, context: Dict[str, Any] = None
    ) -> AgentResponse:
        pass

    @abstractmethod
    def get_available_functions(self) -> List[Dict[str, Any]]:
        pass

    def add_to_history(self, role: str, content: str, metadata: Dict[str, Any] = None):
        message = AgentMessage(role=role, content=content, metadata=metadata)
        self.conversation_history.append(message)

    def clear_history(self):
        self.conversation_history.clear()

    def get_system_prompt(self) -> str:
        return f"""
You are {self.name}, {self.description}.

You have access to the following functions:
{self._format_functions()}

Always respond with structured actions and clear confirmations of what you've done.
If you cannot complete a task, explain why and suggest alternatives.
"""

    def _format_functions(self) -> str:
        functions = self.get_available_functions()
        formatted = []
        for func in functions:
            formatted.append(
                f"- {func['name']}: {func.get('description', 'No description')}"
            )
        return "\n".join(formatted)
