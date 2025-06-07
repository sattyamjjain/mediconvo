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
        self.client = speech.SpeechClient()
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            model="medical_dictation",
            use_enhanced=True,
            enable_automatic_punctuation=True,
        )

    async def recognize_stream(self, audio_stream) -> AsyncIterator[str]:
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

    async def recognize_file(self, audio_file_path: str) -> str:
        with open(audio_file_path, "rb") as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)
        response = self.client.recognize(config=self.config, audio=audio)

        if response.results:
            return response.results[0].alternatives[0].transcript
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
        self.microphone = sr.Microphone()

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


def get_speech_recognizer(provider: str = "google") -> SpeechRecognizer:
    if provider == "google":
        return GoogleSpeechRecognizer()
    elif provider == "aws":
        return AWSTranscribeMedicalRecognizer()
    elif provider == "local":
        return LocalSpeechRecognizer()
    else:
        raise ValueError(f"Unknown speech recognition provider: {provider}")
