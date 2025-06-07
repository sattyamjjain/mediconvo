"""
Order Agent - Handles medical order creation (labs, imaging, medications)
"""

from typing import Dict, Any, List, Optional
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.openai import OpenAI
from agno.tools.reasoning import ReasoningTools
from src.tools.emr_tools import EMRTools
from src.agents.base_agent import AgentResponse
import logging

logger = logging.getLogger(__name__)


class OrderAgent:
    """Agent for creating and managing medical orders"""

    def __init__(self, model_provider: str = "openai"):
        """
        Initialize the Order Agent with Agno framework

        Args:
            model_provider: Either "openai" or "anthropic"
        """
        self.name = "order_agent"
        self.description = "Creates and manages medical orders including labs, imaging, and medications"

        # Select model based on provider
        if model_provider.lower() == "anthropic":
            model = Claude(id="claude-3-5-sonnet-20241022")
        else:
            model = OpenAI(id="gpt-4-turbo-preview")

        # Initialize EMR tools
        self.emr_tools = EMRTools()

        # Create the Agno agent with medical-specific instructions
        self.agent = Agent(
            name="Medical Order Entry Agent",
            model=model,
            tools=[ReasoningTools(add_instructions=True), self.emr_tools],
            instructions=self._get_system_instructions(),
            markdown=True,
            show_tool_calls=True,
        )

    def _get_system_instructions(self) -> str:
        """Get comprehensive system instructions for the agent"""
        return """
You are a specialized EMR Order Entry Agent for healthcare providers.

PRIMARY RESPONSIBILITIES:
1. Create laboratory orders (blood tests, cultures, panels)
2. Create imaging orders (X-rays, CT scans, MRIs, ultrasounds)
3. Create medication orders (prescriptions with dosages and frequencies)
4. Retrieve and display patient order history
5. Provide clinical decision support for appropriate ordering

GUIDELINES:
- Always verify patient identity before creating orders
- Use standard medical terminology and abbreviations correctly
- Ensure all required order information is complete
- Check for potential contraindications or duplicate orders
- Confirm critical details when ambiguous
- Follow evidence-based ordering practices

COMMON LABORATORY ORDERS:
- CBC: Complete Blood Count
- BMP: Basic Metabolic Panel (Na, K, Cl, CO2, BUN, Cr, Glucose)
- CMP: Comprehensive Metabolic Panel (BMP + liver function)
- Lipid Panel: Cholesterol screening
- HbA1c: Hemoglobin A1C for diabetes
- TSH: Thyroid Stimulating Hormone
- PT/INR: Coagulation studies
- PTT: Partial Thromboplastin Time
- Urinalysis: Urine analysis
- Blood Culture: For suspected bacteremia

COMMON IMAGING ORDERS:
- Chest X-Ray (CXR): PA and lateral views
- Abdominal X-Ray: KUB (Kidneys, Ureters, Bladder)
- CT Head: With/without contrast
- CT Chest: With/without contrast, PE protocol
- CT Abdomen/Pelvis: With/without contrast
- MRI Brain: With/without gadolinium
- Ultrasound: Abdominal, pelvic, vascular
- Echocardiogram: TTE (transthoracic)

MEDICATION ORDERING:
- Always include: Drug name, dose, route, frequency, duration
- Use standard abbreviations: PO (by mouth), IV, IM, SubQ
- Frequency: Daily, BID, TID, QID, Q6H, Q8H, Q12H, PRN
- Check for allergies and interactions
- Consider renal/hepatic dosing adjustments

SAFETY CHECKS:
- Verify no duplicate orders exist
- Check for allergies (especially contrast, medications)
- Consider renal function for contrast studies
- Review medication interactions
- Alert for critical values or urgent orders

OUTPUT FORMAT:
- Confirm order details clearly
- Use tables for multiple orders
- Include relevant clinical indications
- Provide order confirmation numbers when available
""".strip()

    async def process_command(
        self, command: str, context: Dict[str, Any] = None
    ) -> AgentResponse:
        """
        Process a voice command related to medical orders

        Args:
            command: Natural language command from physician
            context: Additional context (e.g., current patient, ordering provider)

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
                actions_taken=[f"Processed order command: {command[:50]}..."],
            )

        except Exception as e:
            logger.error(f"Error processing order command: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                message=f"Error processing order command: {str(e)}",
                data={},
                actions_taken=[],
            )

    def get_available_functions(self) -> List[Dict[str, Any]]:
        """Return available functions for this agent"""
        return [
            {
                "name": "create_lab_order",
                "description": "Create a laboratory order",
                "parameters": {
                    "patient_id": "Patient's unique identifier",
                    "lab_type": "Type of lab test (e.g., CBC, BMP, CMP)",
                    "ordered_by": "Ordering provider name",
                },
            },
            {
                "name": "create_imaging_order",
                "description": "Create an imaging order",
                "parameters": {
                    "patient_id": "Patient's unique identifier",
                    "imaging_type": "Type of imaging (e.g., chest_xray, ct_head)",
                    "ordered_by": "Ordering provider name",
                    "reason": "Clinical indication",
                },
            },
            {
                "name": "create_medication_order",
                "description": "Create a medication order",
                "parameters": {
                    "patient_id": "Patient's unique identifier",
                    "medication": "Medication name",
                    "dosage": "Dose amount (e.g., 10mg)",
                    "frequency": "Frequency (e.g., daily, BID)",
                    "ordered_by": "Ordering provider name",
                },
            },
            {
                "name": "get_patient_orders",
                "description": "Retrieve all orders for a patient",
                "parameters": {"patient_id": "Patient's unique identifier"},
            },
        ]

    def get_capabilities(self) -> List[str]:
        """Return human-readable capabilities"""
        return [
            "Create laboratory orders (CBC, BMP, CMP, etc.)",
            "Create imaging orders (X-rays, CT, MRI, Ultrasound)",
            "Create medication orders with proper dosing",
            "Retrieve patient order history",
            "Check for duplicate orders and contraindications",
            "Provide clinical decision support for ordering",
            "Verify order completeness and accuracy",
        ]
