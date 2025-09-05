"""
Model Manager for Friday AI Assistant.
Handles all interactions with Ollama models.
"""

import logging
from typing import Dict, Any, List, Optional
import json
import aiohttp
import asyncio
import os
from datetime import datetime

import ollama
from ollama import AsyncClient


class ModelManager:
    """Manages AI models via Ollama."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the model manager with optional config."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Use provided config or defaults
        if config is None:
            config = {
                'models': {
                    'default': 'openhermes:latest',
                    'coding': 'codellama:13b',
                    'analysis': 'mistral:latest'
                },
                'ollama_host': os.getenv('OLLAMA_HOST', 'http://localhost:11434')
            }
        
        self.config = config
        self.ollama_host = config.get('ollama_host', 'http://localhost:11434')
        self.available_models = {}
        self.model_configs = config.get('models', {})
        self.default_model = config.get('models', {}).get('default', 'openhermes:latest')
        
        # Ollama client
        self.client = AsyncClient(host=self.ollama_host)
        
        self.logger.info(f"Initialized ModelManager with host: {self.ollama_host}")
    
    async def initialize(self):
        """Initialize model manager and check available models."""
        self.logger.info("Initializing Model Manager...")
        
        # Load model configurations
        await self._load_model_configs()
        
        # Refresh available models
        await self.refresh_models()
    
    async def _load_model_configs(self):
        """Load model configurations."""
        # For now, using the config passed in constructor
        self.logger.info(f"Loaded configurations for {len(self.model_configs)} models")
    
    async def refresh_models(self):
        """Refresh the list of available models from Ollama."""
        try:
            # Use ollama library to list models
            models = await self.client.list()
            
            self.available_models = {}
            for model in models.get('models', []):
                model_name = model['name']
                self.available_models[model_name] = {
                    'name': model_name,
                    'size': model.get('size', 0),
                    'modified': model.get('modified_at', ''),
                    'details': model
                }
            
            self.logger.info(f"Found {len(self.available_models)} available models")
            
            # Check if required models are available
            required_models = ['openhermes:latest', 'codellama:13b', 'mistral:latest']
            missing_models = []
            
            for model in required_models:
                if model not in self.available_models:
                    missing_models.append(model)
            
            if missing_models:
                self.logger.warning(f"Missing recommended models: {missing_models}")
                self.logger.info("Pull them with: ollama pull <model-name>")
            
        except Exception as e:
            self.logger.error(f"Failed to refresh models: {str(e)}")
            self.logger.warning("Make sure Ollama is running (ollama serve)")
    
    async def generate(self, prompt: str, model: Optional[str] = None, 
                      max_tokens: int = 1000, temperature: float = 0.7,
                      **kwargs) -> str:
        """Generate text using specified model."""
        model = model or self.default_model
        
        # Ensure model is available
        if model not in self.available_models and self.available_models:
            self.logger.warning(f"Model {model} not found, using {self.default_model}")
            model = self.default_model
        
        try:
            # Use ollama library for generation
            response = await self.client.generate(
                model=model,
                prompt=prompt,
                options={
                    'num_predict': max_tokens,
                    'temperature': temperature,
                    **kwargs
                }
            )
            
            # Extract the generated text
            if isinstance(response, dict) and 'response' in response:
                return response['response']
            else:
                return str(response)
            
        except Exception as e:
            self.logger.error(f"Generation failed with {model}: {str(e)}")
            
            # Try with default model if different
            if model != self.default_model:
                self.logger.info(f"Retrying with default model: {self.default_model}")
                return await self.generate(prompt, self.default_model, max_tokens, temperature, **kwargs)
            else:
                raise
    
    async def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None,
                   **kwargs) -> str:
        """Chat with a model using conversation history."""
        model = model or self.default_model
        
        try:
            response = await self.client.chat(
                model=model,
                messages=messages,
                options=kwargs
            )
            
            # Extract response
            if isinstance(response, dict):
                if 'message' in response:
                    return response['message'].get('content', '')
                elif 'response' in response:
                    return response['response']
            
            return str(response)
            
        except Exception as e:
            self.logger.error(f"Chat failed with {model}: {str(e)}")
            raise
    
    def select_model_for_task(self, task_type: str) -> str:
        """Select the best model for a given task type."""
        task_model_map = {
            'coding': 'codellama:13b',
            'analysis': 'mistral:latest',
            'general': 'openhermes:latest',
            'planning': 'openhermes:latest',
            'security': 'mistral:latest'
        }
        
        selected = task_model_map.get(task_type, self.default_model)
        
        # Check if model is available
        if selected not in self.available_models and self.available_models:
            self.logger.warning(f"Preferred model {selected} for {task_type} not available")
            return self.default_model
        
        return selected
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            self.logger.info(f"Pulling model: {model_name}")
            
            # This would need to be implemented with proper progress handling
            # For now, we'll just log
            self.logger.info(f"Please run 'ollama pull {model_name}' in your terminal")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to pull model {model_name}: {str(e)}")
            return False
    
    async def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model."""
        await self.refresh_models()
        return self.available_models.get(model_name)
    
    def get_available_models(self) -> List[str]:
        """Get list of available model names."""
        return list(self.available_models.keys())
    
    async def test_connection(self) -> bool:
        """Test connection to Ollama."""
        try:
            await self.client.list()
            return True
        except Exception as e:
            self.logger.error(f"Ollama connection test failed: {str(e)}")
            return False