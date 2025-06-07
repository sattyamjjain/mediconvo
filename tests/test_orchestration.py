"""
Test suite for orchestration and command processing
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.orchestration.command_processor import CommandProcessor
from src.agents.base_agent import AgentResponse


class TestCommandProcessor:
    """Test suite for CommandProcessor"""

    @pytest.fixture
    def processor(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            return CommandProcessor("openai")

    def test_initialization(self, processor):
        """Test processor initialization"""
        assert processor is not None
        assert processor.chart_agent is not None
        assert processor.order_agent is not None
        assert processor.messaging_agent is not None
        assert processor.coordinator is not None
        assert processor.team is not None

        # Check agent registry
        assert len(processor.agents) == 3
        assert "chart_agent" in processor.agents
        assert "order_agent" in processor.agents
        assert "messaging_agent" in processor.agents

    def test_get_registered_agents(self, processor):
        """Test getting registered agents"""
        agents = processor.get_registered_agents()
        assert len(agents) == 3
        assert "chart_agent" in agents
        assert "order_agent" in agents
        assert "messaging_agent" in agents

    def test_get_agent_capabilities(self, processor):
        """Test getting agent capabilities"""
        capabilities = processor.get_agent_capabilities()
        assert isinstance(capabilities, dict)
        assert len(capabilities) == 3

        # Check each agent has capabilities
        for agent_name, caps in capabilities.items():
            assert isinstance(caps, list)
            assert len(caps) > 0

    @pytest.mark.asyncio
    async def test_get_help(self, processor):
        """Test help generation"""
        help_text = await processor.get_help()
        assert isinstance(help_text, str)
        assert "Chart Management" in help_text
        assert "Medical Orders" in help_text
        assert "Communication" in help_text
        assert "Complex Workflows" in help_text

    @pytest.mark.asyncio
    async def test_classify_intent_single_agent(self, processor):
        """Test intent classification for single agent"""
        # Mock coordinator response
        mock_response = Mock()
        mock_response.content = """
        {
            "agent": "chart_agent",
            "confidence": 0.95,
            "workflow": [],
            "reasoning": "Patient search command"
        }
        """

        with patch.object(processor.coordinator, "run", return_value=mock_response):
            intent = await processor._classify_intent("Search for patient Smith")

            assert intent["agent"] == "chart_agent"
            assert intent["confidence"] == 0.95
            assert len(intent["workflow"]) == 0

    @pytest.mark.asyncio
    async def test_classify_intent_multi_agent(self, processor):
        """Test intent classification for multi-agent workflow"""
        mock_response = Mock()
        mock_response.content = """
        {
            "agent": "team",
            "confidence": 0.85,
            "workflow": ["chart_agent", "order_agent", "messaging_agent"],
            "reasoning": "Complex workflow requiring multiple agents"
        }
        """

        with patch.object(processor.coordinator, "run", return_value=mock_response):
            intent = await processor._classify_intent(
                "Find patient, order CBC, send notification"
            )

            assert intent["agent"] == "team"
            assert len(intent["workflow"]) == 3
            assert "chart_agent" in intent["workflow"]

    def test_keyword_based_routing_single(self, processor):
        """Test fallback keyword routing for single agent"""
        # Test chart agent keywords
        intent = processor._keyword_based_routing("search for patient john")
        assert intent["agent"] == "chart_agent"
        assert intent["confidence"] > 0.5

        # Test order agent keywords
        intent = processor._keyword_based_routing("order cbc test")
        assert intent["agent"] == "order_agent"

        # Test messaging agent keywords
        intent = processor._keyword_based_routing("send message to patient")
        assert intent["agent"] == "messaging_agent"

    def test_keyword_based_routing_multi(self, processor):
        """Test fallback keyword routing for multi-agent"""
        intent = processor._keyword_based_routing("find patient and order labs")
        assert intent["agent"] == "team"
        assert len(intent["workflow"]) > 1
        assert "chart_agent" in intent["workflow"]
        assert "order_agent" in intent["workflow"]

    @pytest.mark.asyncio
    async def test_process_voice_command_single_agent(self, processor):
        """Test processing single agent command"""
        # Mock intent classification
        with patch.object(
            processor,
            "_classify_intent",
            return_value={
                "agent": "chart_agent",
                "confidence": 0.9,
                "workflow": [],
                "reasoning": "Patient search",
            },
        ):
            # Mock agent response
            mock_agent_response = AgentResponse(
                success=True,
                message="Found patient John Smith",
                data={"patient_id": "123"},
            )

            with patch.object(
                processor.chart_agent,
                "process_command",
                return_value=mock_agent_response,
            ):
                response = await processor.process_voice_command("Find patient Smith")

                assert response.success is True
                assert "John Smith" in response.message
                assert response.data["routing"]["agent"] == "chart_agent"

    @pytest.mark.asyncio
    async def test_process_voice_command_team(self, processor):
        """Test processing multi-agent team command"""
        # Mock intent classification
        with patch.object(
            processor,
            "_classify_intent",
            return_value={
                "agent": "team",
                "confidence": 0.85,
                "workflow": ["chart_agent", "order_agent"],
                "reasoning": "Multi-step workflow",
            },
        ):
            # Mock team response
            mock_team_response = Mock()
            mock_team_response.content = "Completed: Found patient, created order"

            with patch.object(processor.team, "run", return_value=mock_team_response):
                response = await processor.process_voice_command(
                    "Find patient Smith and order CBC"
                )

                assert response.success is True
                assert "Completed" in response.message
                assert response.data["team_execution"] is True
                assert len(response.data["workflow"]) == 2

    @pytest.mark.asyncio
    async def test_process_command_with_context(self, processor):
        """Test processing command with context"""
        context = {"patient_id": "123", "provider": "Dr. Smith", "location": "ICU"}

        with patch.object(
            processor,
            "_classify_intent",
            return_value={
                "agent": "order_agent",
                "confidence": 0.95,
                "workflow": [],
                "reasoning": "Order command",
            },
        ):
            mock_response = AgentResponse(
                success=True, message="Order created", data={}
            )

            with patch.object(
                processor.order_agent, "process_command", return_value=mock_response
            ) as mock_process:
                await processor.process_voice_command("Order CBC", context)

                # Verify context was passed
                mock_process.assert_called_once()
                call_args = mock_process.call_args
                assert call_args[0][0] == "Order CBC"
                assert call_args[0][1] == context

    @pytest.mark.asyncio
    async def test_error_handling_invalid_agent(self, processor):
        """Test error handling for invalid agent"""
        with patch.object(
            processor,
            "_classify_intent",
            return_value={
                "agent": "invalid_agent",
                "confidence": 0.9,
                "workflow": [],
                "reasoning": "Unknown",
            },
        ):
            response = await processor.process_voice_command("Test command")

            assert response.success is False
            assert "Unknown agent" in response.message

    @pytest.mark.asyncio
    async def test_error_handling_agent_failure(self, processor):
        """Test error handling when agent fails"""
        with patch.object(
            processor,
            "_classify_intent",
            return_value={
                "agent": "chart_agent",
                "confidence": 0.9,
                "workflow": [],
                "reasoning": "Chart command",
            },
        ):
            with patch.object(
                processor.chart_agent,
                "process_command",
                side_effect=Exception("Agent error"),
            ):
                response = await processor.process_voice_command("Find patient")

                assert response.success is False
                assert "Error processing command" in response.message

    @pytest.mark.asyncio
    async def test_team_workflow_error_handling(self, processor):
        """Test error handling in team workflow"""
        with patch.object(
            processor,
            "_classify_intent",
            return_value={
                "agent": "team",
                "confidence": 0.9,
                "workflow": ["chart_agent", "order_agent"],
                "reasoning": "Team workflow",
            },
        ):
            with patch.object(
                processor.team, "run", side_effect=Exception("Team execution failed")
            ):
                response = await processor.process_voice_command("Complex command")

                assert response.success is False
                assert "Team workflow error" in response.message


class TestPerformanceTracking:
    """Test performance tracking integration"""

    @pytest.mark.asyncio
    async def test_performance_decorators(self):
        """Test that performance tracking decorators work"""
        from src.utils.metrics import performance_metrics, track_performance

        # Clear metrics
        performance_metrics.clear_metrics()

        # Create processor
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            processor = CommandProcessor("openai")

            # Mock responses
            with patch.object(
                processor,
                "_classify_intent",
                return_value={
                    "agent": "chart_agent",
                    "confidence": 0.9,
                    "workflow": [],
                    "reasoning": "Test",
                },
            ):
                mock_response = AgentResponse(success=True, message="Test", data={})

                with patch.object(
                    processor.chart_agent, "process_command", return_value=mock_response
                ):
                    await processor.process_voice_command("Test")

        # Check metrics were recorded
        stats = performance_metrics.get_stats()
        assert stats["total_operations"] > 0
        assert "classify_intent" in stats["operations"]
        assert "process_command" in stats["operations"]
