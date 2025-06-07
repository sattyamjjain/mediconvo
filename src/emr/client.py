import os
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class Patient(BaseModel):
    id: str
    first_name: str
    last_name: str
    date_of_birth: str
    medical_record_number: str
    phone: Optional[str] = None
    email: Optional[str] = None


class Order(BaseModel):
    id: Optional[str] = None
    patient_id: str
    order_type: str  # "lab", "imaging", "medication"
    description: str
    status: str = "pending"
    ordered_by: str
    created_at: Optional[str] = None


class EMRClient:
    def __init__(self):
        self.base_url = os.getenv("EMR_BASE_URL")
        self.api_key = os.getenv("EMR_API_KEY")
        self.client_id = os.getenv("EMR_CLIENT_ID")
        self.client_secret = os.getenv("EMR_CLIENT_SECRET")

        # Use demo mode if no EMR credentials are provided
        self.demo_mode = not self.base_url

        if self.demo_mode:
            logger.warning(
                "EMR_BASE_URL not found. Running in demo mode with mock data."
            )
            self.base_url = "http://demo-emr-api.local"
            self.is_fhir = False
        else:
            # Check if this is a FHIR server
            self.is_fhir = "fhir" in self.base_url.lower()
            if self.is_fhir:
                logger.info("Detected FHIR server, using FHIR format")

    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/fhir+json" if self.is_fhir else "application/json",
        }
        
        # Only add auth header if we have an API key
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()

    def _parse_fhir_patient(self, fhir_patient: Dict) -> Patient:
        """Parse FHIR Patient resource to our Patient model"""
        # Extract names
        names = fhir_patient.get("name", [{}])
        first_name = ""
        last_name = ""
        
        if names:
            given = names[0].get("given", [])
            family = names[0].get("family", "")
            first_name = " ".join(given) if given else ""
            last_name = family

        # Extract identifiers
        identifiers = fhir_patient.get("identifier", [])
        mrn = ""
        for identifier in identifiers:
            if identifier.get("use") == "usual" or not mrn:
                mrn = identifier.get("value", "")

        # Extract contact info
        telecoms = fhir_patient.get("telecom", [])
        phone = ""
        email = ""
        
        for telecom in telecoms:
            if telecom.get("system") == "phone" and not phone:
                phone = telecom.get("value", "")
            elif telecom.get("system") == "email" and not email:
                email = telecom.get("value", "")

        return Patient(
            id=fhir_patient.get("id", ""),
            first_name=first_name,
            last_name=last_name,
            date_of_birth=fhir_patient.get("birthDate", ""),
            medical_record_number=mrn,
            phone=phone,
            email=email
        )

    async def search_patients(self, query: str, limit: int = 10) -> List[Patient]:
        if self.demo_mode:
            # Return mock patient data
            mock_patients = [
                Patient(
                    id="123",
                    first_name="John",
                    last_name="Doe",
                    date_of_birth="1980-01-15",
                    medical_record_number="MRN123",
                    phone="555-0123",
                    email="john.doe@email.com",
                ),
                Patient(
                    id="456",
                    first_name="Jane",
                    last_name="Smith",
                    date_of_birth="1975-06-22",
                    medical_record_number="MRN456",
                    phone="555-0456",
                    email="jane.smith@email.com",
                ),
            ]
            # Filter by query
            filtered = [
                p
                for p in mock_patients
                if query.lower() in f"{p.first_name} {p.last_name}".lower()
                or query in p.medical_record_number
            ]
            return filtered[:limit]

        try:
            if self.is_fhir:
                # FHIR Patient search
                params = {
                    "name": query,
                    "_count": limit,
                    "_sort": "-_lastUpdated"
                }
                response = await self._make_request("GET", "Patient", params=params)
                
                patients = []
                for entry in response.get("entry", []):
                    if "resource" in entry:
                        patients.append(self._parse_fhir_patient(entry["resource"]))
                return patients
            else:
                # Custom API format
                params = {"q": query, "limit": limit}
                response = await self._make_request(
                    "GET", "/patients/search", params=params
                )
                return [Patient(**patient) for patient in response.get("patients", [])]
        except Exception as e:
            logger.error(f"Error searching patients: {e}")
            return []

    async def get_patient_by_id(self, patient_id: str) -> Optional[Patient]:
        if self.demo_mode:
            # Return mock patient data
            if patient_id == "123":
                return Patient(
                    id="123",
                    first_name="John",
                    last_name="Doe",
                    date_of_birth="1980-01-15",
                    medical_record_number="MRN123",
                    phone="555-0123",
                    email="john.doe@email.com",
                )
            elif patient_id == "456":
                return Patient(
                    id="456",
                    first_name="Jane",
                    last_name="Smith",
                    date_of_birth="1975-06-22",
                    medical_record_number="MRN456",
                    phone="555-0456",
                    email="jane.smith@email.com",
                )
            return None

        try:
            if self.is_fhir:
                # FHIR Patient read
                response = await self._make_request("GET", f"Patient/{patient_id}")
                return self._parse_fhir_patient(response)
            else:
                # Custom API format
                response = await self._make_request("GET", f"/patients/{patient_id}")
                return Patient(**response)
        except Exception as e:
            logger.error(f"Error getting patient {patient_id}: {e}")
            return None

    async def get_patient_chart(self, patient_id: str) -> Dict[str, Any]:
        if self.demo_mode:
            return {
                "patient_id": patient_id,
                "chart_data": "Demo chart data for patient",
                "last_visit": "2024-01-15",
                "allergies": ["Penicillin"],
                "medications": ["Lisinopril 10mg daily"],
                "note": "This is demo data - no real EMR connection",
            }

        try:
            response = await self._make_request("GET", f"/patients/{patient_id}/chart")
            return response
        except Exception as e:
            logger.error(f"Error getting chart for patient {patient_id}: {e}")
            return {}

    async def create_order(self, order: Order) -> Optional[Order]:
        if self.demo_mode:
            # Return the order with an ID and timestamp
            import uuid
            from datetime import datetime

            order.id = str(uuid.uuid4())[:8]
            order.created_at = datetime.now().isoformat()
            logger.info(
                f"Demo mode: Created order {order.id} for patient {order.patient_id}"
            )
            return order

        try:
            response = await self._make_request("POST", "/orders", json=order.dict())
            return Order(**response)
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    async def get_orders(self, patient_id: str) -> List[Order]:
        try:
            params = {"patient_id": patient_id}
            response = await self._make_request("GET", "/orders", params=params)
            return [Order(**order) for order in response.get("orders", [])]
        except Exception as e:
            logger.error(f"Error getting orders for patient {patient_id}: {e}")
            return []

    async def send_patient_message(
        self, patient_id: str, message: str, message_type: str = "general"
    ) -> bool:
        if self.demo_mode:
            logger.info(
                f"Demo mode: Sent {message_type} message to patient {patient_id}: {message[:50]}..."
            )
            return True

        try:
            data = {"patient_id": patient_id, "message": message, "type": message_type}
            await self._make_request("POST", "/messages", json=data)
            return True
        except Exception as e:
            logger.error(f"Error sending message to patient {patient_id}: {e}")
            return False

    async def create_referral(
        self, patient_id: str, consultant_type: str, reason: str
    ) -> bool:
        if self.demo_mode:
            logger.info(
                f"Demo mode: Created {consultant_type} referral for patient {patient_id}: {reason}"
            )
            return True

        try:
            data = {
                "patient_id": patient_id,
                "consultant_type": consultant_type,
                "reason": reason,
            }
            await self._make_request("POST", "/referrals", json=data)
            return True
        except Exception as e:
            logger.error(f"Error creating referral for patient {patient_id}: {e}")
            return False
