#!/usr/bin/env python3
"""
Friday AI Assistant - Quick Start Script
Simplified launcher with automatic checks
"""

import asyncio
import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def check_ollama():
    """Check if Ollama is running."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


def check_dependencies():
    """Check if all required packages are installed."""
    required = ['ollama', 'chromadb', 'langchain', 'rich', 'pyyaml']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    return missing


async def main():
    """Main entry point with checks."""
    print("🚀 Starting Friday AI Assistant...")
    
    # Check Ollama
    if check_ollama():
        print("✅ Ollama is running")
    else:
        print("❌ Ollama is not running!")
        print("Please start Ollama with: ollama serve")
        return
    
    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        print("Please run: pip install -r requirements.txt")
        return
    
    # Create necessary directories
    dirs = ['data/logs', 'data/memory', 'data/exports', 'data/temp']
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    
    # Import and run Friday
    try:
        from main import Friday
        friday = Friday()
        await friday.run()
    except KeyboardInterrupt:
        print("\n👋 Friday shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Windows color fix
    if sys.platform == 'win32':
        os.system('color')
    
    # Run
    asyncio.run(main())