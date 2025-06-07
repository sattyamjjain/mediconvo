import pytest
import asyncio
from unittest.mock import Mock, patch
from src.voice.speech_recognizer import LocalSpeechRecognizer, get_speech_recognizer


@pytest.mark.asyncio
async def test_local_speech_recognizer():
    recognizer = LocalSpeechRecognizer()
    assert recognizer is not None


@pytest.mark.asyncio
async def test_get_speech_recognizer():
    local_recognizer = get_speech_recognizer("local")
    assert isinstance(local_recognizer, LocalSpeechRecognizer)

    with pytest.raises(ValueError):
        get_speech_recognizer("invalid_provider")


@pytest.mark.asyncio
async def test_speech_recognizer_mock():
    with patch("speech_recognition.Recognizer") as mock_sr:
        mock_sr.return_value.recognize_google.return_value = "test transcription"

        recognizer = LocalSpeechRecognizer()

        # This would need actual audio file for full test
        # For now just test that the recognizer is created
        assert recognizer.recognizer is not None
