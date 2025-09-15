"""
Show the content of scanner_agent.py to debug
"""

from pathlib import Path

file_path = Path("agents/cybersecurity/scanner_agent.py")

if file_path.exists():
    print(f"Content of {file_path}:")
    print("=" * 60)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print(content)
    print("=" * 60)
    print(f"\nFile size: {len(content)} characters")
else:
    print(f"{file_path} does not exist!")