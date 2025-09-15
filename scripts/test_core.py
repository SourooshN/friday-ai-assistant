#!/usr/bin/env python3
"""
Comprehensive test script for Friday AI Assistant Core Components
Tests ModelManager, Memory Systems, PolicyEngine, and Orchestrator
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# Setup path
script_dir = Path(__file__).parent.parent
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

# Import test utilities
try:
    from rich.console import Console
    console = Console()
    use_rich = True
except ImportError:
    use_rich = False
    
    class MockConsole:
        def print(self, *args, **kwargs):
            # Strip rich markup
            text = str(args[0]) if args else ""
            text = text.replace("[bold]", "").replace("[/bold]", "")
            text = text.replace("[green]", "").replace("[/green]", "")
            text = text.replace("[red]", "").replace("[/red]", "")
            text = text.replace("[yellow]", "").replace("[/yellow]", "")
            text = text.replace("[blue]", "").replace("[/blue]", "")
            text = text.replace("[cyan]", "").replace("[/cyan]", "")
            print(text)
    
    console = MockConsole()

async def test_model_manager():
    """Test ModelManager functionality"""
    console.print("\n[bold blue]Testing Model Manager...[/bold blue]")
    
    try:
        # Import required modules
        from core.models.model_manager import ModelManager
        
        # Create minimal config
        config = {
            'host': 'http://localhost:11434',
            'default_model': 'openhermes:latest',
            'timeout': 300,
            'temperature': 0.7,
            'max_tokens': 4096
        }
        
        # Initialize ModelManager
        model_manager = ModelManager(config)
        console.print("  ✓ ModelManager instantiated")
        
        # Initialize (discover models)
        await model_manager.initialize()
        console.print("  ✓ ModelManager initialized")
        
        # Check available models
        models = model_manager.list_models()
        console.print(f"  ✓ Found {len(models)} models")
        
        if models:
            console.print("    Available models:")
            for model in models[:3]:  # Show first 3
                console.print(f"      - {model.name}")
        
        # Test health check
        health = await model_manager.health_check()
        if health['status'] == 'healthy':
            console.print("  ✓ Ollama connection healthy")
        else:
            console.print(f"  ✗ Ollama unhealthy: {health.get('error', 'Unknown error')}")
            return False
        
        # Test text generation if models available
        if models:
            console.print("\n  Testing text generation...")
            result = await model_manager.generate(
                prompt="Say 'test passed' and nothing else",
                max_tokens=10,
                temperature=0.1
            )
            console.print(f"  ✓ Generation successful: {result.text.strip()}")
        
        return True
        
    except ImportError as e:
        console.print(f"  ✗ Import error: {e}")
        return False
    except Exception as e:
        console.print(f"  ✗ ModelManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_short_term_memory():
    """Test ShortTermMemory functionality"""
    console.print("\n[bold blue]Testing Short-Term Memory...[/bold blue]")
    
    try:
        from core.memory.short_term import ShortTermMemory
        
        # Create config
        config = {
            'max_items': 100,
            'ttl_seconds': 3600
        }
        
        # Initialize
        memory = ShortTermMemory(config)
        console.print("  ✓ ShortTermMemory instantiated")
        
        # Start memory system
        await memory.start()
        console.print("  ✓ Memory system started")
        
        # Test store and retrieve
        test_key = "test_key_123"
        test_value = {"data": "test value", "timestamp": datetime.now().isoformat()}
        
        await memory.store(test_key, test_value, type="test")
        console.print("  ✓ Stored test value")
        
        retrieved = await memory.retrieve(test_key)
        if retrieved == test_value:
            console.print("  ✓ Retrieved value matches")
        else:
            console.print("  ✗ Retrieved value doesn't match")
            return False
        
        # Test search
        results = await memory.search(query="test", type="test")
        console.print(f"  ✓ Search returned {len(results)} results")
        
        # Test conversation history
        await memory.add_conversation_turn("user", "Test message")
        await memory.add_conversation_turn("assistant", "Test response")
        history = memory.get_conversation_history()
        console.print(f"  ✓ Conversation history has {len(history)} turns")
        
        # Test stats
        stats = memory.get_stats()
        console.print(f"  ✓ Memory stats: {stats['total_items']} items")
        
        # Cleanup
        await memory.stop()
        console.print("  ✓ Memory system stopped")
        
        return True
        
    except Exception as e:
        console.print(f"  ✗ ShortTermMemory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_long_term_memory():
    """Test LongTermMemory functionality"""
    console.print("\n[bold blue]Testing Long-Term Memory...[/bold blue]")
    
    # Create temporary directory for test databases
    temp_dir = tempfile.mkdtemp()
    
    try:
        from core.memory.long_term import LongTermMemory
        
        # Create config with temp paths
        config = {
            'vector_db': {
                'path': os.path.join(temp_dir, 'vectors'),
                'collection_name': 'test_memory'
            },
            'long_term': {
                'path': os.path.join(temp_dir, 'test.db')
            }
        }
        
        # Initialize
        memory = LongTermMemory(config)
        console.print("  ✓ LongTermMemory instantiated")
        
        await memory.initialize()
        console.print("  ✓ Databases initialized")
        
        # Test store
        content = "Friday AI Assistant test memory entry"
        memory_id = await memory.store(content, type="test", importance=0.8)
        console.print(f"  ✓ Stored memory with ID: {memory_id}")
        
        # Test retrieve
        retrieved = await memory.retrieve(memory_id)
        if retrieved and retrieved['content'] == content:
            console.print("  ✓ Retrieved memory matches")
        else:
            console.print("  ✗ Retrieved memory doesn't match")
            return False
        
        # Test search
        results = await memory.search("Friday test", type="test", limit=10)
        console.print(f"  ✓ Search returned {len(results)} results")
        
        # Test fact storage
        await memory.add_fact("Friday", "is", "AI Assistant", confidence=1.0)
        facts = await memory.query_facts(subject="Friday")
        console.print(f"  ✓ Stored and retrieved {len(facts)} facts")
        
        # Test preferences
        await memory.set_preference("test_pref", {"value": 123})
        pref = await memory.get_preference("test_pref")
        if pref == {"value": 123}:
            console.print("  ✓ Preferences working")
        
        # Test stats
        stats = memory.get_stats()
        console.print(f"  ✓ Memory stats: {stats['total_memories']} memories")
        
        return True
        
    except Exception as e:
        console.print(f"  ✗ LongTermMemory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

async def test_policy_engine():
    """Test PolicyEngine functionality"""
    console.print("\n[bold blue]Testing Policy Engine...[/bold blue]")
    
    try:
        from core.security.policy_engine import PolicyEngine
        
        # Create config
        config = {
            'sandbox_enabled': True,
            'require_confirmation': ['delete', 'modify_system'],
            'guardrails': {
                'check_ethical': True,
                'check_legal': True,
                'check_harmful': True
            }
        }
        
        # Initialize
        policy_engine = PolicyEngine(config)
        console.print("  ✓ PolicyEngine instantiated")
        
        # Test with mock task (create minimal Task object)
        class MockTask:
            def __init__(self, task_id, description, task_type, parameters=None):
                self.id = task_id
                self.description = description
                self.type = task_type
                self.parameters = parameters or {}
        
        # Test safe task
        safe_task = MockTask("test1", "List files in current directory", "file_operation")
        result = await policy_engine.check_task(safe_task)
        console.print(f"  ✓ Safe task check: allowed={result.allowed}")
        
        # Test dangerous task  
        dangerous_task = MockTask("test2", "Delete system files", "file_operation")
        result = await policy_engine.check_task(dangerous_task)
        console.print(f"  ✓ Dangerous task check: allowed={result.allowed}")
        
        # Test command check
        safe_cmd_result = await policy_engine.check_command("dir")
        console.print(f"  ✓ Safe command check: allowed={safe_cmd_result.allowed}")
        
        dangerous_cmd_result = await policy_engine.check_command("rm -rf /")
        console.print(f"  ✓ Dangerous command check: allowed={dangerous_cmd_result.allowed}")
        
        # Test file operation check
        safe_path = Path("./data/test.txt")
        file_result = await policy_engine.check_file_operation(safe_path, "read")
        console.print(f"  ✓ File operation check completed")
        
        return True
        
    except Exception as e:
        console.print(f"  ✗ PolicyEngine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_orchestrator():
    """Test Orchestrator initialization"""
    console.print("\n[bold blue]Testing Orchestrator...[/bold blue]")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Import all required components
        from core.orchestrator import Orchestrator
        from core.models.model_manager import ModelManager
        from core.memory.long_term import LongTermMemory
        from core.security.policy_engine import PolicyEngine
        
        # Create minimal configs
        model_config = {
            'host': 'http://localhost:11434',
            'default_model': 'openhermes:latest'
        }
        
        memory_config = {
            'vector_db': {
                'path': os.path.join(temp_dir, 'vectors'),
                'collection_name': 'test_memory'
            },
            'long_term': {
                'path': os.path.join(temp_dir, 'test.db')
            }
        }
        
        security_config = {
            'sandbox_enabled': True,
            'require_confirmation': []
        }
        
        orchestrator_config = {
            'max_agents': 10,
            'task_timeout': 300,
            'planning_model': 'openhermes:latest',
            'reflection_enabled': False
        }
        
        # Initialize components
        console.print("  Initializing components...")
        
        model_manager = ModelManager(model_config)
        await model_manager.initialize()
        console.print("  ✓ ModelManager ready")
        
        memory = LongTermMemory(memory_config)
        await memory.initialize()
        console.print("  ✓ LongTermMemory ready")
        
        policy_engine = PolicyEngine(security_config)
        console.print("  ✓ PolicyEngine ready")
        
        # Create orchestrator
        orchestrator = Orchestrator(
            model_manager=model_manager,
            memory=memory,
            policy_engine=policy_engine,
            config=orchestrator_config
        )
        console.print("  ✓ Orchestrator instantiated")
        
        # Initialize orchestrator
        await orchestrator.initialize()
        console.print("  ✓ Orchestrator initialized")
        
        # Get status
        status = await orchestrator.get_status()
        console.print(f"  ✓ Status retrieved: {len(status['agents'])} agents loaded")
        
        if status['agents']:
            console.print("    Loaded agents:")
            for agent_name in list(status['agents'].keys())[:3]:
                console.print(f"      - {agent_name}")
        
        # Cleanup
        await orchestrator.cleanup()
        console.print("  ✓ Orchestrator cleaned up")
        
        return True
        
    except Exception as e:
        console.print(f"  ✗ Orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

async def run_all_tests():
    """Run all core component tests"""
    console.print("=" * 60)
    console.print("[bold cyan]FRIDAY AI ASSISTANT - CORE COMPONENT TESTS[/bold cyan]")
    console.print("=" * 60)
    
    # Check if Ollama is running first
    try:
        import ollama
        client = ollama.Client(host="http://localhost:11434")
        client.list()
    except:
        console.print("\n[red]ERROR: Ollama is not running![/red]")
        console.print("Please start Ollama first: ollama serve")
        return False
    
    test_functions = [
        ("ModelManager", test_model_manager),
        ("Short-term Memory", test_short_term_memory),
        ("Long-term Memory", test_long_term_memory),
        ("Policy Engine", test_policy_engine),
        ("Orchestrator", test_orchestrator)
    ]
    
    results = []
    
    for test_name, test_func in test_functions:
        try:
            console.print(f"\n{'='*60}")
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            console.print(f"\n[red]Fatal error in {test_name}: {e}[/red]")
            results.append((test_name, False))
    
    # Summary
    console.print("\n" + "="*60)
    console.print("[bold]TEST SUMMARY[/bold]")
    console.print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    
    for test_name, result in results:
        status = "[green]PASSED[/green]" if result else "[red]FAILED[/red]"
        symbol = "✓" if result else "✗"
        console.print(f"{symbol} {test_name:<20} {status}")
    
    console.print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        console.print("\n[bold green]✅ All core components tested successfully![/bold green]")
        console.print("\nFriday is ready to start:")
        console.print("  python main.py")
    else:
        console.print("\n[bold red]❌ Some tests failed.[/bold red]")
        console.print("\nCheck the errors above and ensure:")
        console.print("1. All dependencies are installed")
        console.print("2. Ollama is running with models installed")
        console.print("3. No import errors in the code")
    
    return passed_tests == total_tests

def main():
    """Entry point"""
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()