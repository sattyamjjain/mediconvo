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

        if not self.base_url:
            raise ValueError("EMR_BASE_URL environment variable is required")

    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()

    async def search_patients(self, query: str, limit: int = 10) -> List[Patient]:
        try:
            params = {"q": query, "limit": limit}
            response = await self._make_request(
                "GET", "/patients/search", params=params
            )
            return [Patient(**patient) for patient in response.get("patients", [])]
        except Exception as e:
            logger.error(f"Error searching patients: {e}")
            return []

    async def get_patient_by_id(self, patient_id: str) -> Optional[Patient]:
        try:
            response = await self._make_request("GET", f"/patients/{patient_id}")
            return Patient(**response)
        except Exception as e:
            logger.error(f"Error getting patient {patient_id}: {e}")
            return None

    async def get_patient_chart(self, patient_id: str) -> Dict[str, Any]:
        try:
            response = await self._make_request("GET", f"/patients/{patient_id}/chart")
            return response
        except Exception as e:
            logger.error(f"Error getting chart for patient {patient_id}: {e}")
            return {}

    async def create_order(self, order: Order) -> Optional[Order]:
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
