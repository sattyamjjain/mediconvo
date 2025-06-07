#!/usr/bin/env python3
"""
Quick test script for live system
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_command(text, description=""):
    print(f"\n🎤 {description}")
    print(f"Command: '{text}'")
    
    response = requests.post(
        f"{BASE_URL}/process-command",
        json={"text": text},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success: {data['success']}")
        print(f"🤖 Agent: {data['data']['routing']['agent']}")
        print(f"⏱️  Time: {data['execution_time']:.2f}s")
        print(f"📝 Response: {data['message'][:100]}...")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

def main():
    print("🏥 Testing Mediconvo Voice Assistant with FHIR + Google Speech")
    print("=" * 60)
    
    # Test system info
    print("\n📊 System Status:")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        health = response.json()
        print(f"✅ Status: {health['status']}")
        print(f"🤖 Agents: {health['components']['agents']}")
    
    # Test simple commands
    test_command("Search for patients named John", "Real FHIR Patient Search")
    test_command("Order CBC for patient", "Lab Order Creation")
    test_command("Send appointment reminder to patient", "Patient Messaging")
    
    # Test complex workflow
    test_command(
        "Find patient John, order lipid panel, and send notification", 
        "Multi-Agent Workflow"
    )

if __name__ == "__main__":
    main()