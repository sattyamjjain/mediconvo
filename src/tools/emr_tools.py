from typing import List, Dict, Any, Optional
from agno.tools import Tool
from src.emr.client import EMRClient, Patient, Order
import logging

logger = logging.getLogger(__name__)


class EMRTools(Tool):
    def __init__(self):
        super().__init__(
            name="emr_tools",
            description="Tools for interacting with Electronic Medical Records (EMR) system",
        )
        self.emr_client = EMRClient()

    def search_patients(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for patients by name, medical record number, or other identifiers.

        Args:
            query: Search query (patient name, MRN, etc.)
            limit: Maximum number of results to return (default 10)

        Returns:
            List of patient dictionaries with id, name, mrn, and date_of_birth
        """
        try:
            import asyncio

            patients = asyncio.run(self.emr_client.search_patients(query, limit))

            if not patients:
                return []

            patient_list = []
            for patient in patients:
                patient_list.append(
                    {
                        "id": patient.id,
                        "name": f"{patient.first_name} {patient.last_name}",
                        "mrn": patient.medical_record_number,
                        "date_of_birth": patient.date_of_birth,
                        "phone": patient.phone,
                        "email": patient.email,
                    }
                )

            return patient_list

        except Exception as e:
            logger.error(f"Error searching patients: {e}")
            return []

    def get_patient_by_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        Get patient information by patient ID.

        Args:
            patient_id: The patient's unique identifier

        Returns:
            Patient dictionary or None if not found
        """
        try:
            import asyncio

            patient = asyncio.run(self.emr_client.get_patient_by_id(patient_id))

            if not patient:
                return None

            return {
                "id": patient.id,
                "name": f"{patient.first_name} {patient.last_name}",
                "mrn": patient.medical_record_number,
                "date_of_birth": patient.date_of_birth,
                "phone": patient.phone,
                "email": patient.email,
            }

        except Exception as e:
            logger.error(f"Error getting patient {patient_id}: {e}")
            return None

    def get_patient_chart(self, patient_id: str) -> Dict[str, Any]:
        """
        Get a patient's complete medical chart.

        Args:
            patient_id: The patient's unique identifier

        Returns:
            Dictionary containing chart data
        """
        try:
            import asyncio

            chart_data = asyncio.run(self.emr_client.get_patient_chart(patient_id))
            return chart_data

        except Exception as e:
            logger.error(f"Error getting chart for patient {patient_id}: {e}")
            return {}

    def create_lab_order(
        self, patient_id: str, lab_type: str, ordered_by: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create a laboratory order for a patient.

        Args:
            patient_id: The patient's unique identifier
            lab_type: Type of lab test (e.g., 'cbc', 'bmp', 'lipid')
            ordered_by: Name of the ordering provider

        Returns:
            Created order dictionary or None if failed
        """
        try:
            # Map common lab abbreviations to full names
            lab_mapping = {
                "cbc": "Complete Blood Count",
                "bmp": "Basic Metabolic Panel",
                "cmp": "Comprehensive Metabolic Panel",
                "lipid": "Lipid Panel",
                "hba1c": "Hemoglobin A1C",
                "tsh": "Thyroid Stimulating Hormone",
                "pt/inr": "Prothrombin Time/INR",
                "ptt": "Partial Thromboplastin Time",
                "urinalysis": "Urinalysis",
                "culture": "Blood Culture",
            }

            lab_description = lab_mapping.get(lab_type.lower(), lab_type.upper())

            order = Order(
                patient_id=patient_id,
                order_type="lab",
                description=lab_description,
                ordered_by=ordered_by,
            )

            import asyncio

            created_order = asyncio.run(self.emr_client.create_order(order))

            if created_order:
                return created_order.dict()
            return None

        except Exception as e:
            logger.error(f"Error creating lab order: {e}")
            return None

    def create_imaging_order(
        self,
        patient_id: str,
        imaging_type: str,
        ordered_by: str,
        reason: str = "Clinical indication",
    ) -> Optional[Dict[str, Any]]:
        """
        Create an imaging order for a patient.

        Args:
            patient_id: The patient's unique identifier
            imaging_type: Type of imaging (e.g., 'chest_xray', 'ct_head')
            ordered_by: Name of the ordering provider
            reason: Clinical indication for the imaging

        Returns:
            Created order dictionary or None if failed
        """
        try:
            # Map common imaging abbreviations to full names
            imaging_mapping = {
                "chest_xray": "Chest X-Ray",
                "abdominal_xray": "Abdominal X-Ray",
                "ct_head": "CT Head without contrast",
                "ct_chest": "CT Chest with contrast",
                "ct_abdomen": "CT Abdomen/Pelvis with contrast",
                "mri_brain": "MRI Brain without contrast",
                "ultrasound": "Ultrasound",
                "echo": "Echocardiogram",
            }

            imaging_description = imaging_mapping.get(
                imaging_type.lower(), imaging_type.replace("_", " ").title()
            )

            order = Order(
                patient_id=patient_id,
                order_type="imaging",
                description=f"{imaging_description} - {reason}",
                ordered_by=ordered_by,
            )

            import asyncio

            created_order = asyncio.run(self.emr_client.create_order(order))

            if created_order:
                return created_order.dict()
            return None

        except Exception as e:
            logger.error(f"Error creating imaging order: {e}")
            return None

    def create_medication_order(
        self,
        patient_id: str,
        medication: str,
        dosage: str,
        frequency: str,
        ordered_by: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a medication order for a patient.

        Args:
            patient_id: The patient's unique identifier
            medication: Name of the medication
            dosage: Medication dosage (e.g., '10mg', '5mg')
            frequency: Frequency (e.g., 'daily', 'twice daily', 'BID')
            ordered_by: Name of the ordering provider

        Returns:
            Created order dictionary or None if failed
        """
        try:
            med_description = f"{medication} {dosage} {frequency}".strip()

            order = Order(
                patient_id=patient_id,
                order_type="medication",
                description=med_description,
                ordered_by=ordered_by,
            )

            import asyncio

            created_order = asyncio.run(self.emr_client.create_order(order))

            if created_order:
                return created_order.dict()
            return None

        except Exception as e:
            logger.error(f"Error creating medication order: {e}")
            return None

    def get_patient_orders(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Get all orders for a specific patient.

        Args:
            patient_id: The patient's unique identifier

        Returns:
            List of order dictionaries
        """
        try:
            import asyncio

            orders = asyncio.run(self.emr_client.get_orders(patient_id))

            order_list = []
            for order in orders:
                order_list.append(
                    {
                        "id": order.id,
                        "type": order.order_type,
                        "description": order.description,
                        "status": order.status,
                        "ordered_by": order.ordered_by,
                        "created_at": order.created_at,
                    }
                )

            return order_list

        except Exception as e:
            logger.error(f"Error getting orders for patient {patient_id}: {e}")
            return []

    def send_patient_message(
        self, patient_id: str, message: str, message_type: str = "general"
    ) -> bool:
        """
        Send a message to a patient.

        Args:
            patient_id: The patient's unique identifier
            message: Message content to send
            message_type: Type of message (general, appointment, lab_results, etc.)

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            import asyncio

            success = asyncio.run(
                self.emr_client.send_patient_message(patient_id, message, message_type)
            )
            return success

        except Exception as e:
            logger.error(f"Error sending message to patient {patient_id}: {e}")
            return False

    def create_referral(
        self, patient_id: str, consultant_type: str, reason: str
    ) -> bool:
        """
        Create a referral to a specialist.

        Args:
            patient_id: The patient's unique identifier
            consultant_type: Type of specialist (cardiology, dermatology, etc.)
            reason: Reason for referral

        Returns:
            True if referral was created successfully, False otherwise
        """
        try:
            import asyncio

            success = asyncio.run(
                self.emr_client.create_referral(patient_id, consultant_type, reason)
            )
            return success

        except Exception as e:
            logger.error(f"Error creating referral for patient {patient_id}: {e}")
            return False
