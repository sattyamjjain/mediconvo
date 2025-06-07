"""
Test suite for EMR tools
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.tools.emr_tools import EMRTools
from src.emr.client import Patient, Order


class TestEMRTools:
    """Test suite for EMR Tools"""

    @pytest.fixture
    def emr_tools(self):
        with patch.dict(
            "os.environ",
            {"EMR_BASE_URL": "https://test.emr.com/api", "EMR_API_KEY": "test_key"},
        ):
            return EMRTools()

    def test_initialization(self, emr_tools):
        """Test EMR tools initialization"""
        assert emr_tools is not None
        assert emr_tools.name == "emr_tools"
        assert emr_tools.description is not None
        assert emr_tools.emr_client is not None

    def test_search_patients(self, emr_tools):
        """Test patient search functionality"""
        # Mock patient data
        mock_patients = [
            Patient(
                id="123",
                first_name="John",
                last_name="Smith",
                date_of_birth="1980-01-01",
                medical_record_number="MRN123",
                phone="555-0123",
                email="john.smith@email.com",
            ),
            Patient(
                id="456",
                first_name="Jane",
                last_name="Smith",
                date_of_birth="1985-05-15",
                medical_record_number="MRN456",
                phone="555-0456",
                email="jane.smith@email.com",
            ),
        ]

        with patch("asyncio.run", return_value=mock_patients):
            results = emr_tools.search_patients("Smith")

            assert len(results) == 2
            assert results[0]["name"] == "John Smith"
            assert results[0]["mrn"] == "MRN123"
            assert results[1]["name"] == "Jane Smith"

    def test_search_patients_no_results(self, emr_tools):
        """Test patient search with no results"""
        with patch("asyncio.run", return_value=[]):
            results = emr_tools.search_patients("NonexistentPatient")
            assert len(results) == 0

    def test_search_patients_error_handling(self, emr_tools):
        """Test patient search error handling"""
        with patch("asyncio.run", side_effect=Exception("Connection error")):
            results = emr_tools.search_patients("Smith")
            assert len(results) == 0  # Should return empty list on error

    def test_get_patient_by_id(self, emr_tools):
        """Test getting patient by ID"""
        mock_patient = Patient(
            id="123",
            first_name="John",
            last_name="Doe",
            date_of_birth="1980-01-01",
            medical_record_number="MRN123",
            phone="555-0123",
            email="john.doe@email.com",
        )

        with patch("asyncio.run", return_value=mock_patient):
            result = emr_tools.get_patient_by_id("123")

            assert result is not None
            assert result["id"] == "123"
            assert result["name"] == "John Doe"
            assert result["mrn"] == "MRN123"

    def test_get_patient_by_id_not_found(self, emr_tools):
        """Test getting non-existent patient"""
        with patch("asyncio.run", return_value=None):
            result = emr_tools.get_patient_by_id("999")
            assert result is None

    def test_get_patient_chart(self, emr_tools):
        """Test getting patient chart"""
        mock_chart = {
            "patient_id": "123",
            "visits": [
                {"date": "2024-01-15", "type": "routine"},
                {"date": "2024-02-20", "type": "follow-up"},
            ],
            "medications": ["lisinopril", "metformin"],
            "allergies": ["penicillin"],
        }

        with patch("asyncio.run", return_value=mock_chart):
            result = emr_tools.get_patient_chart("123")

            assert result["patient_id"] == "123"
            assert len(result["visits"]) == 2
            assert "lisinopril" in result["medications"]

    def test_create_lab_order(self, emr_tools):
        """Test creating lab order"""
        mock_order = Order(
            id="ORD123",
            patient_id="123",
            order_type="lab",
            description="Complete Blood Count",
            ordered_by="Dr. Smith",
            status="pending",
        )

        with patch("asyncio.run", return_value=mock_order):
            result = emr_tools.create_lab_order(
                patient_id="123", lab_type="cbc", ordered_by="Dr. Smith"
            )

            assert result is not None
            assert result["id"] == "ORD123"
            assert result["order_type"] == "lab"
            assert result["description"] == "Complete Blood Count"

    def test_create_lab_order_with_abbreviations(self, emr_tools):
        """Test lab order creation handles abbreviations"""
        test_cases = [
            ("cbc", "Complete Blood Count"),
            ("bmp", "Basic Metabolic Panel"),
            ("cmp", "Comprehensive Metabolic Panel"),
            ("lipid", "Lipid Panel"),
            ("hba1c", "Hemoglobin A1C"),
            ("tsh", "Thyroid Stimulating Hormone"),
            ("custom_test", "CUSTOM_TEST"),  # Unknown abbreviation
        ]

        for abbreviation, expected_description in test_cases:
            mock_order = Order(
                id=f"ORD_{abbreviation}",
                patient_id="123",
                order_type="lab",
                description=expected_description,
                ordered_by="Dr. Smith",
                status="pending",
            )

            with patch("asyncio.run", return_value=mock_order):
                result = emr_tools.create_lab_order(
                    patient_id="123", lab_type=abbreviation, ordered_by="Dr. Smith"
                )

                assert result["description"] == expected_description

    def test_create_imaging_order(self, emr_tools):
        """Test creating imaging order"""
        mock_order = Order(
            id="IMG456",
            patient_id="123",
            order_type="imaging",
            description="Chest X-Ray - Rule out pneumonia",
            ordered_by="Dr. Jones",
            status="pending",
        )

        with patch("asyncio.run", return_value=mock_order):
            result = emr_tools.create_imaging_order(
                patient_id="123",
                imaging_type="chest_xray",
                ordered_by="Dr. Jones",
                reason="Rule out pneumonia",
            )

            assert result is not None
            assert result["order_type"] == "imaging"
            assert "Chest X-Ray" in result["description"]
            assert "pneumonia" in result["description"]

    def test_create_medication_order(self, emr_tools):
        """Test creating medication order"""
        mock_order = Order(
            id="MED789",
            patient_id="123",
            order_type="medication",
            description="lisinopril 10mg daily",
            ordered_by="Dr. Brown",
            status="pending",
        )

        with patch("asyncio.run", return_value=mock_order):
            result = emr_tools.create_medication_order(
                patient_id="123",
                medication="lisinopril",
                dosage="10mg",
                frequency="daily",
                ordered_by="Dr. Brown",
            )

            assert result is not None
            assert result["order_type"] == "medication"
            assert "lisinopril 10mg daily" in result["description"]

    def test_get_patient_orders(self, emr_tools):
        """Test getting patient orders"""
        mock_orders = [
            Order(
                id="ORD1",
                patient_id="123",
                order_type="lab",
                description="CBC",
                ordered_by="Dr. Smith",
                status="completed",
            ),
            Order(
                id="ORD2",
                patient_id="123",
                order_type="imaging",
                description="Chest X-Ray",
                ordered_by="Dr. Jones",
                status="pending",
            ),
        ]

        with patch("asyncio.run", return_value=mock_orders):
            results = emr_tools.get_patient_orders("123")

            assert len(results) == 2
            assert results[0]["type"] == "lab"
            assert results[1]["type"] == "imaging"

    def test_send_patient_message(self, emr_tools):
        """Test sending patient message"""
        with patch("asyncio.run", return_value=True):
            result = emr_tools.send_patient_message(
                patient_id="123",
                message="Your appointment is tomorrow at 2 PM",
                message_type="appointment",
            )

            assert result is True

    def test_send_patient_message_failure(self, emr_tools):
        """Test message sending failure"""
        with patch("asyncio.run", return_value=False):
            result = emr_tools.send_patient_message(
                patient_id="123", message="Test message", message_type="general"
            )

            assert result is False

    def test_create_referral(self, emr_tools):
        """Test creating referral"""
        with patch("asyncio.run", return_value=True):
            result = emr_tools.create_referral(
                patient_id="123",
                consultant_type="cardiology",
                reason="Chest pain evaluation",
            )

            assert result is True

    def test_create_referral_failure(self, emr_tools):
        """Test referral creation failure"""
        with patch("asyncio.run", return_value=False):
            result = emr_tools.create_referral(
                patient_id="123", consultant_type="dermatology", reason="Skin rash"
            )

            assert result is False

    def test_error_handling_all_methods(self, emr_tools):
        """Test error handling for all methods"""
        with patch("asyncio.run", side_effect=Exception("Test error")):
            # Test all methods handle errors gracefully
            assert emr_tools.search_patients("test") == []
            assert emr_tools.get_patient_by_id("123") is None
            assert emr_tools.get_patient_chart("123") == {}
            assert emr_tools.create_lab_order("123", "cbc", "Dr. Test") is None
            assert emr_tools.create_imaging_order("123", "xray", "Dr. Test") is None
            assert (
                emr_tools.create_medication_order(
                    "123", "med", "10mg", "daily", "Dr. Test"
                )
                is None
            )
            assert emr_tools.get_patient_orders("123") == []
            assert emr_tools.send_patient_message("123", "test") is False
            assert emr_tools.create_referral("123", "cardiology", "test") is False
