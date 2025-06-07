"""
Chart Agent - Handles patient search, chart opening, and medical record navigation
"""

from typing import Dict, Any, List, Optional
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
from src.tools.emr_tools import EMRTools
from src.agents.base_agent import AgentResponse
import logging

logger = logging.getLogger(__name__)


class ChartAgent:
    """Agent for managing patient charts and medical records"""

    def __init__(self, model_provider: str = "openai"):
        """
        Initialize the Chart Agent with Agno framework

        Args:
            model_provider: Either "openai" or "anthropic"
        """
        self.name = "chart_agent"
        self.description = (
            "Handles patient search, chart opening, and medical record navigation"
        )

        # Select model based on provider
        if model_provider.lower() == "anthropic":
            model = Claude(id="claude-3-5-sonnet-20241022")
        else:
            model = OpenAIChat(id="gpt-4-turbo-preview")

        # Initialize EMR tools
        self.emr_tools = EMRTools()

        # Create the Agno agent with medical-specific instructions
        self.agent = Agent(
            name="Chart Management Agent",
            model=model,
            tools=[ReasoningTools(add_instructions=True), self.emr_tools],
            instructions=self._get_system_instructions(),
            markdown=True,
            show_tool_calls=True,
        )

    def _get_system_instructions(self) -> str:
        """Get comprehensive system instructions for the agent"""
        return """
You are a specialized EMR Chart Management Agent for healthcare providers.

PRIMARY RESPONSIBILITIES:
1. Search for patients by name, medical record number (MRN), or other identifiers
2. Open and retrieve patient charts and medical records
3. Provide patient demographic information
4. Navigate patient medical records efficiently

GUIDELINES:
- Always confirm patient identity before accessing charts
- Use precise search terms when looking for patients
- Present patient information in a clear, organized format
- Maintain HIPAA compliance and patient privacy
- If multiple patients match a search, present options clearly
- Use appropriate medical terminology

SEARCH STRATEGIES:
- Try exact name matches first, then partial matches
- Consider common name variations and misspellings
- Always include MRN in results when available
- Be thorough but efficient in searches

OUTPUT FORMAT:
- Include full name, MRN, date of birth
- Add contact information when relevant
- Summarize key demographic details
- Use tables for multiple patient results
- Highlight important information

SAFETY:
- Never assume patient identity without confirmation
- Alert if accessing sensitive information
- Maintain audit trail of all chart access
""".strip()

    async def process_command(
        self, command: str, context: Dict[str, Any] = None
    ) -> AgentResponse:
        """
        Process a voice command related to chart management

        Args:
            command: Natural language command from physician
            context: Additional context (e.g., current patient, location)

        Returns:
            AgentResponse with success status and results
        """
        try:
            # Add context to command if provided
            full_command = command
            if context:
                context_str = f"Context: Current patient ID: {context.get('patient_id', 'None')}, Location: {context.get('location', 'Unknown')}\n\n"
                full_command = context_str + command

            # Process with Agno agent
            response = self.agent.run(full_command)

            # Extract structured data if available
            data = {}
            if hasattr(response, "data"):
                data = response.data

            return AgentResponse(
                success=True,
                message=response.content,
                data=data,
                actions_taken=[f"Processed chart command: {command[:50]}..."],
            )

        except Exception as e:
            logger.error(f"Error processing chart command: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                message=f"Error processing chart command: {str(e)}",
                data={},
                actions_taken=[],
            )

    def get_available_functions(self) -> List[Dict[str, Any]]:
        """Return available functions for this agent"""
        return [
            {
                "name": "search_patients",
                "description": "Search for patients by name, MRN, or other identifiers",
                "parameters": {
                    "query": "Search query",
                    "limit": "Maximum results (default 10)",
                },
            },
            {
                "name": "get_patient_by_id",
                "description": "Get patient information by ID",
                "parameters": {"patient_id": "Patient's unique identifier"},
            },
            {
                "name": "get_patient_chart",
                "description": "Open a patient's complete medical chart",
                "parameters": {"patient_id": "Patient's unique identifier"},
            },
        ]

    def get_capabilities(self) -> List[str]:
        """Return human-readable capabilities"""
        return [
            "Search for patients by name or medical record number",
            "Open and retrieve patient charts",
            "Get patient demographic information",
            "Navigate patient medical records",
            "Handle multiple patient matches intelligently",
            "Maintain HIPAA compliance during searches",
        ]
