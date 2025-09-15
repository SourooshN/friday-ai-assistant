#!/usr/bin/env python3
"""
Fix the syntax error in base_agent.py
"""

import os

def fix_base_agent():
    """Fix the base_agent.py file by restoring from backup and applying correct fix."""
    
    # First, restore from backup
    backup_files = [f for f in os.listdir('agents') if f.startswith('base_agent.py.backup_')]
    if backup_files:
        latest_backup = sorted(backup_files)[-1]
        print(f"Restoring from backup: agents/{latest_backup}")
        
        # Copy backup to original
        import shutil
        shutil.copy2(f'agents/{latest_backup}', 'agents/base_agent.py')
        print("Restored base_agent.py from backup")
    else:
        print("Warning: No backup found. Proceeding with manual fix...")
    
    # Now read the file and find the execute method
    with open('agents/base_agent.py', 'r') as f:
        lines = f.readlines()
    
    # Find the execute method and properly fix it
    new_lines = []
    in_execute_method = False
    found_try = False
    indent_level = 0
    
    for i, line in enumerate(lines):
        if 'async def execute(self, task: Task)' in line:
            in_execute_method = True
            new_lines.append(line)
            continue
            
        if in_execute_method and line.strip().startswith('try:'):
            found_try = True
            indent_level = len(line) - len(line.lstrip())
            new_lines.append(line)
            # Add the fixed code after try:
            new_lines.append(' ' * (indent_level + 4) + '# Start status update\n')
            new_lines.append(' ' * (indent_level + 4) + 'status_task = asyncio.create_task(self._update_status_periodically(task.id))\n')
            new_lines.append(' ' * (indent_level + 4) + '\n')
            new_lines.append(' ' * (indent_level + 4) + '# Extract task data properly\n')
            new_lines.append(' ' * (indent_level + 4) + 'if hasattr(task, "data") and isinstance(task.data, dict):\n')
            new_lines.append(' ' * (indent_level + 8) + 'task_data = task.data\n')
            new_lines.append(' ' * (indent_level + 4) + 'else:\n')
            new_lines.append(' ' * (indent_level + 8) + '# Create a proper task data dictionary\n')
            new_lines.append(' ' * (indent_level + 8) + 'task_data = {\n')
            new_lines.append(' ' * (indent_level + 12) + '"task_id": task.id,\n')
            new_lines.append(' ' * (indent_level + 12) + '"description": task.description,\n')
            new_lines.append(' ' * (indent_level + 12) + '"type": task.type.value if hasattr(task.type, "value") else str(task.type),\n')
            new_lines.append(' ' * (indent_level + 12) + '"context": getattr(task, "context", {}),\n')
            new_lines.append(' ' * (indent_level + 12) + '"parameters": getattr(task, "parameters", {})\n')
            new_lines.append(' ' * (indent_level + 8) + '}\n')
            new_lines.append(' ' * (indent_level + 4) + '\n')
            continue
            
        if in_execute_method and found_try and 'result = await self._execute_with_retries(' in line:
            # Replace this line with the fixed version
            new_lines.append(' ' * (indent_level + 4) + '# Execute with retries\n')
            new_lines.append(' ' * (indent_level + 4) + 'result = await self._execute_with_retries(\n')
            new_lines.append(' ' * (indent_level + 8) + 'task_func=lambda: self._execute_task(task_data),\n')
            new_lines.append(' ' * (indent_level + 8) + 'task_id=task.id,\n')
            new_lines.append(' ' * (indent_level + 8) + 'max_retries=self.max_retries\n')
            new_lines.append(' ' * (indent_level + 4) + ')\n')
            # Skip the original line and any continuation lines
            j = i + 1
            while j < len(lines) and (lines[j].strip() == '' or lines[j].startswith(' ' * (indent_level + 8))):
                if ')' in lines[j]:
                    break
                j += 1
            continue
            
        if in_execute_method and line.strip() and not line[0].isspace():
            # We've left the execute method
            in_execute_method = False
            found_try = False
            
        new_lines.append(line)
    
    # Write the fixed content
    with open('agents/base_agent.py', 'w') as f:
        f.writelines(new_lines)
    
    print("Fixed agents/base_agent.py")

if __name__ == "__main__":
    print("Fixing base_agent.py syntax error...")
    try:
        fix_base_agent()
        print("\nFix applied successfully!")
        print("You can now run: python main.py")
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nIf the automatic fix doesn't work, you can manually restore from backup:")
        print("1. Go to the agents directory")
        print("2. Find the latest backup file (base_agent.py.backup_*)")
        print("3. Copy it back to base_agent.py")