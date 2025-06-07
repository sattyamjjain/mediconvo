.PHONY: help install test run demo clean lint format check-env

# Default target
help:
	@echo "Mediconvo - Agno-Powered Voice EMR Assistant"
	@echo "==========================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make test        - Run all tests"
	@echo "  make test-unit   - Run unit tests only"
	@echo "  make test-cov    - Run tests with coverage report"
	@echo "  make run         - Start the FastAPI server"
	@echo "  make demo        - Run interactive demo"
	@echo "  make clean       - Clean up cache and temp files"
	@echo "  make lint        - Run code linting"
	@echo "  make format      - Format code with black"
	@echo "  make check-env   - Check environment setup"

# Install dependencies
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt 2>/dev/null || true

# Run tests
test:
	pytest

test-unit:
	pytest -m "not integration"

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term

# Run the application
run: check-env
	python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Run demo
demo: check-env
	python demo.py

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -f demo_metrics_*.json
	rm -f metrics_*.json

# Linting
lint:
	python -m flake8 src tests --max-line-length=100 --ignore=E203,W503
	python -m mypy src --ignore-missing-imports

# Format code
format:
	python -m black src tests --line-length=100
	python -m isort src tests

# Check environment
check-env:
	@echo "Checking environment setup..."
	@python -c "import os; assert os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY'), 'No API key found'"
	@echo "✓ API keys configured"
	@python -c "import os; assert os.getenv('EMR_BASE_URL'), 'EMR_BASE_URL not set'"
	@echo "✓ EMR configuration found"
	@echo "Environment check passed!"

# Development setup
dev-setup:
	python -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source venv/bin/activate  # On Unix/macOS"
	@echo "  venv\\Scripts\\activate   # On Windows"
	@echo "Then run: make install"

# Docker commands (future implementation)
docker-build:
	docker build -t mediconvo:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env mediconvo:latest