"""
Mediconvo Voice Assistant - Agno-Powered EMR System
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.voice.speech_recognizer import get_speech_recognizer
from src.orchestration.command_processor import CommandProcessor
from src.utils.metrics import performance_metrics

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Mediconvo Voice Assistant",
    description="Agno-powered voice-activated EMR assistant for healthcare providers",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
speech_recognizer = None
command_processor = None


# Request/Response models
class CommandRequest(BaseModel):
    text: str
    context: Optional[Dict[str, Any]] = None


class CommandResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any] = {}
    actions_taken: list = []
    execution_time: Optional[float] = None
    timestamp: str = datetime.now().isoformat()


# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global speech_recognizer, command_processor

    try:
        # Get configuration
        speech_provider = os.getenv("SPEECH_PROVIDER", "local")
        model_provider = os.getenv("MODEL_PROVIDER", "openai")

        # Validate API keys
        if model_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment")
        elif model_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        # Initialize components
        speech_recognizer = get_speech_recognizer(speech_provider)
        command_processor = CommandProcessor(model_provider)

        logger.info(f"Speech recognizer initialized: {speech_provider}")
        logger.info(f"Command processor initialized with Agno: {model_provider}")
        logger.info("Mediconvo Voice Assistant started successfully!")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Mediconvo Voice Assistant")
    # Export metrics if configured
    if os.getenv("EXPORT_METRICS_ON_SHUTDOWN", "false").lower() == "true":
        performance_metrics.export_metrics(f"metrics_{datetime.now().isoformat()}.json")


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "application": "Mediconvo Voice Assistant",
        "version": "2.0.0",
        "framework": "Agno AI Agents",
        "status": "operational",
        "agents": (
            command_processor.get_registered_agents() if command_processor else []
        ),
        "documentation": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "speech_recognizer": (
                "initialized" if speech_recognizer else "not initialized"
            ),
            "command_processor": (
                "initialized" if command_processor else "not initialized"
            ),
            "agents": (
                command_processor.get_registered_agents() if command_processor else []
            ),
        },
    }

    # Check if all components are initialized
    if not speech_recognizer or not command_processor:
        health_status["status"] = "degraded"

    return health_status


@app.post("/process-command", response_model=CommandResponse)
async def process_command(request: CommandRequest):
    """Process a text command through the agent system"""
    if not command_processor:
        raise HTTPException(status_code=503, detail="Command processor not initialized")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Command text cannot be empty")

    try:
        # Start timing
        start_time = asyncio.get_event_loop().time()

        # Process command
        response = await command_processor.process_voice_command(
            request.text, request.context
        )

        # Calculate execution time
        execution_time = asyncio.get_event_loop().time() - start_time

        # Return response
        return CommandResponse(
            success=response.success,
            message=response.message,
            data=response.data,
            actions_taken=response.actions_taken,
            execution_time=execution_time,
        )

    except Exception as e:
        logger.error(f"Error processing command: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/capabilities")
async def get_capabilities():
    """Get detailed capabilities of all agents"""
    if not command_processor:
        raise HTTPException(status_code=503, detail="Command processor not initialized")

    return {
        "agents": command_processor.get_agent_capabilities(),
        "total_capabilities": sum(
            len(caps) for caps in command_processor.get_agent_capabilities().values()
        ),
    }


@app.get("/help")
async def get_help():
    """Get help information"""
    if not command_processor:
        raise HTTPException(status_code=503, detail="Command processor not initialized")

    help_text = await command_processor.get_help()
    return {"help": help_text}


@app.get("/metrics")
async def get_metrics():
    """Get performance metrics"""
    stats = performance_metrics.get_stats()
    recent = performance_metrics.get_metrics()[-20:]  # Last 20 operations

    return {
        "statistics": stats,
        "recent_operations": recent,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/metrics/export")
async def export_metrics():
    """Export metrics to file"""
    filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        performance_metrics.export_metrics(filename)
        return {"message": f"Metrics exported to {filename}"}
    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/metrics/clear")
async def clear_metrics():
    """Clear performance metrics"""
    performance_metrics.clear_metrics()
    return {"message": "Metrics cleared"}


# WebSocket for real-time voice processing
@app.websocket("/voice")
async def voice_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time voice processing"""
    await websocket.accept()
    logger.info("Voice WebSocket connection established")

    try:
        while True:
            # Receive audio data
            data = await websocket.receive_bytes()

            # Process through speech recognition
            async for transcript in speech_recognizer.recognize_stream(data):
                if transcript.strip():
                    logger.info(f"Recognized: {transcript}")

                    # Process command
                    start_time = asyncio.get_event_loop().time()
                    response = await command_processor.process_voice_command(transcript)
                    execution_time = asyncio.get_event_loop().time() - start_time

                    # Send response
                    await websocket.send_json(
                        {
                            "transcript": transcript,
                            "response": {
                                "success": response.success,
                                "message": response.message,
                                "data": response.data,
                                "execution_time": execution_time,
                            },
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info("Voice WebSocket connection closed")
        await websocket.close()


# Demo endpoints
@app.post("/demo/commands")
async def demo_commands():
    """Get demo commands for testing"""
    return {
        "simple_commands": [
            "Search for patient John Smith",
            "Open chart for patient 12345",
            "Order CBC for current patient",
            "Get chest X-ray for patient Doe",
            "Prescribe lisinopril 10mg daily",
            "Send appointment reminder to patient",
            "Refer patient to cardiology",
        ],
        "complex_workflows": [
            "Find patient Smith, order CBC, and send notification",
            "Open chart for 12345, prescribe metformin, notify patient",
            "Search for Johnson, create cardiology referral with urgent priority",
        ],
    }


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    # Get configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"

    # Run server
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
