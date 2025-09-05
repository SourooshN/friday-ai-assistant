#!/usr/bin/env python3
"""
Complete setup script for Friday AI Assistant
This script creates all necessary directories and files
"""

import os
from pathlib import Path
import sys

def create_directory_structure():
    """Create all necessary directories."""
    directories = [
        "agents",
        "agents/cybersecurity",
        "agents/development",
        "agents/web", 
        "agents/system",
        "agents/supervisor",
        "core",
        "core/models",
        "core/memory",
        "core/security",
        "interfaces",
        "interfaces/cli",
        "interfaces/voice",
        "interfaces/gui",
        "data",
        "data/logs",
        "data/memory",
        "data/exports",
        "data/temp",
        "config",
        "plugins",
        "tests"
    ]
    
    print("Creating directory structure...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created {directory}")
    
    return True

def create_init_files():
    """Create __init__.py files in all package directories."""
    init_files = {
        "agents/__init__.py": '"""Friday AI Assistant - Agents Module"""\n\nfrom .base_agent import BaseAgent, Task, TaskType, TaskStatus\n\n__all__ = ["BaseAgent", "Task", "TaskType", "TaskStatus"]',
        "agents/cybersecurity/__init__.py": '"""Cybersecurity Agents Module"""',
        "agents/development/__init__.py": '"""Development Agents Module"""',
        "agents/web/__init__.py": '"""Web Automation Agents Module"""',
        "agents/system/__init__.py": '"""System Control Agents Module"""',
        "agents/supervisor/__init__.py": '"""Supervisor Agents Module"""',
        "core/__init__.py": '"""Core Module"""',
        "core/models/__init__.py": '"""Models Module"""',
        "core/memory/__init__.py": '"""Memory Module"""',
        "core/security/__init__.py": '"""Security Module"""',
        "interfaces/__init__.py": '"""Interfaces Module"""',
        "interfaces/cli/__init__.py": '"""CLI Interface Module"""',
        "interfaces/voice/__init__.py": '"""Voice Interface Module"""',
        "interfaces/gui/__init__.py": '"""GUI Interface Module"""',
        "plugins/__init__.py": '"""Plugins Module"""',
        "tests/__init__.py": '"""Tests Module"""'
    }
    
    print("\nCreating __init__.py files...")
    for filepath, content in init_files.items():
        path = Path(filepath)
        if not path.exists():
            path.write_text(content)
            print(f"✓ Created {filepath}")
        else:
            print(f"- Skipped {filepath} (already exists)")
    
    return True

def check_files_exist():
    """Check which essential files exist."""
    essential_files = {
        "main.py": "Main entry point",
        "requirements.txt": "Python dependencies",
        "agents/base_agent.py": "Base agent class",
        "agents/cybersecurity/scanner_agent.py": "Scanner agent",
        "agents/development/coding_agent.py": "Coding agent",
        "agents/web/automation_agent.py": "Web automation agent",
        "agents/system/os_control_agent.py": "OS control agent",
        "agents/supervisor/orchestrator_agent.py": "Orchestrator agent",
        "core/orchestrator.py": "Main orchestrator",
        "core/models/model_manager.py": "Model manager",
        "core/memory/short_term.py": "Short-term memory",
        "core/memory/long_term.py": "Long-term memory",
        "core/security/policy_engine.py": "Policy engine",
        "interfaces/cli/terminal.py": "Terminal interface",
        "interfaces/voice/speech_recognition.py": "Voice interface"
    }
    
    print("\nChecking essential files...")
    missing_files = []
    
    for filepath, description in essential_files.items():
        if Path(filepath).exists():
            print(f"✓ Found {filepath}")
        else:
            print(f"✗ Missing {filepath} - {description}")
            missing_files.append(filepath)
    
    return missing_files

def main():
    """Run the complete setup."""
    print("="*60)
    print("Friday AI Assistant - Complete Setup")
    print("="*60)
    
    # Create directories
    if not create_directory_structure():
        print("Error creating directories!")
        return 1
    
    # Create init files
    if not create_init_files():
        print("Error creating __init__.py files!")
        return 1
    
    # Check which files exist
    missing_files = check_files_exist()
    
    print("\n" + "="*60)
    
    if missing_files:
        print(f"\n⚠️  Missing {len(missing_files)} essential files!")
        print("\nYou need to copy the following files from the artifacts provided:")
        
        # Group by directory
        dirs = {}
        for filepath in missing_files:
            dir_path = os.path.dirname(filepath)
            if dir_path not in dirs:
                dirs[dir_path] = []
            dirs[dir_path].append(os.path.basename(filepath))
        
        for directory, files in dirs.items():
            print(f"\nIn {directory or 'root'}/ :")
            for file in files:
                print(f"  - {file}")
        
        print("\n📝 Instructions:")
        print("1. Copy each missing file from the artifacts provided by Claude")
        print("2. Save them in the correct directories as shown above")
        print("3. Run 'pip install -r requirements.txt' to install dependencies")
        print("4. Make sure Ollama is running with models installed")
        print("5. Run 'python main.py' to start Friday")
    else:
        print("\n✅ All files are in place!")
        print("\nNext steps:")
        print("1. Run 'pip install -r requirements.txt' to install dependencies")
        print("2. Make sure Ollama is running with models installed")
        print("3. Run 'python main.py' to start Friday")
    
    print("\n" + "="*60)
    return 0

if __name__ == "__main__":
    sys.exit(main())