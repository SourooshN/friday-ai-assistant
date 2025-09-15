#!/usr/bin/env python3
"""
Basic test to verify Friday AI Assistant installation
Tests imports, Ollama connection, and basic configuration
"""

import sys
import os
from pathlib import Path

# Ensure we're in the project root
script_dir = Path(__file__).parent
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

def test_python_version():
    """Check Python version"""
    print("\n1. Testing Python Version...")
    print("-" * 40)
    
    major, minor = sys.version_info[:2]
    print(f"  Python version: {major}.{minor}")
    
    if major == 3 and minor >= 11:
        print("  ✓ Python version is compatible")
        return True
    else:
        print(f"  ✗ Python 3.11+ required, found {major}.{minor}")
        return False

def test_imports():
    """Test that core modules can be imported"""
    print("\n2. Testing Core Module Imports...")
    print("-" * 40)
    
    # List of modules to test with their import paths
    modules_to_test = [
        ("ModelManager", "core.models.model_manager", "ModelManager"),
        ("ShortTermMemory", "core.memory.short_term", "ShortTermMemory"),
        ("LongTermMemory", "core.memory.long_term", "LongTermMemory"),
        ("PolicyEngine", "core.security.policy_engine", "PolicyEngine"),
        ("Orchestrator", "core.orchestrator", "Orchestrator"),
        ("TerminalInterface", "interfaces.cli.terminal", "TerminalInterface"),
        ("BaseAgent", "agents.base_agent", "BaseAgent"),
        ("Helpers", "scripts.utils.helpers", "load_config")
    ]
    
    all_passed = True
    imported_modules = {}
    
    for display_name, module_path, class_name in modules_to_test:
        try:
            # Import the module
            module = __import__(module_path, fromlist=[class_name])
            # Get the class/function
            imported_modules[display_name] = getattr(module, class_name)
            print(f"  ✓ {display_name} imported successfully")
        except ImportError as e:
            print(f"  ✗ {display_name} import failed: {e}")
            all_passed = False
        except AttributeError as e:
            print(f"  ✗ {display_name} attribute error: {e}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ {display_name} unexpected error: {e}")
            all_passed = False
    
    return all_passed, imported_modules

def test_ollama_connection():
    """Test if Ollama is running and accessible"""
    print("\n3. Testing Ollama Connection...")
    print("-" * 40)
    
    try:
        import ollama
        
        # Create client
        client = ollama.Client(host="http://localhost:11434")
        
        # Try to list models
        response = client.list()
        models = response.get('models', [])
        
        print("  ✓ Ollama is running and accessible")
        print(f"  ✓ Found {len(models)} installed models:")
        
        if models:
            for model in models[:5]:  # Show first 5
                print(f"    - {model.get('name', 'unknown')}")
            if len(models) > 5:
                print(f"    ... and {len(models) - 5} more")
        else:
            print("    ⚠️  No models installed. Run: ollama pull openhermes:latest")
            return False
            
        return True
        
    except ImportError:
        print("  ✗ ollama package not installed")
        print("    Run: pip install ollama")
        return False
    except Exception as e:
        print(f"  ✗ Ollama connection failed: {e}")
        print("    Ensure Ollama is running: ollama serve")
        return False

def test_config_files():
    """Test that essential configuration files exist"""
    print("\n4. Testing Configuration Files...")
    print("-" * 40)
    
    required_files = {
        ".env": "Environment configuration (copy from .env.example if missing)",
        "config/settings.yaml": "Main settings file",
        "config/model_configs.yaml": "Model configurations",
        "requirements.txt": "Python dependencies"
    }
    
    all_exist = True
    
    for file_path, description in required_files.items():
        full_path = Path(file_path)
        if full_path.exists():
            print(f"  ✓ {file_path} exists")
        else:
            print(f"  ✗ {file_path} missing - {description}")
            all_exist = False
    
    return all_exist

def test_directory_structure():
    """Test that required directories exist"""
    print("\n5. Testing Directory Structure...")
    print("-" * 40)
    
    required_dirs = [
        "agents",
        "core",
        "interfaces",
        "config",
        "data",
        "scripts",
        "venv"
    ]
    
    all_exist = True
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            print(f"  ✓ {dir_name}/ exists")
        else:
            print(f"  ✗ {dir_name}/ missing")
            all_exist = False
    
    return all_exist

def test_simple_ollama_generation():
    """Test basic text generation with Ollama"""
    print("\n6. Testing Basic Text Generation...")
    print("-" * 40)
    
    try:
        import ollama
        
        client = ollama.Client(host="http://localhost:11434")
        
        # Get first available model
        models = client.list().get('models', [])
        if not models:
            print("  ✗ No models available for testing")
            return False
        
        model_name = models[0]['name']
        print(f"  Using model: {model_name}")
        
        # Simple test prompt
        response = client.generate(
            model=model_name,
            prompt="Respond with exactly: 'Friday test successful'",
            options={"temperature": 0.1}
        )
        
        result = response.get('response', '').strip()
        print(f"  Model response: {result}")
        print("  ✓ Text generation working")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Generation failed: {e}")
        return False

def run_all_tests():
    """Run all basic tests"""
    print("=" * 60)
    print("FRIDAY AI ASSISTANT - BASIC SYSTEM TEST")
    print("=" * 60)
    
    test_results = []
    
    # Run tests in order
    test_results.append(("Python Version", test_python_version()))
    test_results.append(("Directory Structure", test_directory_structure()))
    test_results.append(("Config Files", test_config_files()))
    
    # Import test returns tuple
    import_result = test_imports()
    test_results.append(("Module Imports", import_result[0]))
    
    test_results.append(("Ollama Connection", test_ollama_connection()))
    
    # Only test generation if Ollama is connected
    if test_results[-1][1]:  # If Ollama connection succeeded
        test_results.append(("Text Generation", test_simple_ollama_generation()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, result in test_results if result)
    
    for test_name, result in test_results:
        status = "PASSED" if result else "FAILED"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name:<20} {status}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n✅ All tests passed! Friday core is ready.")
        print("\nNext steps:")
        print("1. Run comprehensive tests: python scripts/test_core.py")
        print("2. Start Friday: python main.py")
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("1. Activate virtual environment: .\\venv\\Scripts\\Activate.ps1")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Start Ollama: ollama serve")
        print("4. Install a model: ollama pull openhermes:latest")
        print("5. Create .env file: copy .env.example .env")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)