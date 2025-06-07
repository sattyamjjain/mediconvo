#!/bin/bash

echo "🏥 Starting Mediconvo with FHIR + Google Speech..."
echo "📍 FHIR Server: https://hapi.fhir.org/baseR4"
echo "🎤 Speech Provider: Google Cloud Speech (fallback enabled)"
echo "🤖 AI Provider: OpenAI (Agno framework)"
echo ""

# Set environment variables
export EMR_BASE_URL="https://hapi.fhir.org/baseR4"
export SPEECH_PROVIDER="google"
export MODEL_PROVIDER="openai"
export LOG_LEVEL="INFO"

# Start the server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload