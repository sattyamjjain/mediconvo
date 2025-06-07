#!/usr/bin/env python3
"""Quick test script for FHIR connectivity"""
import asyncio
import os
from src.emr.client import EMRClient

async def test_fhir():
    os.environ['EMR_BASE_URL'] = 'https://hapi.fhir.org/baseR4'
    
    client = EMRClient()
    print(f"🏥 EMR Client initialized")
    print(f"📍 Base URL: {client.base_url}")
    print(f"🔬 FHIR Mode: {client.is_fhir}")
    print(f"🎮 Demo Mode: {client.demo_mode}")
    
    print("\n🔍 Testing patient search...")
    try:
        patients = await client.search_patients("John", limit=3)
        print(f"✅ Found {len(patients)} patients")
        for patient in patients:
            print(f"   - {patient.first_name} {patient.last_name} (ID: {patient.id})")
        
        if patients:
            print(f"\n👤 Testing patient details for ID: {patients[0].id}")
            patient = await client.get_patient_by_id(patients[0].id)
            if patient:
                print(f"✅ Patient details retrieved:")
                print(f"   Name: {patient.first_name} {patient.last_name}")
                print(f"   DOB: {patient.date_of_birth}")
                print(f"   MRN: {patient.medical_record_number}")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_fhir())