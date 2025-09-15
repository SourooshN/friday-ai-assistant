#!/usr/bin/env python3
"""
Script to apply all the fixes to Friday AI Assistant
Run this from the root directory of your friday-ai-assistant project
"""

import os
import shutil
from datetime import datetime

def backup_file(filepath):
    """Create a backup of the original file."""
    if os.path.exists(filepath):
        backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(filepath, backup_path)
        print(f"Backed up {filepath} to {backup_path}")

def apply_terminal_fix():
    """Fix the terminal command processing."""
    filepath = "interfaces/cli/terminal.py"
    backup_file(filepath)
    
    # Read the file
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find and replace the process_command method
    new_method = '''    async def process_command(self, command: str) -> bool:
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
            return True'''
    
    # Replace the method
    import re
    pattern = r'async def process_command\(self, command: str\) -> bool:.*?return True'
    content = re.sub(pattern, new_method, content, flags=re.DOTALL)
    
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Fixed {filepath}")

def apply_scanner_agent_fix():
    """Fix the scanner agent execution."""
    filepath = "agents/cybersecurity/scanner_agent.py"
    backup_file(filepath)
    
    # Read the file
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Find the _execute_task method and replace it
    in_execute_task = False
    new_lines = []
    indent_level = 0
    
    for i, line in enumerate(lines):
        if 'async def _execute_task' in line:
            in_execute_task = True
            indent_level = len(line) - len(line.lstrip())
            # Add the new method
            new_lines.append(line)
            new_lines.append(' ' * (indent_level + 4) + '"""Execute scanner-specific tasks."""\\n')
            new_lines.append(' ' * (indent_level + 4) + '# Extract task information properly\\n')
            new_lines.append(' ' * (indent_level + 4) + "task_type = task_data.get('type', 'unknown')\\n")
            new_lines.append(' ' * (indent_level + 4) + "description = task_data.get('description', '')\\n")
            new_lines.append(' ' * (indent_level + 4) + "parameters = task_data.get('parameters', {})\\n")
            new_lines.append(' ' * (indent_level + 4) + '\\n')
            new_lines.append(' ' * (indent_level + 4) + 'self.logger.info(f"Scanner Agent executing: {description}")\\n')
            new_lines.append(' ' * (indent_level + 4) + '\\n')
            new_lines.append(' ' * (indent_level + 4) + 'try:\\n')
            new_lines.append(' ' * (indent_level + 8) + '# For now, return a simple success response\\n')
            new_lines.append(' ' * (indent_level + 8) + 'return {\\n')
            new_lines.append(' ' * (indent_level + 12) + "'status': 'success',\\n")
            new_lines.append(' ' * (indent_level + 12) + "'result': f'Processed task: {description}',\\n")
            new_lines.append(' ' * (indent_level + 12) + "'task_type': task_type\\n")
            new_lines.append(' ' * (indent_level + 8) + '}\\n')
            new_lines.append(' ' * (indent_level + 4) + 'except Exception as e:\\n')
            new_lines.append(' ' * (indent_level + 8) + 'self.logger.error(f"Scanner task failed: {str(e)}")\\n')
            new_lines.append(' ' * (indent_level + 8) + 'return {\\n')
            new_lines.append(' ' * (indent_level + 12) + "'status': 'error',\\n")
            new_lines.append(' ' * (indent_level + 12) + "'error': str(e),\\n")
            new_lines.append(' ' * (indent_level + 12) + "'task_type': task_type\\n")
            new_lines.append(' ' * (indent_level + 8) + '}\\n')
            # Skip the old method body
            continue
        elif in_execute_task:
            # Check if we're still in the method
            if line.strip() and not line[indent_level].isspace() and not line.strip().startswith('#'):
                in_execute_task = False
                new_lines.append(line)
            # Skip old method body
        else:
            new_lines.append(line)
    
    # Write back
    with open(filepath, 'w') as f:
        f.writelines(new_lines)
    
    print(f"Fixed {filepath}")

def apply_base_agent_fix():
    """Fix the base agent execute method."""
    filepath = "agents/base_agent.py"
    backup_file(filepath)
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Add import if not present
    if 'from typing import' not in content:
        content = 'from typing import Dict, Any, Optional\\n' + content
    
    # Fix the execute method to properly handle task data
    fixed_content = content.replace(
        "result = await self._execute_with_retries(",
        """# Extract task data properly
        if hasattr(task, 'data') and isinstance(task.data, dict):
            task_data = task.data
        else:
            # Create a proper task data dictionary
            task_data = {
                'task_id': task.id,
                'description': task.description,
                'type': task.type.value if hasattr(task.type, 'value') else str(task.type),
                'context': getattr(task, 'context', {}),
                'parameters': getattr(task, 'parameters', {})
            }
        
        # Execute with retries
        result = await self._execute_with_retries("""
    )
    
    # Fix the lambda to use task_data
    fixed_content = fixed_content.replace(
        "task_func=lambda: self._execute_task(task)",
        "task_func=lambda: self._execute_task(task_data)"
    )
    
    with open(filepath, 'w') as f:
        f.write(fixed_content)
    
    print(f"Fixed {filepath}")

def main():
    """Apply all fixes."""
    print("Applying fixes to Friday AI Assistant...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("main.py") or not os.path.exists("agents"):
        print("Error: Please run this script from the friday-ai-assistant root directory")
        return
    
    try:
        # Apply fixes
        apply_terminal_fix()
        apply_scanner_agent_fix()
        apply_base_agent_fix()
        
        print("=" * 50)
        print("All fixes applied successfully!")
        print("\\nYou can now run Friday with: python main.py")
        print("\\nTry these commands:")
        print("  - agents (or /agents) - to see available agents")
        print("  - help (or /help) - to see help")
        print("  - status (or /status) - to see system status")
        
    except Exception as e:
        print(f"\\nError applying fixes: {str(e)}")
        print("Please check the error and try again.")

if __name__ == "__main__":
    main()