import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.orchestration.command_processor import CommandProcessor
from src.agents.chart_agent import ChartAgent
from src.agents.order_agent import OrderAgent
from src.agents.messaging_agent import MessagingAgent
from src.emr.client import Patient, Order


@pytest.fixture
def mock_emr_responses():
    return {
        "patient": Patient(
            id="123",
            first_name="John",
            last_name="Doe",
            date_of_birth="1980-01-01",
            medical_record_number="MRN123456",
        ),
        "order": Order(
            id="order_123",
            patient_id="123",
            order_type="lab",
            description="Complete Blood Count",
            ordered_by="Dr. Smith",
        ),
    }


@pytest.fixture
def command_processor():
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
        processor = CommandProcessor("openai")

        # Register all agents
        chart_agent = ChartAgent("openai")
        order_agent = OrderAgent("openai")
        messaging_agent = MessagingAgent("openai")

        processor.register_agent(chart_agent)
        processor.register_agent(order_agent)
        processor.register_agent(messaging_agent)

        return processor


@pytest.mark.asyncio
async def test_full_workflow_chart_search(command_processor, mock_emr_responses):
    """Test complete workflow: voice command -> intent classification -> agent execution"""

    # Mock the LLM response for intent classification
    with patch.object(
        command_processor,
        "_classify_intent",
        return_value={
            "agent": "chart_agent",
            "confidence": 0.9,
            "intent": "search_patients",
        },
    ):
        # Mock the chart agent's function extraction
        chart_agent = command_processor.agents["chart_agent"]
        with patch.object(
            chart_agent,
            "_extract_function_call",
            return_value={
                "function": "search_patients",
                "parameters": {"query": "John Doe"},
            },
        ):
            # Mock EMR client response
            with patch.object(
                chart_agent.emr_client,
                "search_patients",
                return_value=[mock_emr_responses["patient"]],
            ):

                response = await command_processor.process_voice_command(
                    "Search for John Doe"
                )

                assert response.success is True
                assert "John Doe" in response.message
                assert len(response.data["patients"]) == 1


@pytest.mark.asyncio
async def test_full_workflow_order_creation(command_processor, mock_emr_responses):
    """Test complete workflow for order creation"""

    with patch.object(
        command_processor,
        "_classify_intent",
        return_value={
            "agent": "order_agent",
            "confidence": 0.9,
            "intent": "create_lab_order",
        },
    ):
        order_agent = command_processor.agents["order_agent"]
        with patch.object(
            order_agent,
            "_extract_function_call",
            return_value={
                "function": "create_lab_order",
                "parameters": {
                    "patient_id": "123",
                    "lab_type": "cbc",
                    "ordered_by": "Dr. Smith",
                },
            },
        ):
            with patch.object(
                order_agent.emr_client,
                "create_order",
                return_value=mock_emr_responses["order"],
            ):

                response = await command_processor.process_voice_command(
                    "Order CBC for patient 123"
                )

                assert response.success is True
                assert "Complete Blood Count" in response.message
                assert response.data["order"]["order_type"] == "lab"


@pytest.mark.asyncio
async def test_full_workflow_messaging(command_processor, mock_emr_responses):
    """Test complete workflow for patient messaging"""

    with patch.object(
        command_processor,
        "_classify_intent",
        return_value={
            "agent": "messaging_agent",
            "confidence": 0.9,
            "intent": "send_message",
        },
    ):
        messaging_agent = command_processor.agents["messaging_agent"]
        with patch.object(
            messaging_agent,
            "_extract_function_call",
            return_value={
                "function": "send_patient_message",
                "parameters": {
                    "patient_id": "123",
                    "message": "Your lab results are ready",
                    "message_type": "lab_results",
                },
            },
        ):
            with patch.object(
                messaging_agent.emr_client,
                "get_patient_by_id",
                return_value=mock_emr_responses["patient"],
            ):
                with patch.object(
                    messaging_agent.emr_client,
                    "send_patient_message",
                    return_value=True,
                ):

                    response = await command_processor.process_voice_command(
                        "Send message to patient 123 about lab results"
                    )

                    assert response.success is True
                    assert "John Doe" in response.message
                    assert "lab results are ready" in response.data["message"]


@pytest.mark.asyncio
async def test_unknown_agent_handling(command_processor):
    """Test handling of commands that don't match any agent"""

    with patch.object(
        command_processor,
        "_classify_intent",
        return_value={"agent": "unknown_agent", "confidence": 0.1, "intent": "unknown"},
    ):
        response = await command_processor.process_voice_command("Do something unknown")

        assert response.success is False
        assert "No suitable agent found" in response.message


@pytest.mark.asyncio
async def test_error_handling_in_workflow(command_processor):
    """Test error handling throughout the workflow"""

    with patch.object(
        command_processor,
        "_classify_intent",
        return_value={
            "agent": "chart_agent",
            "confidence": 0.9,
            "intent": "search_patients",
        },
    ):
        chart_agent = command_processor.agents["chart_agent"]
        with patch.object(
            chart_agent,
            "_extract_function_call",
            return_value={
                "function": "search_patients",
                "parameters": {"query": "John Doe"},
            },
        ):
            # Mock EMR client to raise exception
            with patch.object(
                chart_agent.emr_client,
                "search_patients",
                side_effect=Exception("EMR connection failed"),
            ):

                response = await command_processor.process_voice_command(
                    "Search for John Doe"
                )

                assert response.success is False
                assert "EMR connection failed" in response.message


@pytest.mark.asyncio
async def test_performance_tracking():
    """Test that performance metrics are collected"""
    from src.utils.metrics import performance_metrics, track_performance

    performance_metrics.clear_metrics()

    @track_performance("test_operation")
    async def test_async_function():
        await asyncio.sleep(0.1)
        return "completed"

    result = await test_async_function()

    assert result == "completed"
    metrics = performance_metrics.get_metrics("test_operation")
    assert len(metrics) == 1
    assert metrics[0]["duration_seconds"] >= 0.1
