"""
Terminal interface for Friday AI Assistant.
Provides interactive command-line interface with rich formatting.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import sys
import os

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich import box
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter

from core.orchestrator import Orchestrator


class TerminalInterface:
    """Rich terminal interface for Friday."""
    
    def __init__(self, orchestrator: Orchestrator):
        """Initialize terminal interface."""
        self.orchestrator = orchestrator
        self.console = Console()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.is_running = False
        
        # Command history
        self.command_history: List[str] = []
        self.history_file = "data/logs/command_history.txt"
        
        # Auto-completion
        self.commands = [
            '/help', '/status', '/agents', '/history', '/clear', '/exit',
            'help', 'status', 'agents', 'history', 'clear', 'exit'
        ]
        
        # Prompt session for better input handling
        self._init_prompt_session()
        
        self.logger.info("Initialized Terminal Interface")
    
    def _init_prompt_session(self):
        """Initialize prompt session with history and auto-complete."""
        # Create history directory if it doesn't exist
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        
        # Create prompt session
        self.prompt_session = PromptSession(
            history=FileHistory(self.history_file),
            auto_suggest=AutoSuggestFromHistory(),
            completer=WordCompleter(self.commands, ignore_case=True),
            complete_while_typing=True
        )
    
    def start(self):
        """Start the terminal interface."""
        self.is_running = True
        self._display_welcome()
        self.logger.info("Terminal interface started")
    
    def stop(self):
        """Stop the terminal interface."""
        self.is_running = False
        self.logger.info("Terminal interface stopped")
    
    def _display_welcome(self):
        """Display welcome message and help."""
        welcome_panel = Panel(
            "[bold cyan]Welcome to Friday AI Assistant![/bold cyan]\n"
            "Your autonomous AI desktop assistant\n\n"
            "[yellow]Available Commands:[/yellow]\n"
            "• /help - Show this help message\n"
            "• /status - Show system status\n"
            "• /agents - List available agents\n"
            "• /history - Show command history\n"
            "• /clear - Clear the screen\n"
            "• /exit - Exit Friday\n\n"
            "[green]Just type your request naturally, for example:[/green]\n"
            '• "Scan my network for open ports"\n'
            '• "Create a Python web scraper for tech news"\n'
            '• "Help me organize my desktop files"\n'
            '• "Generate a report on system performance"\n\n'
            "[dim]Type your command or request below...[/dim]",
            title="🤖 Friday AI Assistant",
            border_style="bright_blue",
            padding=(1, 2),
            width=None
        )
        self.console.print(welcome_panel)
    
    async def process_command(self, command: str) -> bool:
        """Process a command and return whether to continue the loop."""
        try:
            command = command.strip()
            if not command:
                return True
            
            # Add to history
            self.command_history.append(command)
            
            # Check for system commands (with or without /)
            command_lower = command.lower()
            
            # Handle both /command and command formats
            if command_lower in ['/exit', 'exit', '/quit', 'quit']:
                return False
            elif command_lower in ['/help', 'help']:
                self._show_help()
            elif command_lower in ['/status', 'status']:
                await self._show_status()
            elif command_lower in ['/agents', 'agents']:
                self._show_agents()
            elif command_lower in ['/history', 'history']:
                self._show_history()
            elif command_lower in ['/clear', 'clear']:
                self._clear_screen()
            elif command.startswith('/'):
                self.console.print(f"[yellow]Unknown command: {command}[/yellow]")
                self.console.print("Type /help for available commands")
            else:
                # Process as AI request
                await self._process_ai_request(command)
            
            return True
            
        except KeyboardInterrupt:
            return False
        except Exception as e:
            self.logger.error(f"Error processing command: {e}")
            self.console.print(f"[red]Error: {str(e)}[/red]")
            return True
    
    async def _process_ai_request(self, request: str):
        """Process an AI request through the orchestrator."""
        with self.console.status("[bold green]Friday is thinking...", spinner="dots"):
            try:
                # Get response from orchestrator
                result = await self.orchestrator.process_request(request)
                
                # Display result
                self._display_result(result)
                
            except asyncio.TimeoutError:
                self.console.print("[red]Request timed out. Please try again.[/red]")
            except Exception as e:
                self.logger.error(f"Error processing AI request: {e}")
                self.console.print(f"[red]Error: {str(e)}[/red]")
    
    def _display_result(self, result: Dict[str, Any]):
        """Display the result of an AI request."""
        if result.get('status') == 'error':
            self.console.print(f"[red]Error: {result.get('message', 'Unknown error')}[/red]")
            if result.get('details'):
                self.console.print(f"[dim]{result['details']}[/dim]")
            if result.get('suggestion'):
                self.console.print(f"[yellow]Suggestion: {result['suggestion']}[/yellow]")
            return
        
        # Handle different response types
        response = result.get('response', result.get('result', ''))
        
        if isinstance(response, str):
            # Simple text response
            panel = Panel(
                Markdown(response) if response else "No response generated",
                title="[bold green]Friday's Response[/bold green]",
                border_style="green",
                padding=(1, 2)
            )
            self.console.print(panel)
        elif isinstance(response, dict):
            # Structured response
            self._display_structured_response(response)
        elif isinstance(response, list):
            # List response
            self._display_list_response(response)
        else:
            # Fallback
            self.console.print(str(response))
        
        # Show execution details if available
        if result.get('execution_time'):
            self.console.print(f"\n[dim]Execution time: {result['execution_time']:.2f}s[/dim]")
        
        if result.get('agents_used'):
            agents = ", ".join(result['agents_used'])
            self.console.print(f"[dim]Agents used: {agents}[/dim]")
    
    def _display_structured_response(self, response: Dict[str, Any]):
        """Display a structured response."""
        for key, value in response.items():
            if isinstance(value, dict) or isinstance(value, list):
                self.console.print(f"\n[bold]{key}:[/bold]")
                self.console.print(value)
            else:
                self.console.print(f"[bold]{key}:[/bold] {value}")
    
    def _display_list_response(self, response: List[Any]):
        """Display a list response."""
        for i, item in enumerate(response, 1):
            self.console.print(f"{i}. {item}")
    
    def _show_help(self):
        """Show help information."""
        help_table = Table(title="Friday AI Commands", box=box.ROUNDED)
        help_table.add_column("Command", style="cyan", no_wrap=True)
        help_table.add_column("Description", style="white")
        
        commands = [
            ("/help", "Show this help message"),
            ("/status", "Show system status and agent metrics"),
            ("/agents", "List all available agents and their capabilities"),
            ("/history", "Show command history"),
            ("/clear", "Clear the terminal screen"),
            ("/exit", "Exit Friday AI Assistant"),
        ]
        
        for cmd, desc in commands:
            help_table.add_row(cmd, desc)
        
        self.console.print(help_table)
        
        self.console.print("\n[bold yellow]Natural Language Requests:[/bold yellow]")
        examples = [
            "• Scan my network for security vulnerabilities",
            "• Create a Python script to automate file organization",
            "• Generate a weekly report of system performance",
            "• Help me set up a development environment for React",
            "• Find and summarize the latest tech news",
        ]
        for example in examples:
            self.console.print(f"  {example}")
    
    async def _show_status(self):
        """Show system status."""
        with self.console.status("Gathering system status..."):
            status = await self.orchestrator.get_status()
        
        # System overview
        overview_table = Table(title="System Status", box=box.ROUNDED)
        overview_table.add_column("Component", style="cyan")
        overview_table.add_column("Status", style="green")
        
        overview_table.add_row("Orchestrator", "🟢 Active" if status.get('is_running') else "🔴 Inactive")
        overview_table.add_row("Active Agents", str(len(status.get('agents', {}))))
        overview_table.add_row("Models Available", str(status.get('models_available', 0)))
        overview_table.add_row("Memory Usage", f"{status.get('memory_usage', 0):.1f} MB")
        
        self.console.print(overview_table)
        
        # Agent details
        if status.get('agents'):
            agent_table = Table(title="Agent Status", box=box.ROUNDED)
            agent_table.add_column("Agent", style="cyan")
            agent_table.add_column("Type", style="yellow")
            agent_table.add_column("Status", style="green")
            agent_table.add_column("Tasks", justify="right")
            
            for agent_name, agent_info in status['agents'].items():
                agent_table.add_row(
                    agent_name,
                    agent_info.get('type', 'Unknown'),
                    "🟢 Active" if agent_info.get('is_running') else "🔴 Inactive",
                    str(agent_info.get('metrics', {}).get('total_tasks', 0))
                )
            
            self.console.print(agent_table)
    
    def _show_agents(self):
        """Show available agents and their capabilities."""
        agents = self.orchestrator.agents
        
        if not agents:
            self.console.print("[yellow]No agents available[/yellow]")
            return
        
        agent_table = Table(title="Available Agents", box=box.ROUNDED)
        agent_table.add_column("Agent", style="cyan", no_wrap=True)
        agent_table.add_column("Capabilities", style="green")
        agent_table.add_column("Description", style="white")
        
        agent_descriptions = {
            "ScannerAgent": "Performs security scans and vulnerability assessments",
            "CodingAgent": "Writes code, creates applications, and handles development tasks",
            "AutomationAgent": "Automates web browsing, form filling, and online tasks",
            "OSControlAgent": "Controls OS functions, manages files, and system settings",
            "OrchestratorAgent": "Coordinates other agents and plans complex tasks"
        }
        
        for agent_name, agent in agents.items():
            capabilities = ", ".join(agent.capabilities)
            description = agent_descriptions.get(agent_name, "Specialized task agent")
            agent_table.add_row(agent_name, capabilities, description)
        
        self.console.print(agent_table)
    
    def _show_history(self):
        """Show command history."""
        if not self.command_history:
            self.console.print("[yellow]No command history[/yellow]")
            return
        
        history_table = Table(title="Command History", box=box.ROUNDED)
        history_table.add_column("#", style="cyan", width=4)
        history_table.add_column("Command", style="white")
        history_table.add_column("Time", style="dim")
        
        # Show last 20 commands
        for i, cmd in enumerate(self.command_history[-20:], 1):
            history_table.add_row(
                str(i),
                cmd[:80] + "..." if len(cmd) > 80 else cmd,
                datetime.now().strftime("%H:%M:%S")  # This is simplified
            )
        
        self.console.print(history_table)
    
    def _clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
        self._display_welcome()
    
    async def run_interactive(self):
        """Run the interactive terminal loop."""
        self.console.print("")  # Empty line for spacing
        
        while self.is_running:
            try:
                # Get user input with rich prompt
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.prompt_session.prompt("\nFriday: ")
                )
                
                # Display user input
                self.console.print(f"[bold blue]You:[/bold blue] {user_input}")
                
                # Process command
                should_continue = await self.process_command(user_input)
                if not should_continue:
                    break
                    
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /exit to quit Friday[/yellow]")
                continue
            except EOFError:
                break
            except Exception as e:
                self.logger.error(f"Error in interactive loop: {e}")
                self.console.print(f"[red]Unexpected error: {str(e)}[/red]")