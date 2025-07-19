#!/usr/bin/env python3
"""
Simple launcher for Friday AI Assistant
Ensures proper startup and error handling
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_requirements():
    """Check if basic requirements are met"""
    import subprocess
    
    # Check if Ollama is running
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code != 200:
            print("⚠️  Ollama is not responding properly")
            return False
    except:
        print("❌ Ollama is not running!")
        print("Please start Ollama in another terminal: ollama serve")
        return False
    
    print("✅ Ollama is running")
    return True


async def main():
    """Main entry point"""
    print("🚀 Starting Friday AI Assistant...")
    
    if not check_requirements():
        print("\nPlease fix the issues above and try again.")
        return
    
    # Import and run Friday
    from main import Friday
    
    friday = Friday()
    
    print("\n" + "="*60)
    print("Friday is starting up...")
    print("="*60)
    print("\nYou can interact with Friday in two ways:")
    print("1. Type commands in the terminal")
    print("2. Say 'Hey Friday' to use voice commands")
    print("\nType /help for available commands or /exit to quit")
    print("="*60 + "\n")
    
    await friday.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()