"""Setup configuration for Friday AI Assistant"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="friday-ai-assistant",
    version="1.0.0",
    author="Friday Development Team",
    author_email="friday@example.com",
    description="Autonomous AI Desktop Assistant inspired by JARVIS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/friday-ai-assistant",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "scripts"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows :: Windows 11",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.11",
    install_requires=[
        # Core dependencies only
        "ollama>=0.3.3",
        "langchain>=0.3.7",
        "pyyaml>=6.0.2",
        "click>=8.1.7",
        "loguru>=0.7.2",
        "python-dotenv>=1.0.1",
    ],
    extras_require={
        "dev": [
            "pytest>=8.3.4",
            "pytest-asyncio>=0.24.0",
            "pytest-cov>=6.0.0",
            "black>=24.10.0",
            "flake8>=7.1.1",
            "mypy>=1.13.0",
        ],
        "voice": [
            "SpeechRecognition>=3.11.0",
            "pyttsx3>=2.90",
            "vosk>=0.3.45",
            "pyaudio>=0.2.14",
        ],
        "web": [
            "selenium>=4.27.1",
            "playwright>=1.49.0",
            "beautifulsoup4>=4.12.3",
        ],
        "security": [
            "python-nmap>=0.7.1",
            "scapy>=2.6.1",
            "cryptography>=44.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "friday=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "friday": [
            "config/*.yaml",
            "data/.gitkeep",
        ],
    },
)