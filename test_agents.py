"""
Quick test to check agent imports
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_agent_imports():
    """Test importing each agent"""
    agents = [
        ("agents.cybersecurity.scanner_agent", "ScannerAgent"),
        ("agents.development.coding_agent", "CodingAgent"),
        ("agents.web.automation_agent", "AutomationAgent"),
        ("agents.system.os_control_agent", "OSControlAgent"),
        ("agents.supervisor.orchestrator_agent", "OrchestratorAgent")
    ]
    
    for module_path, class_name in agents:
        try:
            # Try to import the module
            module = __import__(module_path, fromlist=[class_name])
            
            # Try to get the class
            if hasattr(module, class_name):
                print(f"✓ {class_name} found in {module_path}")
            else:
                print(f"✗ {class_name} NOT FOUND in {module_path}")
                # List what's actually in the module
                print(f"  Available in module: {[name for name in dir(module) if not name.startswith('_')]}")
                
        except ImportError as e:
            print(f"✗ Failed to import {module_path}: {e}")
        except Exception as e:
            print(f"✗ Error with {module_path}: {e}")

if __name__ == "__main__":
    test_agent_imports()