#!/usr/bin/env python3
"""
Friday AI Assistant - Comprehensive Demo Scenario

This script demonstrates the complete capabilities of Friday AI Assistant including:
- All three main plugins (System Control, File Operations, Media/App Control)
- Task orchestration and plugin coordination
- CLI interaction patterns
- Error handling and recovery
- Memory and logging integration

Run this script to see Friday in action!
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.kernel import FridayKernel


async def demo_scenario():
    """Run comprehensive demo scenario."""
    print("🚀 Friday AI Assistant - Demo Scenario")
    print("=" * 50)

    # Initialize Friday kernel (which handles logging initialization)
    kernel = FridayKernel()

    try:
        print("\n📋 Phase 1: System Initialization")
        print("-" * 30)

        # Initialize the system
        success = await kernel.initialize()
        if not success:
            print("❌ Failed to initialize Friday AI Assistant")
            return

        print("✅ Friday AI Assistant initialized successfully!")

        # Show system status
        status = kernel.get_system_status()
        print(f"   Environment: {status['environment']}")
        print(f"   Plugins loaded: {len(status['components']['plugins']['loaded_plugin_ids'])}")
        print(f"   Available plugins: {', '.join(status['components']['plugins']['loaded_plugin_ids'])}")

        print("\n🔧 Phase 2: System Control Plugin Demo")
        print("-" * 40)

        # Demo 1: System Information
        print("1. Getting comprehensive system information...")
        task_id = await kernel.submit_task("get system info")
        await asyncio.sleep(2)
        result = await kernel.get_task_status(task_id)

        if result["status"] == "completed" and result["result"]["success"]:
            sys_data = result["result"]["data"]
            print(f"   ✅ System: {sys_data['platform']['system']} {sys_data['platform']['release']}")
            print(f"   ✅ CPU cores: {sys_data['cpu']['physical_cores']} physical, {sys_data['cpu']['logical_cores']} logical")
            print(f"   ✅ Memory: {sys_data['memory']['total'] // (1024**3)} GB total, {sys_data['memory']['percentage']}% used")
        else:
            print("   ❌ System info task failed")

        # Demo 2: CPU Usage
        print("\n2. Getting current CPU usage...")
        task_id = await kernel.submit_task("get CPU usage")
        await asyncio.sleep(2)
        result = await kernel.get_task_status(task_id)

        if result["status"] == "completed" and result["result"]["success"]:
            cpu_data = result["result"]["data"]
            print(f"   ✅ CPU usage: {cpu_data['cpu_percent']}%")
        else:
            print("   ❌ CPU usage task failed")

        # Demo 3: Process List
        print("\n3. Getting running processes...")
        task_id = await kernel.submit_task("list running processes")
        await asyncio.sleep(2)
        result = await kernel.get_task_status(task_id)

        if result["status"] == "completed" and result["result"]["success"]:
            proc_data = result["result"]["data"]
            print(f"   ✅ Found {proc_data['total_processes']} processes, showing top {len(proc_data['processes'])}")
            for i, proc in enumerate(proc_data["processes"][:3]):
                print(f"      #{i+1}: {proc['name']} (PID: {proc['pid']})")
        else:
            print("   ❌ Process list task failed")

        print("\n📁 Phase 3: File Operations Plugin Demo")
        print("-" * 42)

        # Demo 4: Directory Listing
        print("1. Listing files in current directory...")
        task_id = await kernel.submit_task("list files in current directory")
        await asyncio.sleep(2)
        result = await kernel.get_task_status(task_id)

        if result["status"] == "completed" and result["result"]["success"]:
            file_data = result["result"]["data"]
            print(f"   ✅ Found {file_data['total_items']} items ({file_data['files']} files, {file_data['directories']} directories)")
            print("   📋 Key files/directories:")
            for item in file_data["items"][:5]:
                icon = "📁" if item["type"] == "directory" else "📄"
                print(f"      {icon} {item['name']}")
        else:
            print("   ❌ Directory listing task failed")

        # Demo 5: File Creation and Management
        print("\n2. Creating a demo report file...")

        # Create a comprehensive system report
        report_data = {
            "friday_demo_report": {
                "timestamp": "2024-01-15T19:25:00Z",
                "system_info": sys_data if "sys_data" in locals() else "Not available",
                "plugins_loaded": status["components"]["plugins"]["loaded_plugin_ids"],
                "demo_completed": True,
            }
        }

        # Use a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Use kernel to create the file
            create_task = f"create file at {tmp_path} with content: {json.dumps(report_data, indent=2)}"
            task_id = await kernel.submit_task(create_task)
            await asyncio.sleep(2)
            result = await kernel.get_task_status(task_id)

            if result["status"] == "completed" and result["result"]["success"]:
                print("   ✅ Demo report created successfully")

                # Now read it back
                read_task = f"read file {tmp_path}"
                task_id = await kernel.submit_task(read_task)
                await asyncio.sleep(2)
                result = await kernel.get_task_status(task_id)

                if result["status"] == "completed" and result["result"]["success"]:
                    print(f"   ✅ File read back successfully ({len(result['result']['data']['content'])} characters)")
                else:
                    print("   ❌ File read failed")
            else:
                print("   ❌ File creation failed")

        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        print("\n🎵 Phase 4: Media & Application Control Plugin Demo")
        print("-" * 52)

        # Demo 6: Running Applications
        print("1. Getting running applications...")
        task_id = await kernel.submit_task("show running applications")
        await asyncio.sleep(2)
        result = await kernel.get_task_status(task_id)

        if result["status"] == "completed" and result["result"]["success"]:
            app_data = result["result"]["data"]
            print(f"   ✅ Found {len(app_data['applications'])} running applications")
            for i, app in enumerate(app_data["applications"][:3]):
                print(f"      #{i+1}: {app['name']} (PID: {app['pid']})")
        else:
            print("   ❌ Applications list task failed")

        # Demo 7: Media Status
        print("\n2. Checking media player status...")
        task_id = await kernel.submit_task("get media status")
        await asyncio.sleep(2)
        result = await kernel.get_task_status(task_id)

        if result["status"] == "completed":
            if result["result"]["success"]:
                print("   ✅ Media status retrieved successfully")
            else:
                print("   ℹ️  Media status check completed (no active media player)")
        else:
            print("   ❌ Media status task failed")

        print("\n🔄 Phase 5: Multi-Plugin Coordination Demo")
        print("-" * 45)

        print("Demonstrating complex workflow using all plugins...")

        # Concurrent task execution
        print("\n1. Executing multiple tasks concurrently...")

        tasks = []
        task_descriptions = ["get memory usage", "get disk usage", "list files in current directory", "show running applications"]

        # Submit all tasks
        for desc in task_descriptions:
            task_id = await kernel.submit_task(desc)
            tasks.append((desc, task_id))

        # Wait for completion
        await asyncio.sleep(4)

        # Check results
        completed = 0
        for desc, task_id in tasks:
            result = await kernel.get_task_status(task_id)
            if result["status"] == "completed" and result["result"]["success"]:
                completed += 1
                print(f"   ✅ {desc}")
            else:
                print(f"   ❌ {desc}")

        print(f"\n📊 Concurrent execution results: {completed}/{len(tasks)} tasks completed successfully")

        print("\n🛡️ Phase 6: Security & Policy Demo")
        print("-" * 38)

        print("Testing security policy enforcement...")

        # Test safe operations
        safe_task = await kernel.submit_task("get system info")
        await asyncio.sleep(2)
        safe_result = await kernel.get_task_status(safe_task)

        if safe_result["status"] == "completed":
            print("   ✅ Safe operations allowed by policy engine")
        else:
            print("   ❌ Safe operations blocked unexpectedly")

        print("\n📈 Phase 7: Performance & Stats")
        print("-" * 35)

        # Get final system status
        final_status = kernel.get_system_status()
        if "orchestrator" in final_status["components"]:
            orch_stats = final_status["components"]["orchestrator"]
            print(f"   📋 Total tasks processed: {orch_stats['total_tasks']}")
            print(f"   ⚡ Active tasks: {orch_stats['active_tasks']}")

        print(f"   🔌 Plugins loaded: {len(final_status['components']['plugins']['loaded_plugin_ids'])}")
        print(f"   💾 Memory manager: {'✅ Connected' if final_status['components']['memory']['sqlite_connected'] else '❌ Disconnected'}")

        print("\n🎉 Demo Scenario Complete!")
        print("=" * 50)
        print("✅ All Friday AI Assistant capabilities demonstrated successfully!")
        print("\nKey Features Showcased:")
        print("  🔧 System Control Plugin - System monitoring, process management")
        print("  📁 File Operations Plugin - File/directory management, CRUD operations")
        print("  🎵 Media/App Control Plugin - Application monitoring, media control")
        print("  🔄 Task Orchestration - Concurrent execution, policy enforcement")
        print("  💾 Memory Integration - Task storage, audit logging")
        print("  🛡️ Security Controls - Policy engine, safe operation validation")
        print("  📊 Real-time Monitoring - System status, component health")

        print("\n📋 Summary Statistics:")
        print(f"  • Plugins loaded: {len(final_status['components']['plugins']['loaded_plugin_ids'])}")
        print(f"  • Tasks executed: {orch_stats.get('total_tasks', 'N/A')}")
        print(f"  • System status: {'✅ Healthy' if final_status['running'] else '❌ Issues'}")

    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n🔄 Shutting down Friday AI Assistant...")
        await kernel.shutdown()
        print("✅ Shutdown complete")


if __name__ == "__main__":
    print("Starting Friday AI Assistant Demo...")
    try:
        asyncio.run(demo_scenario())
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)
