import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.agents.chart_agent import ChartAgent
from src.emr.client import Patient


@pytest.fixture
def chart_agent():
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
        return ChartAgent()


@pytest.fixture
def mock_patient():
    return Patient(
        id="123",
        first_name="John",
        last_name="Doe",
        date_of_birth="1980-01-01",
        medical_record_number="MRN123456",
    )


@pytest.mark.asyncio
async def test_chart_agent_initialization(chart_agent):
    assert chart_agent.name == "chart_agent"
    assert "chart" in chart_agent.description.lower()
    functions = chart_agent.get_available_functions()
    assert len(functions) == 3
    function_names = [f["name"] for f in functions]
    assert "search_patients" in function_names
    assert "open_chart" in function_names
    assert "get_patient_info" in function_names


@pytest.mark.asyncio
async def test_search_patients_success(chart_agent, mock_patient):
    with patch.object(
        chart_agent,
        "_extract_function_call",
        return_value={"function": "search_patients", "parameters": {"query": "John"}},
    ):
        with patch.object(
            chart_agent.emr_client, "search_patients", return_value=[mock_patient]
        ):
            response = await chart_agent.process_command("Search for John")

            assert response.success is True
            assert "John Doe" in response.message
            assert len(response.data["patients"]) == 1
            assert response.data["patients"][0]["name"] == "John Doe"


@pytest.mark.asyncio
async def test_open_chart_success(chart_agent, mock_patient):
    with patch.object(
        chart_agent,
        "_extract_function_call",
        return_value={
            "function": "open_chart",
            "parameters": {"patient_identifier": "John Doe"},
        },
    ):
        with patch.object(
            chart_agent.emr_client, "search_patients", return_value=[mock_patient]
        ):
            with patch.object(
                chart_agent.emr_client,
                "get_patient_chart",
                return_value={"notes": "Patient is healthy"},
            ):
                response = await chart_agent.process_command("Open John Doe's chart")

                assert response.success is True
                assert "Opened chart for John Doe" in response.message
                assert response.data["patient"]["name"] == "John Doe"
                assert "chart" in response.data


@pytest.mark.asyncio
async def test_search_patients_no_results(chart_agent):
    with patch.object(
        chart_agent,
        "_extract_function_call",
        return_value={
            "function": "search_patients",
            "parameters": {"query": "NonexistentPatient"},
        },
    ):
        with patch.object(chart_agent.emr_client, "search_patients", return_value=[]):
            response = await chart_agent.process_command(
                "Search for NonexistentPatient"
            )

            assert response.success is True
            assert "No patients found" in response.message
            assert len(response.data["patients"]) == 0
