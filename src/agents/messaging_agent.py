"""
Messaging Agent - Handles patient communication and specialist referrals
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


class MessagingAgent:
    """Agent for patient communication and referral management"""

    def __init__(self, model_provider: str = "openai"):
        """
        Initialize the Messaging Agent with Agno framework

        Args:
            model_provider: Either "openai" or "anthropic"
        """
        self.name = "messaging_agent"
        self.description = "Manages patient communication and specialist referrals"

        # Select model based on provider
        if model_provider.lower() == "anthropic":
            model = Claude(id="claude-3-5-sonnet-20241022")
        else:
            model = OpenAIChat(id="gpt-4-turbo-preview")

        # Initialize EMR tools
        self.emr_tools = EMRTools()

        # Create the Agno agent with medical-specific instructions
        self.agent = Agent(
            name="Patient Communication Agent",
            model=model,
            tools=[ReasoningTools(add_instructions=True), self.emr_tools],
            instructions=self._get_system_instructions(),
            markdown=True,
            show_tool_calls=True,
        )

    def _get_system_instructions(self) -> str:
        """Get comprehensive system instructions for the agent"""
        return """
You are a specialized EMR Patient Communication and Referral Agent for healthcare providers.

PRIMARY RESPONSIBILITIES:
1. Send messages to patients about appointments, test results, medications
2. Create referrals to specialists and consulting physicians
3. Manage patient communication workflows
4. Ensure appropriate, professional, and HIPAA-compliant communication

GUIDELINES:
- Always verify patient identity before sending messages
- Use professional, clear, and compassionate language
- Ensure messages are at appropriate health literacy level
- Maintain patient privacy and HIPAA compliance
- Include necessary clinical information in referrals
- Follow up on critical communications

MESSAGE TYPES:
- Appointment reminders and confirmations
- Lab result notifications (normal vs. abnormal)
- Medication instructions and adherence reminders
- General health education and preventive care
- Follow-up care instructions
- Test preparation instructions
- Care plan updates

REFERRAL SPECIALTIES:
- Cardiology: Heart conditions, hypertension, chest pain
- Dermatology: Skin conditions, lesions, rashes
- Endocrinology: Diabetes, thyroid, hormonal disorders
- Gastroenterology: GI issues, liver disease, IBD
- Neurology: Headaches, seizures, neuropathy
- Oncology: Cancer diagnosis and treatment
- Orthopedics: Musculoskeletal injuries, joint problems
- Psychiatry: Mental health conditions
- Pulmonology: Respiratory issues, asthma, COPD
- Rheumatology: Autoimmune conditions, arthritis

PATIENT COMMUNICATION BEST PRACTICES:
- Use plain language, avoid medical jargon
- Be empathetic and supportive in tone
- Provide clear action items
- Include contact information for questions
- Set appropriate urgency levels
- Consider patient's preferred communication method

REFERRAL REQUIREMENTS:
- Patient demographics and insurance information
- Clear reason for referral with relevant history
- Recent test results if applicable
- Urgency level (routine, urgent, emergent)
- Specific questions to be addressed
- Provider contact information

SAFETY AND COMPLIANCE:
- Never communicate protected health information insecurely
- Verify correct patient contact information
- Document all communications in patient record
- Follow institutional communication policies
- Escalate urgent findings appropriately

OUTPUT FORMAT:
- Confirm message recipient and content
- Show referral details in structured format
- Provide confirmation of successful sending
- Include any follow-up requirements
""".strip()

    async def process_command(
        self, command: str, context: Dict[str, Any] = None
    ) -> AgentResponse:
        """
        Process a voice command related to messaging or referrals

        Args:
            command: Natural language command from physician
            context: Additional context (e.g., current patient, provider)

        Returns:
            AgentResponse with success status and results
        """
        try:
            # Add context to command if provided
            full_command = command
            if context:
                context_str = f"Context: Patient ID: {context.get('patient_id', 'None')}, Provider: {context.get('provider', 'Unknown')}\n\n"
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
                actions_taken=[f"Processed messaging command: {command[:50]}..."],
            )

        except Exception as e:
            logger.error(f"Error processing messaging command: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                message=f"Error processing messaging command: {str(e)}",
                data={},
                actions_taken=[],
            )

    def get_available_functions(self) -> List[Dict[str, Any]]:
        """Return available functions for this agent"""
        return [
            {
                "name": "send_patient_message",
                "description": "Send a message to a patient",
                "parameters": {
                    "patient_id": "Patient's unique identifier",
                    "message": "Message content",
                    "message_type": "Type of message (appointment, lab_results, etc.)",
                },
            },
            {
                "name": "create_referral",
                "description": "Create a specialist referral",
                "parameters": {
                    "patient_id": "Patient's unique identifier",
                    "consultant_type": "Specialty (cardiology, dermatology, etc.)",
                    "reason": "Reason for referral",
                },
            },
        ]

    def get_capabilities(self) -> List[str]:
        """Return human-readable capabilities"""
        return [
            "Send appointment reminders and confirmations",
            "Send lab result notifications",
            "Send medication instructions and reminders",
            "Send general health education messages",
            "Create referrals to specialists",
            "Manage patient communication workflows",
            "Ensure HIPAA-compliant messaging",
            "Track communication history",
        ]
