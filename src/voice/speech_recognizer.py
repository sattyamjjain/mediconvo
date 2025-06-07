import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator
import speech_recognition as sr
from google.cloud import speech
import boto3
import logging

logger = logging.getLogger(__name__)


class SpeechRecognizer(ABC):
    @abstractmethod
    async def recognize_stream(self, audio_stream) -> AsyncIterator[str]:
        pass

    @abstractmethod
    async def recognize_file(self, audio_file_path: str) -> str:
        pass


class GoogleSpeechRecognizer(SpeechRecognizer):
    def __init__(self):
        try:
            self.client = speech.SpeechClient()
            self.config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-US",
                model="medical_dictation",
                use_enhanced=True,
                enable_automatic_punctuation=True,
            )
            logger.info("Google Cloud Speech initialized successfully")
        except Exception as e:
            logger.warning(f"Google Cloud Speech initialization failed: {e}")
            # Fall back to basic speech recognition via speech_recognition library
            import speech_recognition as sr
            self.client = None
            self.recognizer = sr.Recognizer()
            logger.info("Falling back to speech_recognition with Google API")

    async def recognize_stream(self, audio_stream) -> AsyncIterator[str]:
        if self.client:
            # Use Google Cloud Speech API
            streaming_config = speech.StreamingRecognitionConfig(
                config=self.config,
                interim_results=True,
            )

            audio_generator = self._audio_generator(audio_stream)
            requests = (
                speech.StreamingRecognizeRequest(audio_content=chunk)
                for chunk in audio_generator
            )

            responses = self.client.streaming_recognize(streaming_config, requests)

            for response in responses:
                for result in response.results:
                    if result.is_final:
                        yield result.alternatives[0].transcript
        else:
            # Fall back to speech_recognition library
            import speech_recognition as sr
            with sr.AudioFile(audio_stream) as source:
                audio = self.recognizer.record(source)
            try:
                text = self.recognizer.recognize_google(audio)
                yield text
            except sr.UnknownValueError:
                logger.warning("Could not understand audio")
            except sr.RequestError as e:
                logger.error(f"Could not request results; {e}")

    async def recognize_file(self, audio_file_path: str) -> str:
        if self.client:
            # Use Google Cloud Speech API
            with open(audio_file_path, "rb") as audio_file:
                content = audio_file.read()

            audio = speech.RecognitionAudio(content=content)
            response = self.client.recognize(config=self.config, audio=audio)

            if response.results:
                return response.results[0].alternatives[0].transcript
            return ""
        else:
            # Fall back to speech_recognition library
            import speech_recognition as sr
            with sr.AudioFile(audio_file_path) as source:
                audio = self.recognizer.record(source)
            try:
                return self.recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                logger.warning("Could not understand audio")
                return ""
            except sr.RequestError as e:
                logger.error(f"Could not request results; {e}")
                return ""

    def _audio_generator(self, audio_stream):
        while True:
            chunk = audio_stream.read(4096)
            if not chunk:
                break
            yield chunk


class AWSTranscribeMedicalRecognizer(SpeechRecognizer):
    def __init__(self):
        self.client = boto3.client(
            "transcribe",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )

    async def recognize_stream(self, audio_stream) -> AsyncIterator[str]:
        raise NotImplementedError("AWS streaming not implemented yet")

    async def recognize_file(self, audio_file_path: str) -> str:
        raise NotImplementedError("AWS file recognition not implemented yet")


class LocalSpeechRecognizer(SpeechRecognizer):
    def __init__(self):
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
        except (ImportError, AttributeError, OSError) as e:
            logger.warning(
                f"Could not initialize microphone: {e}. Audio file recognition will still work."
            )
            self.microphone = None

    async def recognize_stream(self, audio_stream) -> AsyncIterator[str]:
        with sr.AudioFile(audio_stream) as source:
            audio = self.recognizer.record(source)

        try:
            text = self.recognizer.recognize_google(audio)
            yield text
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
        except sr.RequestError as e:
            logger.error(f"Could not request results; {e}")

    async def recognize_file(self, audio_file_path: str) -> str:
        with sr.AudioFile(audio_file_path) as source:
            audio = self.recognizer.record(source)

        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return ""
        except sr.RequestError as e:
            logger.error(f"Could not request results; {e}")
            return ""


class MockSpeechRecognizer(SpeechRecognizer):
    """Mock speech recognizer for testing or when audio is not available"""

    async def recognize_stream(self, audio_stream) -> AsyncIterator[str]:
        yield "Mock speech recognition - audio input not available"

    async def recognize_file(self, audio_file_path: str) -> str:
        return "Mock speech recognition - audio file processing not available"


def get_speech_recognizer(provider: str = "google") -> SpeechRecognizer:
    if provider == "google":
        try:
            return GoogleSpeechRecognizer()
        except Exception as e:
            logger.warning(
                f"Failed to initialize Google speech recognizer: {e}, falling back to local"
            )
            try:
                return LocalSpeechRecognizer()
            except Exception as e2:
                logger.warning(
                    f"Failed to initialize local speech recognizer: {e2}, using mock"
                )
                return MockSpeechRecognizer()
    elif provider == "aws":
        try:
            return AWSTranscribeMedicalRecognizer()
        except Exception as e:
            logger.warning(
                f"Failed to initialize AWS speech recognizer: {e}, falling back to local"
            )
            try:
                return LocalSpeechRecognizer()
            except Exception as e2:
                logger.warning(
                    f"Failed to initialize local speech recognizer: {e2}, using mock"
                )
                return MockSpeechRecognizer()
    elif provider == "local":
        try:
            return LocalSpeechRecognizer()
        except Exception as e:
            logger.warning(
                f"Failed to initialize local speech recognizer: {e}, using mock"
            )
            return MockSpeechRecognizer()
    else:
        raise ValueError(f"Unknown speech recognition provider: {provider}")
