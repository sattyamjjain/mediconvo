#!/bin/bash

# Mediconvo Voice Assistant Startup Script

echo "Starting Mediconvo Voice Assistant..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your API keys and configuration"
    echo "Required: OPENAI_API_KEY or ANTHROPIC_API_KEY"
    exit 1
fi

# Run the application
echo "Starting FastAPI server..."
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload