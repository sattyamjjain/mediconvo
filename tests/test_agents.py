"""
Test suite for Agno-powered agents
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.agents.chart_agent import ChartAgent
from src.agents.order_agent import OrderAgent
from src.agents.messaging_agent import MessagingAgent
from src.agents.base_agent import AgentResponse


class TestChartAgent:
    """Test suite for Chart Agent"""

    @pytest.fixture
    def chart_agent(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            return ChartAgent("openai")

    def test_initialization(self, chart_agent):
        """Test agent initialization"""
        assert chart_agent.name == "chart_agent"
        assert chart_agent.description is not None
        assert chart_agent.agent is not None
        assert chart_agent.emr_tools is not None

    def test_capabilities(self, chart_agent):
        """Test agent capabilities"""
        capabilities = chart_agent.get_capabilities()
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert any("search" in cap.lower() for cap in capabilities)
        assert any("chart" in cap.lower() for cap in capabilities)

    def test_available_functions(self, chart_agent):
        """Test available functions"""
        functions = chart_agent.get_available_functions()
        assert isinstance(functions, list)
        assert len(functions) == 3

        function_names = [f["name"] for f in functions]
        assert "search_patients" in function_names
        assert "get_patient_by_id" in function_names
        assert "get_patient_chart" in function_names

    @pytest.mark.asyncio
    async def test_process_command_search(self, chart_agent):
        """Test processing search command"""
        # Mock Agno agent response
        mock_response = Mock()
        mock_response.content = "Found 3 patients matching 'Smith'"
        mock_response.data = {}

        with patch.object(chart_agent.agent, "run", return_value=mock_response):
            response = await chart_agent.process_command("Search for patient Smith")

            assert isinstance(response, AgentResponse)
            assert response.success is True
            assert "Found 3 patients" in response.message
            assert len(response.actions_taken) > 0

    @pytest.mark.asyncio
    async def test_process_command_with_context(self, chart_agent):
        """Test processing command with context"""
        mock_response = Mock()
        mock_response.content = "Chart opened for patient 12345"
        mock_response.data = {"patient_id": "12345"}

        with patch.object(chart_agent.agent, "run", return_value=mock_response):
            context = {"patient_id": "12345", "location": "ER"}
            response = await chart_agent.process_command("Open patient chart", context)

            assert response.success is True
            assert "12345" in response.message

    @pytest.mark.asyncio
    async def test_error_handling(self, chart_agent):
        """Test error handling"""
        with patch.object(
            chart_agent.agent, "run", side_effect=Exception("Test error")
        ):
            response = await chart_agent.process_command("Search for patient")

            assert response.success is False
            assert "Error" in response.message
            assert "Test error" in response.message


class TestOrderAgent:
    """Test suite for Order Agent"""

    @pytest.fixture
    def order_agent(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            return OrderAgent("openai")

    def test_initialization(self, order_agent):
        """Test agent initialization"""
        assert order_agent.name == "order_agent"
        assert order_agent.agent is not None
        assert order_agent.emr_tools is not None

    def test_capabilities(self, order_agent):
        """Test agent capabilities"""
        capabilities = order_agent.get_capabilities()
        assert any("lab" in cap.lower() for cap in capabilities)
        assert any("imaging" in cap.lower() for cap in capabilities)
        assert any("medication" in cap.lower() for cap in capabilities)

    def test_available_functions(self, order_agent):
        """Test available functions"""
        functions = order_agent.get_available_functions()
        function_names = [f["name"] for f in functions]

        assert "create_lab_order" in function_names
        assert "create_imaging_order" in function_names
        assert "create_medication_order" in function_names
        assert "get_patient_orders" in function_names

    @pytest.mark.asyncio
    async def test_process_lab_order(self, order_agent):
        """Test processing lab order command"""
        mock_response = Mock()
        mock_response.content = "CBC order created successfully"
        mock_response.data = {"order_id": "ORD123"}

        with patch.object(order_agent.agent, "run", return_value=mock_response):
            response = await order_agent.process_command("Order CBC for patient 123")

            assert response.success is True
            assert "CBC" in response.message
            assert "successfully" in response.message

    @pytest.mark.asyncio
    async def test_process_medication_order(self, order_agent):
        """Test processing medication order"""
        mock_response = Mock()
        mock_response.content = "Prescription created: Lisinopril 10mg daily"
        mock_response.data = {"medication": "lisinopril", "dosage": "10mg"}

        with patch.object(order_agent.agent, "run", return_value=mock_response):
            response = await order_agent.process_command(
                "Prescribe lisinopril 10mg daily"
            )

            assert response.success is True
            assert "lisinopril" in response.message.lower()
            assert "10mg" in response.message


class TestMessagingAgent:
    """Test suite for Messaging Agent"""

    @pytest.fixture
    def messaging_agent(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            return MessagingAgent("openai")

    def test_initialization(self, messaging_agent):
        """Test agent initialization"""
        assert messaging_agent.name == "messaging_agent"
        assert messaging_agent.agent is not None

    def test_capabilities(self, messaging_agent):
        """Test agent capabilities"""
        capabilities = messaging_agent.get_capabilities()
        assert any("message" in cap.lower() for cap in capabilities)
        assert any("referral" in cap.lower() for cap in capabilities)
        assert any("appointment" in cap.lower() for cap in capabilities)

    @pytest.mark.asyncio
    async def test_send_message(self, messaging_agent):
        """Test sending patient message"""
        mock_response = Mock()
        mock_response.content = "Appointment reminder sent to patient"
        mock_response.data = {"message_sent": True}

        with patch.object(messaging_agent.agent, "run", return_value=mock_response):
            response = await messaging_agent.process_command(
                "Send appointment reminder"
            )

            assert response.success is True
            assert "reminder sent" in response.message

    @pytest.mark.asyncio
    async def test_create_referral(self, messaging_agent):
        """Test creating referral"""
        mock_response = Mock()
        mock_response.content = "Referral to cardiology created"
        mock_response.data = {"referral_id": "REF789"}

        with patch.object(messaging_agent.agent, "run", return_value=mock_response):
            response = await messaging_agent.process_command(
                "Refer patient to cardiology"
            )

            assert response.success is True
            assert "cardiology" in response.message.lower()


class TestAgentIntegration:
    """Integration tests for agent system"""

    @pytest.mark.asyncio
    async def test_agent_with_mock_emr(self):
        """Test agent with mocked EMR responses"""
        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test_key",
                "EMR_BASE_URL": "https://test.emr.com/api",
                "EMR_API_KEY": "test_emr_key",
            },
        ):
            agent = ChartAgent("openai")

            # Mock EMR tools
            with patch.object(
                agent.emr_tools,
                "search_patients",
                return_value=[
                    {
                        "id": "123",
                        "name": "John Doe",
                        "mrn": "MRN123",
                        "date_of_birth": "1980-01-01",
                    }
                ],
            ):
                # Mock agent response
                mock_response = Mock()
                mock_response.content = "Found patient John Doe"
                mock_response.data = {}

                with patch.object(agent.agent, "run", return_value=mock_response):
                    response = await agent.process_command("Search for John Doe")

                    assert response.success is True
                    assert "John Doe" in response.message

    @pytest.mark.asyncio
    async def test_multi_agent_scenario(self):
        """Test scenario involving multiple agents"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            # Initialize agents
            chart_agent = ChartAgent("openai")
            order_agent = OrderAgent("openai")

            # Mock responses
            chart_response = Mock()
            chart_response.content = "Patient found: John Doe (ID: 123)"
            chart_response.data = {"patient_id": "123"}

            order_response = Mock()
            order_response.content = "CBC ordered for patient 123"
            order_response.data = {"order_id": "ORD456"}

            # Test chart search
            with patch.object(chart_agent.agent, "run", return_value=chart_response):
                chart_result = await chart_agent.process_command("Find John Doe")
                assert chart_result.success is True

            # Test order creation
            with patch.object(order_agent.agent, "run", return_value=order_response):
                order_result = await order_agent.process_command("Order CBC")
                assert order_result.success is True


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_agent_provider_selection(provider):
    """Test agent initialization with different providers"""
    env_key = f"{provider.upper()}_API_KEY"
    with patch.dict("os.environ", {env_key: "test_key"}):
        agent = ChartAgent(provider)
        assert agent.model_provider == provider

        # Check that correct model is selected
        if provider == "anthropic":
            assert hasattr(agent.agent.model, "__class__")
            assert "Claude" in str(agent.agent.model.__class__)
        else:
            assert hasattr(agent.agent.model, "__class__")
            assert "OpenAI" in str(agent.agent.model.__class__)
