#!/usr/bin/env python3
"""
Friday AI Assistant - Main Entry Point
An autonomous AI desktop assistant inspired by JARVIS
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.orchestrator import Orchestrator
from interfaces.cli.terminal import TerminalInterface
from interfaces.voice.speech_recognition import VoiceInterface
from core.models.model_manager import ModelManager
from core.memory.long_term import LongTermMemory
from core.security.policy_engine import PolicyEngine
from scripts.utils.helpers import load_config, setup_logging

# ASCII Art Banner
FRIDAY_BANNER = """
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

class Friday:
    """Main Friday AI Assistant Application"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Friday with configuration"""
        self.config = load_config(config_path or PROJECT_ROOT / "config" / "settings.yaml")
        self.logger = setup_logging(self.config.get("logging", {}))
        
        # Initialize core components
        self.logger.info("Initializing Friday AI Assistant...")
        self.model_manager = ModelManager(self.config.get("models", {}))
        self.memory = LongTermMemory(self.config.get("memory", {}))
        self.policy_engine = PolicyEngine(self.config.get("security", {}))
        self.orchestrator = Orchestrator(
            model_manager=self.model_manager,
            memory=self.memory,
            policy_engine=self.policy_engine,
            config=self.config
        )
        
        # Initialize interfaces
        self.interfaces = {
            "cli": TerminalInterface(self.orchestrator),
            "voice": VoiceInterface(self.orchestrator) if self.config.get("voice", {}).get("enabled", False) else None
        }
        
        self.running = False

    async def startup(self):
        """Perform startup initialization"""
        print(FRIDAY_BANNER)
        self.logger.info("Starting Friday AI Assistant...")
        
        # Initialize model manager
        await self.model_manager.initialize()
        
        # Load memory
        await self.memory.load()
        
        # Initialize orchestrator
        await self.orchestrator.initialize()
        
        # Start interfaces
        for name, interface in self.interfaces.items():
            if interface:
                self.logger.info(f"Starting {name} interface...")
                await interface.start()
        
        self.running = True
        self.logger.info("Friday is ready! Say 'Hey Friday' or type your command.")

    async def shutdown(self):
        """Gracefully shutdown Friday"""
        self.logger.info("Shutting down Friday...")
        self.running = False
        
        # Stop interfaces
        for name, interface in self.interfaces.items():
            if interface:
                await interface.stop()
        
        # Save memory
        await self.memory.save()
        
        # Cleanup
        await self.orchestrator.cleanup()
        
        self.logger.info("Friday shutdown complete. Goodbye!")

    async def run(self):
        """Main run loop"""
        try:
            await self.startup()
            
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal...")
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            await self.shutdown()

def main():
    """Main entry point"""
    # Parse command line arguments if needed
    import argparse
    parser = argparse.ArgumentParser(description="Friday AI Assistant")
    parser.add_argument("--config", type=Path, help="Path to configuration file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Create and run Friday
    friday = Friday(config_path=args.config)
    
    # Run the async main loop
    asyncio.run(friday.run())

if __name__ == "__main__":
    main()