"""
Model Manager for Friday AI Assistant
Handles Ollama model loading, switching, and inference
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import aiohttp
import ollama
from loguru import logger

from scripts.utils.helpers import load_config, retry_async


@dataclass
class ModelInfo:
    """Information about an available model"""
    name: str
    size: int
    modified: datetime
    capabilities: List[str]
    parameters: Dict[str, Any]
    is_loaded: bool = False


@dataclass
class GenerationResult:
    """Result from model generation"""
    text: str
    model: str
    duration: float
    tokens_generated: int
    metadata: Dict[str, Any]


class ModelManager:
    """Manages Ollama models for Friday"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Model Manager"""
        self.config = config
        self.ollama_host = config.get('host', 'http://localhost:11434')
        self.default_model = config.get('default_model', 'openhermes:latest')
        self.timeout = config.get('timeout', 300)
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 4096)
        
        # Model registry
        self.available_models: Dict[str, ModelInfo] = {}
        self.loaded_models: List[str] = []
        self.model_configs = {}
        
        # Performance tracking
        self.generation_history = []
        
        # Ollama client
        self.client = ollama.Client(host=self.ollama_host)
        
        logger.info(f"Initialized ModelManager with host: {self.ollama_host}")

    async def initialize(self):
        """Initialize model manager and load model configurations"""
        logger.info("Initializing Model Manager...")
        
        # Load model configurations
        try:
            model_config_path = load_config("config/model_configs.yaml")
            self.model_configs = model_config_path.get('models', {})
            logger.info(f"Loaded configurations for {len(self.model_configs)} models")
        except Exception as e:
            logger.warning(f"Could not load model configs: {e}")
        
        # Discover available models
        await self.refresh_models()
        
        # Ensure default model is available
        if self.default_model not in self.available_models:
            logger.warning(f"Default model {self.default_model} not found!")
            if self.available_models:
                self.default_model = list(self.available_models.keys())[0]
                logger.info(f"Using {self.default_model} as default")
            else:
                logger.error("No models available!")

    async def refresh_models(self):
        """Refresh list of available models from Ollama"""
        try:
            models = self.client.list()
            self.available_models.clear()
            
            for model in models.get('models', []):
                model_name = model['name']
                
                # Get capabilities from config or infer
                capabilities = []
                if model_name in self.model_configs:
                    capabilities = self.model_configs[model_name].get('capabilities', [])
                else:
                    # Infer capabilities from model name
                    if 'code' in model_name.lower() or 'llama' in model_name.lower():
                        capabilities.append('coding')
                    if 'chat' in model_name.lower() or 'hermes' in model_name.lower():
                        capabilities.append('conversation')
                    if not capabilities:
                        capabilities = ['general']
                
                self.available_models[model_name] = ModelInfo(
                    name=model_name,
                    size=model.get('size', 0),
                    modified=datetime.fromisoformat(model['modified'].replace('Z', '+00:00')) if 'modified' in model else datetime.now(),
                    capabilities=capabilities,
                    parameters=model.get('details', {}).get('parameter_size', {}),
                    is_loaded=model_name in self.loaded_models
                )
            
            logger.info(f"Found {len(self.available_models)} available models")
            
        except Exception as e:
            logger.error(f"Failed to refresh models: {e}")

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[GenerationResult, asyncio.StreamReader]:
        """Generate text using specified model"""
        
        model = model or self.default_model
        temperature = temperature or self.temperature
        max_tokens = max_tokens or self.max_tokens
        
        # Check if model is available
        if model not in self.available_models:
            logger.warning(f"Model {model} not available, using default")
            model = self.default_model
        
        logger.debug(f"Generating with {model}: {prompt[:100]}...")
        start_time = datetime.now()
        
        try:
            # Build options
            options = {
                'temperature': temperature,
                'num_predict': max_tokens,
                **kwargs
            }
            
            # Add system prompt if provided
            messages = []
            if system:
                messages.append({'role': 'system', 'content': system})
            messages.append({'role': 'user', 'content': prompt})
            
            if stream:
                # Return async generator for streaming
                return self._stream_generate(model, messages, options)
            else:
                # Non-streaming generation
                response = await asyncio.to_thread(
                    self.client.chat,
                    model=model,
                    messages=messages,
                    options=options
                )
                
                duration = (datetime.now() - start_time).total_seconds()
                
                # Extract text from response
                text = response.get('message', {}).get('content', '')
                
                result = GenerationResult(
                    text=text,
                    model=model,
                    duration=duration,
                    tokens_generated=response.get('eval_count', 0),
                    metadata={
                        'total_duration': response.get('total_duration', 0),
                        'load_duration': response.get('load_duration', 0),
                        'eval_duration': response.get('eval_duration', 0)
                    }
                )
                
                # Track performance
                self.generation_history.append({
                    'timestamp': datetime.now(),
                    'model': model,
                    'duration': duration,
                    'tokens': result.tokens_generated,
                    'prompt_length': len(prompt)
                })
                
                # Mark model as loaded
                if model not in self.loaded_models:
                    self.loaded_models.append(model)
                    self.available_models[model].is_loaded = True
                
                logger.debug(f"Generated {result.tokens_generated} tokens in {duration:.2f}s")
                
                return result
                
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    async def _stream_generate(self, model: str, messages: List[Dict], options: Dict):
        """Stream generation responses"""
        try:
            stream = self.client.chat(
                model=model,
                messages=messages,
                options=options,
                stream=True
            )
            
            for chunk in stream:
                if chunk:
                    yield chunk['message']['content']
                    
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            raise

    def select_model_for_task(self, task_type: str, complexity: str = 'medium') -> str:
        """Select best model for a given task type"""
        
        # Check selection rules from config
        if hasattr(self, 'model_configs'):
            rules = load_config("config/model_configs.yaml").get('selection_rules', [])
            
            for rule in rules:
                # Simple rule evaluation
                condition = rule.get('condition', '')
                if f"task_type == '{task_type}'" in condition:
                    model = rule.get('model')
                    if model and model in self.available_models:
                        logger.debug(f"Selected {model} for {task_type} based on rules")
                        return model
        
        # Fallback to capability matching
        for model_name, model_info in self.available_models.items():
            if task_type in model_info.capabilities:
                logger.debug(f"Selected {model_name} for {task_type} based on capabilities")
                return model_name
        
        # Default fallback
        logger.debug(f"Using default model for {task_type}")
        return self.default_model

    async def load_model(self, model_name: str) -> bool:
        """Ensure a model is loaded and ready"""
        try:
            # Pull model if not available
            if model_name not in self.available_models:
                logger.info(f"Pulling model {model_name}...")
                await asyncio.to_thread(self.client.pull, model_name)
                await self.refresh_models()
            
            # Generate a test prompt to load the model
            logger.info(f"Loading model {model_name}...")
            await self.generate("Hello", model=model_name, max_tokens=1)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return False

    async def unload_model(self, model_name: str) -> bool:
        """Unload a model to free memory"""
        try:
            # Ollama doesn't have explicit unload, but we can track it
            if model_name in self.loaded_models:
                self.loaded_models.remove(model_name)
                if model_name in self.available_models:
                    self.available_models[model_name].is_loaded = False
                logger.info(f"Marked model {model_name} as unloaded")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload model {model_name}: {e}")
            return False

    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        return self.available_models.get(model_name)

    def list_models(self) -> List[ModelInfo]:
        """List all available models"""
        return list(self.available_models.values())

    def get_loaded_models(self) -> List[str]:
        """Get list of currently loaded models"""
        return self.loaded_models.copy()

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.generation_history:
            return {}
        
        total_generations = len(self.generation_history)
        total_tokens = sum(h['tokens'] for h in self.generation_history)
        avg_duration = sum(h['duration'] for h in self.generation_history) / total_generations
        
        model_stats = {}
        for history in self.generation_history:
            model = history['model']
            if model not in model_stats:
                model_stats[model] = {
                    'count': 0,
                    'total_tokens': 0,
                    'total_duration': 0
                }
            model_stats[model]['count'] += 1
            model_stats[model]['total_tokens'] += history['tokens']
            model_stats[model]['total_duration'] += history['duration']
        
        return {
            'total_generations': total_generations,
            'total_tokens': total_tokens,
            'average_duration': avg_duration,
            'model_statistics': model_stats,
            'loaded_models': self.loaded_models,
            'available_models': len(self.available_models)
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check health of model manager and Ollama"""
        health = {
            'status': 'unknown',
            'ollama_host': self.ollama_host,
            'available_models': len(self.available_models),
            'loaded_models': len(self.loaded_models),
            'default_model': self.default_model
        }
        
        try:
            # Try to list models
            models = self.client.list()
            health['status'] = 'healthy'
            health['ollama_version'] = models.get('version', 'unknown')
            
        except Exception as e:
            health['status'] = 'unhealthy'
            health['error'] = str(e)
        
        return health