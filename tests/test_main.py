"""
Test suite for main FastAPI application
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime
from src.agents.base_agent import AgentResponse


@pytest.fixture
def test_client():
    """Create test client"""
    with patch.dict(
        "os.environ",
        {
            "OPENAI_API_KEY": "test_key",
            "EMR_BASE_URL": "https://test.emr.com/api",
            "EMR_API_KEY": "test_emr_key",
            "SPEECH_PROVIDER": "local",
            "MODEL_PROVIDER": "openai",
        },
    ):
        from src.main import app

        return TestClient(app)


class TestAPIEndpoints:
    """Test API endpoints"""

    def test_root_endpoint(self, test_client):
        """Test root endpoint"""
        response = test_client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["application"] == "Mediconvo Voice Assistant"
        assert data["version"] == "2.0.0"
        assert data["framework"] == "Agno AI Agents"
        assert data["status"] == "operational"

    def test_health_endpoint(self, test_client):
        """Test health check endpoint"""
        response = test_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert data["components"]["speech_recognizer"] == "initialized"
        assert data["components"]["command_processor"] == "initialized"

    def test_capabilities_endpoint(self, test_client):
        """Test capabilities endpoint"""
        response = test_client.get("/capabilities")
        assert response.status_code == 200

        data = response.json()
        assert "agents" in data
        assert "total_capabilities" in data
        assert len(data["agents"]) == 3
        assert data["total_capabilities"] > 0

    def test_help_endpoint(self, test_client):
        """Test help endpoint"""
        response = test_client.get("/help")
        assert response.status_code == 200

        data = response.json()
        assert "help" in data
        assert "Chart Management" in data["help"]
        assert "Medical Orders" in data["help"]
        assert "Communication" in data["help"]

    def test_metrics_endpoint(self, test_client):
        """Test metrics endpoint"""
        response = test_client.get("/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "statistics" in data
        assert "recent_operations" in data
        assert "timestamp" in data

    def test_metrics_export_endpoint(self, test_client):
        """Test metrics export endpoint"""
        with patch(
            "src.utils.metrics.performance_metrics.export_metrics"
        ) as mock_export:
            response = test_client.post("/metrics/export")
            assert response.status_code == 200

            data = response.json()
            assert "message" in data
            assert "Metrics exported" in data["message"]
            mock_export.assert_called_once()

    def test_metrics_clear_endpoint(self, test_client):
        """Test metrics clear endpoint"""
        response = test_client.post("/metrics/clear")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Metrics cleared"

    def test_demo_commands_endpoint(self, test_client):
        """Test demo commands endpoint"""
        response = test_client.post("/demo/commands")
        assert response.status_code == 200

        data = response.json()
        assert "simple_commands" in data
        assert "complex_workflows" in data
        assert len(data["simple_commands"]) > 0
        assert len(data["complex_workflows"]) > 0


class TestCommandProcessing:
    """Test command processing endpoint"""

    def test_process_command_success(self, test_client):
        """Test successful command processing"""
        # Mock the command processor
        mock_response = AgentResponse(
            success=True,
            message="Found patient John Smith",
            data={"patient_id": "123"},
            actions_taken=["Searched for patient"],
        )

        with patch("src.main.command_processor") as mock_processor:
            mock_processor.process_voice_command = AsyncMock(return_value=mock_response)

            response = test_client.post(
                "/process-command", json={"text": "Search for John Smith"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "John Smith" in data["message"]
            assert data["data"]["patient_id"] == "123"
            assert "execution_time" in data

    def test_process_command_with_context(self, test_client):
        """Test command processing with context"""
        mock_response = AgentResponse(
            success=True, message="Order created", data={"order_id": "ORD123"}
        )

        with patch("src.main.command_processor") as mock_processor:
            mock_processor.process_voice_command = AsyncMock(return_value=mock_response)

            response = test_client.post(
                "/process-command",
                json={
                    "text": "Order CBC",
                    "context": {"patient_id": "123", "provider": "Dr. Smith"},
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify context was passed
            mock_processor.process_voice_command.assert_called_once()
            call_args = mock_processor.process_voice_command.call_args
            assert call_args[0][1]["patient_id"] == "123"

    def test_process_command_empty_text(self, test_client):
        """Test command processing with empty text"""
        response = test_client.post("/process-command", json={"text": ""})

        assert response.status_code == 400
        assert "Command text cannot be empty" in response.json()["detail"]

    def test_process_command_processor_not_initialized(self, test_client):
        """Test command processing when processor not initialized"""
        with patch("src.main.command_processor", None):
            response = test_client.post(
                "/process-command", json={"text": "Test command"}
            )

            assert response.status_code == 503
            assert "Command processor not initialized" in response.json()["detail"]

    def test_process_command_error_handling(self, test_client):
        """Test command processing error handling"""
        with patch("src.main.command_processor") as mock_processor:
            mock_processor.process_voice_command = AsyncMock(
                side_effect=Exception("Processing error")
            )

            response = test_client.post(
                "/process-command", json={"text": "Test command"}
            )

            assert response.status_code == 500
            assert "Processing error" in response.json()["detail"]


class TestWebSocket:
    """Test WebSocket endpoint"""

    def test_websocket_connection(self, test_client):
        """Test WebSocket connection and basic message flow"""
        with test_client.websocket_connect("/voice") as websocket:
            # Mock speech recognizer
            with patch("src.main.speech_recognizer") as mock_recognizer:
                # Create async generator for recognized text
                async def mock_recognize():
                    yield "Test transcript"

                mock_recognizer.recognize_stream = Mock(return_value=mock_recognize())

                # Mock command processor
                mock_response = AgentResponse(
                    success=True, message="Command processed", data={}
                )

                with patch("src.main.command_processor") as mock_processor:
                    mock_processor.process_voice_command = AsyncMock(
                        return_value=mock_response
                    )

                    # Send audio data
                    websocket.send_bytes(b"fake_audio_data")

                    # Note: Full WebSocket testing requires async test framework
                    # This is a basic connectivity test


class TestErrorHandlers:
    """Test error handlers"""

    def test_value_error_handler(self, test_client):
        """Test ValueError handler"""
        # Trigger ValueError by not providing required API key
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            with patch("src.main.startup_event", side_effect=ValueError("Test error")):
                # This would normally trigger during startup
                pass

    def test_general_exception_handler(self, test_client):
        """Test general exception handler"""
        with patch("src.main.command_processor") as mock_processor:
            mock_processor.process_voice_command = AsyncMock(
                side_effect=RuntimeError("Unexpected error")
            )

            response = test_client.post("/process-command", json={"text": "Test"})

            # Should be caught and return 500
            assert response.status_code == 500


class TestStartupShutdown:
    """Test startup and shutdown events"""

    def test_startup_missing_api_key(self):
        """Test startup with missing API key"""
        with patch.dict(
            "os.environ", {"MODEL_PROVIDER": "openai", "OPENAI_API_KEY": ""}
        ):
            from src.main import startup_event

            with pytest.raises(ValueError) as exc_info:
                import asyncio

                asyncio.run(startup_event())

            assert "OPENAI_API_KEY not found" in str(exc_info.value)

    def test_shutdown_with_metrics_export(self):
        """Test shutdown with metrics export enabled"""
        with patch.dict("os.environ", {"EXPORT_METRICS_ON_SHUTDOWN": "true"}):
            from src.main import shutdown_event

            with patch(
                "src.utils.metrics.performance_metrics.export_metrics"
            ) as mock_export:
                import asyncio

                asyncio.run(shutdown_event())

                mock_export.assert_called_once()
                # Check filename contains timestamp
                filename = mock_export.call_args[0][0]
                assert "metrics_" in filename
                assert ".json" in filename
