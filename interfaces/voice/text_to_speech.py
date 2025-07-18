"""
Text-to-Speech module for Friday AI Assistant
Handles voice synthesis with multiple engine support
"""

import asyncio
import threading
import queue
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger
import hashlib
import json

# Try to import TTS engines
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    logger.warning("pyttsx3 not available")

try:
    from TTS.api import TTS as CoquiTTS
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False
    logger.warning("Coqui TTS not available")


class TextToSpeech:
    """Advanced text-to-speech handler"""
    
    def __init__(self, engine: str = "pyttsx3", config: Dict[str, Any] = None):
        """Initialize TTS with specified engine"""
        self.engine_type = engine
        self.config = config or {}
        self.engine = None
        self.voice_cache = {}
        self.cache_dir = Path("data/temp/tts_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize engine
        if engine == "pyttsx3" and PYTTSX3_AVAILABLE:
            self._init_pyttsx3()
        elif engine == "coqui" and COQUI_AVAILABLE:
            self._init_coqui()
        else:
            logger.warning(f"TTS engine {engine} not available")

    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine"""
        try:
            self.engine = pyttsx3.init()
            
            # Configure voice
            voices = self.engine.getProperty('voices')
            voice_id = self.config.get('voice_id', 0)
            
            if voices and 0 <= voice_id < len(voices):
                self.engine.setProperty('voice', voices[voice_id].id)
            
            # Set properties
            self.engine.setProperty('rate', self.config.get('rate', 150))
            self.engine.setProperty('volume', self.config.get('volume', 0.9))
            
            logger.info("pyttsx3 TTS initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")
            self.engine = None

    def _init_coqui(self):
        """Initialize Coqui TTS engine"""
        try:
            # Use a lightweight model
            model_name = self.config.get('model', 'tts_models/en/ljspeech/tacotron2-DDC')
            self.engine = CoquiTTS(model_name=model_name, progress_bar=False)
            
            logger.info(f"Coqui TTS initialized with model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Coqui TTS: {e}")
            self.engine = None

    async def speak(self, text: str, cache: bool = True) -> bool:
        """Speak text asynchronously"""
        if not self.engine:
            logger.warning("No TTS engine available")
            return False
        
        try:
            # Check cache
            if cache:
                cache_key = self._get_cache_key(text)
                if cache_key in self.voice_cache:
                    # Play from cache
                    return await self._play_audio(self.voice_cache[cache_key])
            
            # Generate speech
            if self.engine_type == "pyttsx3":
                await self._speak_pyttsx3(text)
            elif self.engine_type == "coqui":
                audio_file = await self._speak_coqui(text)
                if cache and audio_file:
                    self.voice_cache[cache_key] = audio_file
            
            return True
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return False

    async def _speak_pyttsx3(self, text: str):
        """Speak using pyttsx3"""
        await asyncio.to_thread(self._pyttsx3_say, text)

    def _pyttsx3_say(self, text: str):
        """Blocking pyttsx3 speech"""
        self.engine.say(text)
        self.engine.runAndWait()

    async def _speak_coqui(self, text: str) -> Optional[Path]:
        """Speak using Coqui TTS"""
        # Generate unique filename
        filename = self.cache_dir / f"tts_{self._get_cache_key(text)}.wav"
        
        # Generate audio
        await asyncio.to_thread(
            self.engine.tts_to_file,
            text=text,
            file_path=str(filename)
        )
        
        # Play audio
        await self._play_audio(filename)
        
        return filename

    async def _play_audio(self, audio_file: Path) -> bool:
        """Play audio file"""
        try:
            if audio_file.exists():
                # Use system command to play
                import subprocess
                
                if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                    # Windows
                    await asyncio.to_thread(
                        subprocess.run,
                        ["powershell", "-c", f"(New-Object Media.SoundPlayer '{audio_file}').PlaySync()"],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    # Linux/Mac
                    await asyncio.to_thread(
                        subprocess.run,
                        ["aplay", str(audio_file)] if Path("/usr/bin/aplay").exists() else ["afplay", str(audio_file)],
                        capture_output=True
                    )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
        
        return False

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(f"{text}_{self.engine_type}".encode()).hexdigest()[:16]

    def list_voices(self) -> list:
        """List available voices"""
        voices = []
        
        if self.engine_type == "pyttsx3" and self.engine:
            for voice in self.engine.getProperty('voices'):
                voices.append({
                    'id': voice.id,
                    'name': voice.name,
                    'languages': getattr(voice, 'languages', []),
                    'gender': getattr(voice, 'gender', 'unknown')
                })
        
        return voices

    def set_voice(self, voice_id: str):
        """Set voice by ID"""
        if self.engine_type == "pyttsx3" and self.engine:
            self.engine.setProperty('voice', voice_id)
            logger.info(f"Voice set to: {voice_id}")

    def set_rate(self, rate: int):
        """Set speech rate"""
        if self.engine_type == "pyttsx3" and self.engine:
            self.engine.setProperty('rate', rate)
            self.config['rate'] = rate

    def set_volume(self, volume: float):
        """Set speech volume (0.0 to 1.0)"""
        if self.engine_type == "pyttsx3" and self.engine:
            self.engine.setProperty('volume', max(0.0, min(1.0, volume)))
            self.config['volume'] = volume

    def clear_cache(self):
        """Clear voice cache"""
        self.voice_cache.clear()
        
        # Delete cache files
        for file in self.cache_dir.glob("tts_*.wav"):
            try:
                file.unlink()
            except:
                pass
        
        logger.info("TTS cache cleared")

    def get_status(self) -> dict:
        """Get TTS status"""
        return {
            'engine': self.engine_type,
            'available': self.engine is not None,
            'cache_size': len(self.voice_cache),
            'config': self.config
        }