import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.orchestration_v2.agent_team import EMRAgentTeam
from src.agents_v2.chart_agent import ChartAgent
from src.agents_v2.order_agent import OrderAgent
from src.agents_v2.messaging_agent import MessagingAgent
from src.tools.emr_tools import EMRTools


@pytest.fixture
def mock_env():
    """Mock environment variables for testing."""
    with patch.dict(
        "os.environ",
        {
            "OPENAI_API_KEY": "test_key",
            "EMR_BASE_URL": "https://test-emr.com/api",
            "EMR_API_KEY": "test_emr_key",
        },
    ):
        yield


@pytest.fixture
def emr_tools():
    """Create EMR tools instance for testing."""
    return EMRTools()


@pytest.fixture
def chart_agent(mock_env):
    """Create chart agent for testing."""
    return ChartAgent("openai")


@pytest.fixture
def order_agent(mock_env):
    """Create order agent for testing."""
    return OrderAgent("openai")


@pytest.fixture
def messaging_agent(mock_env):
    """Create messaging agent for testing."""
    return MessagingAgent("openai")


@pytest.fixture
def agent_team(mock_env):
    """Create agent team for testing."""
    return EMRAgentTeam("openai")


class TestEMRTools:
    def test_emr_tools_initialization(self, emr_tools):
        """Test EMR tools can be initialized."""
        assert emr_tools is not None
        assert emr_tools.name == "emr_tools"
        assert "EMR" in emr_tools.description

    @patch("src.tools.emr_tools.EMRClient")
    def test_search_patients(self, mock_emr_client, emr_tools):
        """Test patient search functionality."""
        # Mock the EMR client response
        mock_patient = Mock()
        mock_patient.id = "123"
        mock_patient.first_name = "John"
        mock_patient.last_name = "Doe"
        mock_patient.medical_record_number = "MRN123"
        mock_patient.date_of_birth = "1980-01-01"
        mock_patient.phone = "555-0123"
        mock_patient.email = "john.doe@email.com"

        # Mock async call
        async def mock_search_patients(query, limit):
            return [mock_patient]

        emr_tools.emr_client.search_patients = mock_search_patients

        # Test the search
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = [mock_patient]
            results = emr_tools.search_patients("John Doe")

            assert len(results) == 1
            assert results[0]["name"] == "John Doe"
            assert results[0]["mrn"] == "MRN123"


class TestChartAgent:
    def test_chart_agent_initialization(self, chart_agent):
        """Test chart agent initialization."""
        assert chart_agent is not None
        assert chart_agent.agent.name == "Chart Management Agent"

    def test_chart_agent_capabilities(self, chart_agent):
        """Test chart agent capabilities."""
        capabilities = chart_agent.get_capabilities()
        assert len(capabilities) > 0
        assert any("search" in cap.lower() for cap in capabilities)
        assert any("chart" in cap.lower() for cap in capabilities)

    @patch("src.agents_v2.chart_agent.ChartAgent")
    @pytest.mark.asyncio
    async def test_chart_agent_process_command(self, mock_chart_agent):
        """Test chart agent command processing."""
        # Mock the agent response
        mock_response = Mock()
        mock_response.content = "Found patient John Doe (MRN: 12345)"

        mock_agent_instance = Mock()
        mock_agent_instance.run.return_value = mock_response
        mock_chart_agent.return_value.agent = mock_agent_instance

        chart_agent = ChartAgent("openai")
        chart_agent.agent = mock_agent_instance

        response = await chart_agent.process_command("Search for John Doe")

        assert response["success"] is True
        assert "John Doe" in response["message"]
        assert response["agent"] == "chart_agent"


class TestOrderAgent:
    def test_order_agent_initialization(self, order_agent):
        """Test order agent initialization."""
        assert order_agent is not None
        assert order_agent.agent.name == "Medical Order Entry Agent"

    def test_order_agent_capabilities(self, order_agent):
        """Test order agent capabilities."""
        capabilities = order_agent.get_capabilities()
        assert len(capabilities) > 0
        assert any("lab" in cap.lower() for cap in capabilities)
        assert any("imaging" in cap.lower() for cap in capabilities)
        assert any("medication" in cap.lower() for cap in capabilities)


class TestMessagingAgent:
    def test_messaging_agent_initialization(self, messaging_agent):
        """Test messaging agent initialization."""
        assert messaging_agent is not None
        assert messaging_agent.agent.name == "Patient Communication Agent"

    def test_messaging_agent_capabilities(self, messaging_agent):
        """Test messaging agent capabilities."""
        capabilities = messaging_agent.get_capabilities()
        assert len(capabilities) > 0
        assert any("message" in cap.lower() for cap in capabilities)
        assert any("referral" in cap.lower() for cap in capabilities)


class TestAgentTeam:
    def test_agent_team_initialization(self, agent_team):
        """Test agent team initialization."""
        assert agent_team is not None
        assert agent_team.chart_agent is not None
        assert agent_team.order_agent is not None
        assert agent_team.messaging_agent is not None
        assert agent_team.coordinator is not None
        assert agent_team.team is not None

    @pytest.mark.asyncio
    async def test_get_capabilities(self, agent_team):
        """Test getting all agent capabilities."""
        capabilities = await agent_team.get_available_capabilities()

        assert "chart_agent" in capabilities
        assert "order_agent" in capabilities
        assert "messaging_agent" in capabilities

        assert len(capabilities["chart_agent"]) > 0
        assert len(capabilities["order_agent"]) > 0
        assert len(capabilities["messaging_agent"]) > 0

    @pytest.mark.asyncio
    async def test_help_generation(self, agent_team):
        """Test help text generation."""
        help_text = await agent_team.get_help()

        assert "Chart Management" in help_text
        assert "Medical Orders" in help_text
        assert "Patient Communication" in help_text
        assert "Example Voice Commands" in help_text

    @patch("src.orchestration_v2.agent_team.Agent")
    @pytest.mark.asyncio
    async def test_voice_command_routing(self, mock_agent_class, agent_team):
        """Test voice command routing to appropriate agents."""
        # Mock coordinator response
        mock_coordinator_response = Mock()
        mock_coordinator_response.content = "Route to chart agent"

        # Mock chart agent response
        mock_chart_response = {
            "success": True,
            "message": "Found patient John Smith",
            "agent": "chart_agent",
        }

        agent_team.coordinator.run = Mock(return_value=mock_coordinator_response)
        agent_team.chart_agent.process_command = AsyncMock(
            return_value=mock_chart_response
        )

        # Test chart-related command
        response = await agent_team.process_voice_command(
            "Search for patient John Smith"
        )

        assert response["success"] is True
        assert response["routing"] == "chart_agent"
        assert "John Smith" in response["message"]

    @pytest.mark.asyncio
    async def test_complex_workflow_routing(self, agent_team):
        """Test complex multi-agent workflow routing."""
        # Mock team response for complex commands
        mock_team_response = Mock()
        mock_team_response.content = "Completed multi-step workflow: found patient, created order, sent notification"

        agent_team.team.run = Mock(return_value=mock_team_response)
        agent_team.coordinator.run = Mock(
            return_value=Mock(content="Complex workflow needed")
        )

        complex_command = (
            "Find patient Smith, order CBC, and notify them about the test"
        )
        response = await agent_team.process_voice_command(complex_command)

        assert response["success"] is True
        assert response["routing"] == "team_collaboration"
        assert "workflow" in response["message"]

    @pytest.mark.asyncio
    async def test_error_handling(self, agent_team):
        """Test error handling in agent team."""
        # Mock an error in the coordinator
        agent_team.coordinator.run = Mock(side_effect=Exception("Test error"))

        response = await agent_team.process_voice_command("Test command")

        assert response["success"] is False
        assert "error" in response["message"].lower()
        assert response["routing"] == "error"


class TestAgentIntegration:
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, mock_env):
        """Test complete end-to-end workflow with mocked components."""
        # This test would verify the complete flow from voice command to EMR action
        # In a real scenario, this would test with actual EMR mock responses

        agent_team = EMRAgentTeam("openai")

        # Mock all the underlying components
        with patch.object(agent_team.coordinator, "run") as mock_coordinator:
            mock_coordinator.return_value = Mock(content="Route to chart agent")

            with patch.object(agent_team.chart_agent, "process_command") as mock_chart:
                mock_chart.return_value = {
                    "success": True,
                    "message": "Successfully found patient and opened chart",
                    "agent": "chart_agent",
                }

                response = await agent_team.process_voice_command(
                    "Open chart for patient 12345"
                )

                assert response["success"] is True
                assert response["routing"] == "chart_agent"
                mock_coordinator.assert_called_once()
                mock_chart.assert_called_once()

    @pytest.mark.asyncio
    async def test_performance_characteristics(self, agent_team):
        """Test that agent operations complete within reasonable time."""
        import time

        start_time = time.time()
        capabilities = await agent_team.get_available_capabilities()
        end_time = time.time()

        # Should complete very quickly (< 1 second for capability lookup)
        assert (end_time - start_time) < 1.0
        assert len(capabilities) == 3  # Three main agents
