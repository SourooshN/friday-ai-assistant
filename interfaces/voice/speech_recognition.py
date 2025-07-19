"""
Voice Interface for Friday AI Assistant
Handles speech recognition and text-to-speech
"""

import asyncio
import threading
import queue
from typing import Optional, Callable, Any
from pathlib import Path
from loguru import logger

# Try to import speech recognition libraries
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logger.warning("SpeechRecognition not available - voice input disabled")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.warning("pyttsx3 not available - voice output disabled")

try:
    import vosk
    import json
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logger.warning("Vosk not available - offline speech recognition disabled")


class VoiceInterface:
    """Voice interface for Friday"""
    
    def __init__(self, orchestrator: Any):
        """Initialize voice interface"""
        self.orchestrator = orchestrator
        self.enabled = False
        self.listening = False
        self.wake_words = ["hey friday", "friday", "ok friday"]
        
        # Speech recognition
        self.recognizer = None
        self.microphone = None
        self.recognition_thread = None
        self.audio_queue = queue.Queue()
        
        # Text-to-speech
        self.tts_engine = None
        self.tts_queue = queue.Queue()
        self.tts_thread = None
        
        # Vosk offline recognition
        self.vosk_model = None
        self.vosk_recognizer = None
        
        # Callbacks
        self.on_wake_word: Optional[Callable] = None
        self.on_command: Optional[Callable] = None
        
        # Initialize if available
        if SPEECH_RECOGNITION_AVAILABLE:
            self._init_speech_recognition()
        
        if TTS_AVAILABLE:
            self._init_tts()
        
        logger.info(f"Voice interface initialized (SR: {SPEECH_RECOGNITION_AVAILABLE}, TTS: {TTS_AVAILABLE})")

    def _init_speech_recognition(self):
        """Initialize speech recognition"""
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            
            # Adjust for ambient noise
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            logger.info("Speech recognition initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize speech recognition: {e}")
            self.recognizer = None
            self.microphone = None

    def _init_tts(self):
        """Initialize text-to-speech"""
        try:
            self.tts_engine = pyttsx3.init()
            
            # Configure voice
            voices = self.tts_engine.getProperty('voices')
            if voices:
                # Try to find a suitable voice
                for voice in voices:
                    if 'english' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
            
            # Set properties
            self.tts_engine.setProperty('rate', 150)  # Speed
            self.tts_engine.setProperty('volume', 0.9)  # Volume
            
            logger.info("Text-to-speech initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS: {e}")
            self.tts_engine = None

    async def start(self):
        """Start voice interface"""
        if not SPEECH_RECOGNITION_AVAILABLE and not TTS_AVAILABLE:
            logger.warning("Voice interface not available - missing dependencies")
            return
        
        self.enabled = True
        
        # Start recognition thread
        if self.recognizer and self.microphone:
            self.recognition_thread = threading.Thread(target=self._recognition_loop, daemon=True)
            self.recognition_thread.start()
        
        # Start TTS thread
        if self.tts_engine:
            self.tts_thread = threading.Thread(target=self._tts_loop, daemon=True)
            self.tts_thread.start()
        
        # Start async audio processor
        asyncio.create_task(self._process_audio_queue())
        
        logger.info("Voice interface started")

    async def stop(self):
        """Stop voice interface"""
        self.enabled = False
        self.listening = False
        
        # Stop threads
        if self.recognition_thread:
            self.recognition_thread.join(timeout=2)
        
        if self.tts_thread:
            self.tts_queue.put(None)  # Sentinel to stop
            self.tts_thread.join(timeout=2)
        
        logger.info("Voice interface stopped")

    def _recognition_loop(self):
        """Background thread for continuous recognition"""
        while self.enabled:
            try:
                if not self.listening:
                    # Listen for wake word
                    self._listen_for_wake_word()
                else:
                    # Listen for command
                    self._listen_for_command()
                    
            except Exception as e:
                logger.error(f"Recognition error: {e}")
                
            # Small delay between attempts
            threading.Event().wait(0.1)

    def _listen_for_wake_word(self):
        """Listen for wake word"""
        try:
            with self.microphone as source:
                # Listen with timeout
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
            # Try to recognize
            try:
                text = self.recognizer.recognize_google(audio).lower()
                
                # Check for wake word
                for wake_word in self.wake_words:
                    if wake_word in text:
                        logger.info(f"Wake word detected: {text}")
                        self.listening = True
                        
                        # Notify
                        if self.on_wake_word:
                            self.on_wake_word()
                        
                        # Audio feedback
                        self.speak("Yes, I'm listening.")
                        break
                        
            except sr.UnknownValueError:
                pass  # Couldn't understand audio
            except sr.RequestError as e:
                logger.error(f"Recognition service error: {e}")
                
        except sr.WaitTimeoutError:
            pass  # No speech detected

    def _listen_for_command(self):
        """Listen for command after wake word"""
        try:
            with self.microphone as source:
                # Listen with longer timeout for commands
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
            # Put in queue for async processing
            self.audio_queue.put(audio)
            
        except sr.WaitTimeoutError:
            # No command after wake word
            self.listening = False
            logger.info("No command detected, stopping listening")

    async def _process_audio_queue(self):
        """Process audio from queue asynchronously"""
        while self.enabled:
            try:
                # Check for audio (non-blocking)
                try:
                    audio = self.audio_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.1)
                    continue
                
                # Recognize audio
                try:
                    text = await asyncio.to_thread(
                        self.recognizer.recognize_google, audio
                    )
                    
                    logger.info(f"Recognized command: {text}")
                    
                    # Process command
                    if self.on_command:
                        await self.on_command(text)
                    else:
                        # Use orchestrator directly
                        result = await self.orchestrator.process_request(text)
                        
                        if result.success and result.result:
                            # Convert result to string for speech
                            response_text = str(result.result)
                            if isinstance(result.result, dict):
                                # For structured results, create a summary
                                if 'code' in result.result:
                                    response_text = "I've generated the code for you. Here it is: " + str(result.result.get('code', ''))
                                elif 'summary' in result.result:
                                    response_text = result.result['summary']
                                else:
                                    response_text = "Task completed successfully."
                            
                            self.speak(response_text[:500])  # Limit speech length
                        else:
                            self.speak(f"Sorry, I encountered an error: {result.error}")
                    
                except sr.UnknownValueError:
                    self.speak("Sorry, I didn't understand that.")
                except sr.RequestError as e:
                    logger.error(f"Recognition service error: {e}")
                    self.speak("Sorry, I'm having trouble with speech recognition.")
                
                # Reset listening state
                self.listening = False
                
            except Exception as e:
                logger.error(f"Audio processing error: {e}")

    def speak(self, text: str):
        """Speak text using TTS"""
        if self.tts_engine:
            self.tts_queue.put(text)
        else:
            logger.info(f"TTS not available, would say: {text}")

    def _tts_loop(self):
        """Background thread for TTS"""
        while self.enabled:
            try:
                # Get text to speak
                text = self.tts_queue.get()
                
                if text is None:  # Sentinel
                    break
                
                # Speak
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                
            except Exception as e:
                logger.error(f"TTS error: {e}")

    async def process_voice_command(self, audio_data: bytes) -> Optional[str]:
        """Process voice command from audio data"""
        if not self.recognizer:
            return None
        
        try:
            # Convert bytes to AudioData
            audio = sr.AudioData(audio_data, sample_rate=16000, sample_width=2)
            
            # Recognize
            text = await asyncio.to_thread(
                self.recognizer.recognize_google, audio
            )
            
            return text
            
        except Exception as e:
            logger.error(f"Voice command processing error: {e}")
            return None

    def set_wake_words(self, wake_words: list):
        """Set custom wake words"""
        self.wake_words = [w.lower() for w in wake_words]
        logger.info(f"Wake words updated: {self.wake_words}")

    def is_available(self) -> bool:
        """Check if voice interface is available"""
        return SPEECH_RECOGNITION_AVAILABLE or TTS_AVAILABLE

    def get_status(self) -> dict:
        """Get voice interface status"""
        return {
            "available": self.is_available(),
            "enabled": self.enabled,
            "listening": self.listening,
            "speech_recognition": SPEECH_RECOGNITION_AVAILABLE,
            "text_to_speech": TTS_AVAILABLE,
            "vosk_offline": VOSK_AVAILABLE,
            "wake_words": self.wake_words
        }