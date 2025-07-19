"""
Check what's actually in each agent file
"""

import ast
import sys
from pathlib import Path

def check_agent_file(file_path):
    """Check what classes are defined in an agent file"""
    print(f"\nChecking {file_path}:")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the file
        tree = ast.parse(content)
        
        # Find all class definitions
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
        
        if classes:
            print(f"  Found classes: {', '.join(classes)}")
        else:
            print("  No classes found!")
            
        # Check if file is empty or has syntax errors
        if len(content.strip()) < 10:
            print("  WARNING: File appears to be empty or very small")
            
    except SyntaxError as e:
        print(f"  SYNTAX ERROR: {e}")
    except Exception as e:
        print(f"  ERROR: {e}")

# Check all agent files
agent_files = [
    "agents/cybersecurity/scanner_agent.py",
    "agents/development/coding_agent.py", 
    "agents/web/automation_agent.py",
    "agents/system/os_control_agent.py",
    "agents/supervisor/orchestrator_agent.py"
]

for file_path in agent_files:
    if Path(file_path).exists():
        check_agent_file(file_path)
    else:
        print(f"\n{file_path}: FILE NOT FOUND")