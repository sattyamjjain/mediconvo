"""
Command Processor - Orchestrates agent team using Agno framework
"""

from typing import Dict, Any, List, Optional
from agno.team import Team
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.openai import OpenAI
from agno.tools.reasoning import ReasoningTools
from src.agents.chart_agent import ChartAgent
from src.agents.order_agent import OrderAgent
from src.agents.messaging_agent import MessagingAgent
from src.agents.base_agent import AgentResponse
from src.utils.metrics import performance_metrics, track_performance
import logging

logger = logging.getLogger(__name__)


class CommandProcessor:
    """Orchestrates multi-agent EMR system using Agno Team"""

    def __init__(self, model_provider: str = "openai"):
        """
        Initialize the command processor with Agno Team

        Args:
            model_provider: Either "openai" or "anthropic"
        """
        self.model_provider = model_provider

        # Initialize specialized agents
        self.chart_agent = ChartAgent(model_provider)
        self.order_agent = OrderAgent(model_provider)
        self.messaging_agent = MessagingAgent(model_provider)

        # Create coordinator agent for intelligent routing
        if model_provider.lower() == "anthropic":
            coordinator_model = Claude(id="claude-3-5-sonnet-20241022")
        else:
            coordinator_model = OpenAI(id="gpt-4-turbo-preview")

        self.coordinator = Agent(
            name="EMR Command Coordinator",
            model=coordinator_model,
            tools=[ReasoningTools(add_instructions=True)],
            instructions=self._get_coordinator_instructions(),
            markdown=True,
        )

        # Create Agno Team for multi-agent collaboration
        self.team = Team(
            members=[
                self.chart_agent.agent,
                self.order_agent.agent,
                self.messaging_agent.agent,
            ],
            instructions=self._get_team_instructions(),
            show_tool_calls=True,
        )

        # Agent registry for direct routing
        self.agents = {
            "chart_agent": self.chart_agent,
            "order_agent": self.order_agent,
            "messaging_agent": self.messaging_agent,
        }

        logger.info(f"CommandProcessor initialized with {model_provider} provider")

    def _get_coordinator_instructions(self) -> str:
        """Instructions for the coordinator agent"""
        return """
You are the EMR Command Coordinator responsible for analyzing healthcare voice commands and determining the optimal routing strategy.

AVAILABLE AGENTS:
1. Chart Agent: Patient search, chart opening, demographics, medical records
2. Order Agent: Lab orders, imaging orders, medications, prescriptions
3. Messaging Agent: Patient messages, notifications, specialist referrals

ROUTING STRATEGY:
- Analyze the command to identify the primary intent
- Determine if it's a simple single-agent task or complex multi-agent workflow
- For complex workflows, identify the sequence of agents needed
- Consider dependencies between tasks

COMMAND PATTERNS:
Chart Agent:
- Keywords: "search", "find", "open chart", "patient", "demographics", "medical record"
- Examples: "Find patient Smith", "Open chart for 12345"

Order Agent:
- Keywords: "order", "prescribe", "lab", "imaging", "medication", "CBC", "X-ray", "CT", "MRI"
- Examples: "Order CBC", "Prescribe lisinopril", "Get chest X-ray"

Messaging Agent:
- Keywords: "message", "notify", "send", "refer", "referral", "appointment"
- Examples: "Send lab results", "Refer to cardiology"

COMPLEX WORKFLOWS:
- Multiple actions: "Find patient AND order labs AND notify"
- Sequential dependencies: Chart must be opened before ordering
- Parallel tasks: Multiple orders can be placed simultaneously

OUTPUT:
Provide a structured routing decision:
- agent: single agent name OR "team" for multi-agent
- workflow: list of agents if multi-agent
- reasoning: brief explanation of routing decision
""".strip()

    def _get_team_instructions(self) -> str:
        """Instructions for the agent team"""
        return """
You are a team of specialized EMR agents working together to help healthcare providers efficiently manage electronic medical records through voice commands.

TEAM COMPOSITION:
- Chart Agent: Patient data and medical records
- Order Agent: Medical orders and prescriptions
- Messaging Agent: Patient communication and referrals

COLLABORATION PRINCIPLES:
1. Share relevant patient context between agents
2. Ensure data consistency across actions
3. Complete workflows in logical sequence
4. Verify prerequisites before actions
5. Provide comprehensive responses

WORKFLOW PATTERNS:
- Sequential: Open chart → Create order → Send notification
- Parallel: Multiple orders can be created simultaneously
- Conditional: Check patient data before ordering

SAFETY:
- Always verify patient identity
- Check for contraindications
- Ensure HIPAA compliance
- Document all actions

OUTPUT:
Provide clear, structured responses showing:
- Actions completed by each agent
- Any warnings or important notes
- Confirmation of successful completion
""".strip()

    @track_performance("classify_intent")
    async def _classify_intent(self, command: str) -> Dict[str, Any]:
        """
        Use coordinator to classify command intent

        Args:
            command: Voice command to analyze

        Returns:
            Routing decision with agent selection
        """
        try:
            analysis_prompt = f"""
Analyze this healthcare voice command and determine routing:
Command: "{command}"

Respond with JSON:
{{
    "agent": "chart_agent" | "order_agent" | "messaging_agent" | "team",
    "confidence": 0.0-1.0,
    "workflow": ["agent1", "agent2"] if multi-agent,
    "reasoning": "brief explanation"
}}
"""
            response = self.coordinator.run(analysis_prompt)

            # Parse response (Agno responses are typically well-structured)
            import json

            try:
                # Extract JSON from response
                content = response.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "{" in content and "}" in content:
                    # Find JSON object in response
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    content = content[start:end]

                return json.loads(content)
            except:
                # Fallback to keyword-based routing
                return self._keyword_based_routing(command)

        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return self._keyword_based_routing(command)

    def _keyword_based_routing(self, command: str) -> Dict[str, Any]:
        """Fallback keyword-based routing"""
        command_lower = command.lower()

        # Check for multi-agent workflows
        agent_keywords = {
            "chart_agent": ["search", "find", "open chart", "patient", "demographics"],
            "order_agent": [
                "order",
                "prescribe",
                "lab",
                "imaging",
                "medication",
                "cbc",
                "x-ray",
            ],
            "messaging_agent": ["message", "notify", "send", "refer", "referral"],
        }

        matched_agents = []
        for agent, keywords in agent_keywords.items():
            if any(keyword in command_lower for keyword in keywords):
                matched_agents.append(agent)

        if len(matched_agents) > 1:
            return {
                "agent": "team",
                "confidence": 0.8,
                "workflow": matched_agents,
                "reasoning": "Multiple agent domains detected",
            }
        elif matched_agents:
            return {
                "agent": matched_agents[0],
                "confidence": 0.9,
                "workflow": [],
                "reasoning": "Single agent domain detected",
            }
        else:
            return {
                "agent": "chart_agent",  # Default
                "confidence": 0.5,
                "workflow": [],
                "reasoning": "No clear match, defaulting to chart agent",
            }

    @track_performance("process_command")
    async def process_voice_command(
        self, command: str, context: Dict[str, Any] = None
    ) -> AgentResponse:
        """
        Process voice command using intelligent agent routing

        Args:
            command: Natural language voice command
            context: Additional context (patient, provider, location)

        Returns:
            AgentResponse with execution results
        """
        try:
            # Log command
            logger.info(f"Processing command: {command[:100]}...")

            # Classify intent
            routing = await self._classify_intent(command)
            logger.info(f"Routing decision: {routing}")

            # Execute based on routing
            if routing["agent"] == "team":
                # Multi-agent workflow
                return await self._execute_team_workflow(command, context, routing)
            else:
                # Single agent execution
                agent_name = routing["agent"]
                if agent_name in self.agents:
                    agent = self.agents[agent_name]
                    response = await agent.process_command(command, context)
                    response.data["routing"] = routing
                    return response
                else:
                    return AgentResponse(
                        success=False,
                        message=f"Unknown agent: {agent_name}",
                        data={"routing": routing},
                    )

        except Exception as e:
            logger.error(f"Error processing command: {e}", exc_info=True)
            return AgentResponse(
                success=False, message=f"Error processing command: {str(e)}", data={}
            )

    async def _execute_team_workflow(
        self, command: str, context: Dict[str, Any], routing: Dict[str, Any]
    ) -> AgentResponse:
        """
        Execute multi-agent team workflow

        Args:
            command: Voice command
            context: Execution context
            routing: Routing decision with workflow

        Returns:
            AgentResponse with combined results
        """
        try:
            # Add context to command
            full_command = command
            if context:
                context_str = f"Context: {context}\n\n"
                full_command = context_str + command

            # Execute with Agno Team
            team_response = self.team.run(full_command)

            return AgentResponse(
                success=True,
                message=team_response.content,
                data={
                    "routing": routing,
                    "workflow": routing.get("workflow", []),
                    "team_execution": True,
                },
                actions_taken=["Executed multi-agent workflow"],
            )

        except Exception as e:
            logger.error(f"Error in team workflow: {e}")
            return AgentResponse(
                success=False,
                message=f"Team workflow error: {str(e)}",
                data={"routing": routing},
            )

    def get_registered_agents(self) -> List[str]:
        """Get list of registered agents"""
        return list(self.agents.keys())

    def get_agent_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of all agents"""
        capabilities = {}
        for name, agent in self.agents.items():
            capabilities[name] = agent.get_capabilities()
        return capabilities

    async def get_help(self) -> str:
        """Generate comprehensive help text"""
        help_text = """
# EMR Voice Assistant - Available Commands

## Chart Management (Chart Agent)
- Search for patients: "Find patient John Smith"
- Open charts: "Open chart for patient 12345"
- Get demographics: "Show patient information for Smith"

## Medical Orders (Order Agent)
- Lab orders: "Order CBC for patient"
- Imaging: "Get chest X-ray for patient Doe"
- Medications: "Prescribe lisinopril 10mg daily"
- Order history: "Show all orders for patient 123"

## Communication (Messaging Agent)
- Patient messages: "Send appointment reminder to patient"
- Lab notifications: "Notify patient about lab results"
- Referrals: "Refer patient to cardiology for chest pain"

## Complex Workflows
- "Find patient Smith, order CBC, and send notification"
- "Open chart for 12345, prescribe metformin, notify patient"
- "Search for Johnson, create cardiology referral with recent labs"

## Tips
- Be specific with patient identifiers
- Include relevant clinical details
- Commands can be conversational
- Multiple actions can be combined
"""
        return help_text
