#!/usr/bin/env python3
"""
Friday AI Assistant - Main Entry Point

A modern, modular AI assistant with autonomous capabilities.
"""

import asyncio
import os
import sys
from pathlib import Path

import click

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.kernel import FridayKernel


@click.command()
@click.option('--env', '-e', default=None, help='Environment (dev, staging, prod)')
@click.option('--config-dir', '-c', default=None, help='Configuration directory path')
@click.option('--task', '-t', default=None, help='Execute a single task and exit')
@click.option('--status', is_flag=True, help='Show system status and exit')
def main(env, config_dir, task, status):
    """Friday AI Assistant - Your autonomous AI companion."""

    # Set environment if provided
    if env:
        os.environ['FRIDAY_ENV'] = env

    # Configure paths
    config_path = Path(config_dir) if config_dir else None

    try:
        # Run the async main function
        asyncio.run(async_main(config_path, task, status))
    except KeyboardInterrupt:
        click.echo("\nShutdown requested by user")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


async def async_main(config_path, task, status_only):
    """Async main function."""

    # Initialize Friday kernel
    kernel = FridayKernel(config_dir=config_path)

    # Initialize the system
    success = await kernel.initialize()
    if not success:
        click.echo("Failed to initialize Friday AI Assistant", err=True)
        return

    if status_only:
        # Show status and exit
        status = kernel.get_system_status()
        click.echo("Friday AI Assistant Status:")
        click.echo(f"  Environment: {status['environment']}")
        click.echo(f"  Initialized: {status['initialized']}")
        click.echo(f"  Running: {status['running']}")

        if 'components' in status:
            click.echo("  Components:")
            for component, comp_status in status['components'].items():
                click.echo(f"    {component}: {comp_status}")

        await kernel.shutdown()
        return

    if task:
        # Execute single task and exit
        click.echo(f"Executing task: {task}")

        try:
            task_id = await kernel.submit_task(task)
            click.echo(f"Task submitted with ID: {task_id}")

            # Wait a bit for task completion (simplified)
            await asyncio.sleep(2)

            status = await kernel.get_task_status(task_id)
            click.echo(f"Task status: {status}")

        except Exception as e:
            click.echo(f"Task execution failed: {e}", err=True)

        await kernel.shutdown()
        return

    # Interactive mode
    click.echo("Friday AI Assistant starting...")
    click.echo("Type 'help' for commands, 'quit' or Ctrl+C to exit")

    # Start the kernel in the background
    kernel_task = asyncio.create_task(kernel.run())

    # Simple command loop
    try:
        while kernel.is_running:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "friday> "
                )

                user_input = user_input.strip()

                if user_input.lower() in ['quit', 'exit', 'bye']:
                    break
                elif user_input.lower() == 'help':
                    show_help()
                elif user_input.lower() == 'status':
                    status = kernel.get_system_status()
                    click.echo(f"Status: {status}")
                elif user_input.lower() == 'plugins':
                    if kernel.plugin_host:
                        plugins = kernel.plugin_host.get_loaded_plugins()
                        click.echo(f"Loaded plugins: {plugins}")
                    else:
                        click.echo("Plugin host not available")
                elif user_input:
                    # Submit as task
                    task_id = await kernel.submit_task(user_input)
                    click.echo(f"Task submitted: {task_id}")

            except EOFError:
                break
            except Exception as e:
                click.echo(f"Error: {e}", err=True)

    finally:
        click.echo("Shutting down Friday AI Assistant...")
        await kernel.shutdown()

        # Cancel the kernel task if it's still running
        if not kernel_task.done():
            kernel_task.cancel()
            try:
                await kernel_task
            except asyncio.CancelledError:
                pass


def show_help():
    """Show help information."""
    click.echo("""
Friday AI Assistant Commands:

  help      - Show this help message
  status    - Show system status
  plugins   - Show loaded plugins
  quit/exit - Exit Friday

  Or just type any request and Friday will try to help!

Examples:
  friday> Hello, how are you?
  friday> List files in current directory
  friday> Create a Python script that says hello
""")


if __name__ == '__main__':
    main()