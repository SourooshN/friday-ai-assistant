#!/usr/bin/env python3
"""
Friday AI Assistant - Main Entry Point
An autonomous AI desktop assistant inspired by JARVIS
"""

import asyncio
import logging
import sys
import os
import signal
from pathlib import Path
import argparse
from datetime import datetime

# Core imports
from core.models.model_manager import ModelManager
from core.orchestrator import Orchestrator
from core.memory.short_term import ShortTermMemory
from core.memory.long_term import LongTermMemory
from core.security.policy_engine import PolicyEngine

# Interface imports
from interfaces.cli.terminal import TerminalInterface
from interfaces.voice.speech_recognition import VoiceInterface

# Agent imports
from agents.cybersecurity.scanner_agent import ScannerAgent
from agents.development.coding_agent import CodingAgent
from agents.web.automation_agent import AutomationAgent
from agents.system.os_control_agent import OSControlAgent
from agents.supervisor.orchestrator_agent import OrchestratorAgent

# Configure logging - FIXED FORMAT
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('data/logs/friday.log', mode='a')
    ]
)


class Friday:
    """Main Friday AI Assistant class."""
    
    def __init__(self, config_path: str = "config/friday_config.yaml"):
        """Initialize Friday AI Assistant."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Initializing Friday AI Assistant...")
        
        # Initialize core components with proper configs
        # Model Manager config
        model_config = {
            'models': {
                'default': 'openhermes:latest',
                'coding': 'codellama:13b',
                'analysis': 'mistral:latest'
            },
            'ollama_host': os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        }
        
        # Memory configs
        short_term_config = {
            'ttl_minutes': 30,
            'max_items': 1000,
            'cleanup_interval': 300
        }
        
        long_term_config = {
            'db_path': 'data/memory/friday.db',
            'chroma_path': 'data/memory/chroma',
            'collection_name': 'friday_memory'
        }
        
        # Initialize components
        self.model_manager = ModelManager(config=model_config)
        self.short_term_memory = ShortTermMemory(config=short_term_config)
        self.long_term_memory = LongTermMemory(config=long_term_config)
        self.policy_engine = PolicyEngine()
        
        # Initialize orchestrator with all required parameters
        self.orchestrator = Orchestrator(
            model_manager=self.model_manager,
            short_term_memory=self.short_term_memory,
            long_term_memory=self.long_term_memory,
            policy_engine=self.policy_engine
        )
        
        # Initialize interfaces (they'll be started later)
        self.terminal_interface = None
        self.voice_interface = None
        
        # Shutdown flag
        self.is_running = False
        
        # Display banner
        self._display_banner()
    
    def _display_banner(self):
        """Display Friday startup banner."""
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ███████╗██████╗ ██╗██████╗  █████╗ ██╗   ██╗            ║
║     ██╔════╝██╔══██╗██║██╔══██╗██╔══██╗╚██╗ ██╔╝            ║
║     █████╗  ██████╔╝██║██║  ██║███████║ ╚████╔╝             ║
║     ██╔══╝  ██╔══██╗██║██║  ██║██╔══██║  ╚██╔╝              ║
║     ██║     ██║  ██║██║██████╔╝██║  ██║   ██║               ║
║     ╚═╝     ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝   ╚═╝               ║
║                                                               ║
║          Autonomous AI Desktop Assistant v1.0                 ║
║            "Just A Rather Very Intelligent System"            ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    async def startup(self):
        """Startup sequence for Friday."""
        self.logger.info("Starting Friday AI Assistant...")
        
        try:
            # Initialize model manager
            await self.model_manager.initialize()
            
            # Initialize memory systems
            await self.long_term_memory.initialize()
            await self.short_term_memory.start()
            
            # Initialize orchestrator
            await self.orchestrator.initialize()
            
            # Register agents
            await self._register_agents()
            
            # Initialize interfaces
            self.terminal_interface = TerminalInterface(self.orchestrator)
            self.voice_interface = VoiceInterface(self.orchestrator)
            
            # Start interfaces
            for interface_name, interface in [("cli", self.terminal_interface), 
                                             ("voice", self.voice_interface)]:
                self.logger.info(f"Starting {interface_name} interface...")
                interface.start()
            
            self.is_running = True
            self.logger.info("Friday is ready! Say 'Hey Friday' or type your command.")
            
        except Exception as e:
            self.logger.error(f"Startup failed: {str(e)}")
            raise
    
    async def _register_agents(self):
        """Register all available agents with the orchestrator."""
        # Create agent instances
        agents = [
            ScannerAgent(
                name="ScannerAgent",
                model_manager=self.model_manager,
                memory=self.short_term_memory,
                policy_engine=self.policy_engine
            ),
            CodingAgent(
                name="CodingAgent",
                model_manager=self.model_manager,
                memory=self.short_term_memory,
                policy_engine=self.policy_engine
            ),
            AutomationAgent(
                name="AutomationAgent",
                model_manager=self.model_manager,
                memory=self.short_term_memory,
                policy_engine=self.policy_engine
            ),
            OSControlAgent(
                name="OSControlAgent",
                model_manager=self.model_manager,
                memory=self.short_term_memory,
                policy_engine=self.policy_engine
            ),
            OrchestratorAgent(
                name="OrchestratorAgent",
                model_manager=self.model_manager,
                memory=self.short_term_memory,
                policy_engine=self.policy_engine
            )
        ]
        
        # Register each agent
        for agent in agents:
            self.orchestrator.register_agent(agent)
    
    async def shutdown(self):
        """Shutdown Friday gracefully."""
        self.logger.info("Shutting down Friday...")
        self.is_running = False
        
        # Stop interfaces
        if self.terminal_interface:
            self.terminal_interface.stop()
        if self.voice_interface:
            self.voice_interface.stop()
        
        # Stop memory systems
        await self.short_term_memory.stop()
        await self.long_term_memory.save()
        
        # Cleanup orchestrator
        await self.orchestrator.cleanup()
        
        self.logger.info("Friday shutdown complete. Goodbye!")
    
    async def run(self):
        """Main run loop."""
        # Startup
        await self.startup()
        
        try:
            # Run the terminal interface interactively
            if self.terminal_interface:
                await self.terminal_interface.run_interactive()
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            # Shutdown
            await self.shutdown()


def handle_signal(signum, frame):
    """Handle system signals."""
    print("\nReceived signal to terminate. Shutting down gracefully...")
    sys.exit(0)


def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Friday AI Assistant")
    parser.add_argument('--config', type=str, default='config/friday_config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create data directories
    for directory in ['data/logs', 'data/memory', 'data/exports', 'data/temp']:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Create and run Friday
    friday = Friday(config_path=args.config)
    
    # Run the async main loop
    try:
        asyncio.run(friday.run())
    except KeyboardInterrupt:
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()