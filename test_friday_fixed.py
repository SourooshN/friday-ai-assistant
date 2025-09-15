#!/usr/bin/env python3
"""
Test script to verify Friday is working after fixes
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_components():
    """Test individual components."""
    print("🧪 Testing Friday Components...\n")
    
    # Test 1: Model Manager
    print("1️⃣ Testing Model Manager...")
    try:
        from core.models.model_manager import ModelManager
        mm = ModelManager()
        await mm.initialize()
        print("✅ Model Manager initialized")
        
        # Test generation
        response = await mm.generate("Say 'Hello, I am Friday!'", max_tokens=50)
        print(f"✅ Model response: {response[:100]}...")
    except Exception as e:
        print(f"❌ Model Manager error: {e}")
        return False
    
    # Test 2: Memory Systems
    print("\n2️⃣ Testing Memory Systems...")
    try:
        from core.memory.short_term import ShortTermMemory
        from core.memory.long_term import LongTermMemory
        
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        await ltm.initialize()
        print("✅ Memory systems initialized")
    except Exception as e:
        print(f"❌ Memory error: {e}")
        return False
    
    # Test 3: Orchestrator
    print("\n3️⃣ Testing Orchestrator...")
    try:
        from core.orchestrator import Orchestrator
        from core.security.policy_engine import PolicyEngine
        
        pe = PolicyEngine()
        orchestrator = Orchestrator(
            model_manager=mm,
            short_term_memory=stm,
            long_term_memory=ltm,
            policy_engine=pe
        )
        await orchestrator.initialize()
        print("✅ Orchestrator initialized")
    except Exception as e:
        print(f"❌ Orchestrator error: {e}")
        return False
    
    # Test 4: Agents
    print("\n4️⃣ Testing Agents...")
    try:
        from agents.development.coding_agent import CodingAgent
        
        agent = CodingAgent(
            name="TestCodingAgent",
            model_manager=mm,
            memory=stm,
            policy_engine=pe
        )
        print("✅ Agents can be created")
    except Exception as e:
        print(f"❌ Agent error: {e}")
        return False
    
    print("\n✅ All components working!")
    return True


async def test_simple_request():
    """Test a simple request through the system."""
    print("\n5️⃣ Testing Simple Request...")
    
    try:
        from main import Friday
        
        # Create Friday instance
        friday = Friday()
        await friday.startup()
        
        # Test the orchestrator with a simple request
        result = await friday.orchestrator.process_request("What agents do you have?")
        
        if result.get('status') == 'success':
            print("✅ Request processed successfully")
            print(f"Response preview: {str(result.get('response', ''))[:200]}...")
        else:
            print(f"❌ Request failed: {result}")
        
        # Cleanup
        await friday.shutdown()
        
    except Exception as e:
        print(f"❌ Request test error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Friday AI Assistant - Component Test")
    print("=" * 60)
    
    # Run component tests
    if await test_components():
        # Run request test
        await test_simple_request()
    
    print("\n" + "=" * 60)
    print("Test complete! If all tests passed, run: python run_friday.py")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())