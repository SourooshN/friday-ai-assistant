# Friday AI Assistant

**Friday** is an autonomous, modular AI assistant designed to function like a Jarvis-style system.  
It combines OS automation, coding assistance, web workflows, social media drafting, voice interaction, and a sandboxed Ops module into a single, extensible framework.

---

## ✨ Features

- **OS Automation:** File operations, process control, window management.
- **Coding/DevOps:** Claude Code + Ollama models for edits, tests, PR automation.
- **Web Automation:** Playwright/Selenium workflows, structured scraping.
- **Social Media Agent:** Draft posts/content across major platforms (human approval required).
- **Voice Interface:** Push-to-talk only; Jarvis-like persona with emotional range.
- **Ops Module:** Optional, sandboxed cyber tooling (scans, anonymity, obfuscation).
- **Self-Modification:** dev → sandbox → adversarial test → (optional) human → staging → prod pipeline.
- **Memory:** Local (ChromaDB, SQLite) + cloud (Supabase, Softr, Memori).

---

## 🚀 Quickstart (Dev Environment)

Friday is built/tested initially on **Windows 11 with WSL + VS Code**.

### 1. Install dependencies

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Python + venv
sudo apt install python3 python3-venv python3-pip -y

# Install Node.js (for frontend, optional at this stage)
sudo apt install nodejs npm -y

# Install Docker (for staging)
sudo apt install docker.io docker-compose -y

# Install Git
sudo apt install git -y
```

### 2. Set up project

```bash
# Clone the repo
git clone <your-repo-url> friday-ai-assistant
cd friday-ai-assistant

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python requirements
pip install -r requirements.txt
```

### 3. Install and configure models

```bash
# Install Ollama (local LLM runtime)
curl https://ollama.ai/install.sh | sh

# Verify Ollama
ollama --version

# Pull local models
ollama pull mistral
ollama pull openhermes
ollama pull codellama
ollama pull nous-hermes
```

> Claude Code requires Pro subscription + VS Code plugin.  
> Ensure `claude` CLI is available and authenticated.

### 4. Run Friday (dev)

```bash
# From project root in WSL
source .venv/bin/activate
python main.py
```

---

## 🖥 Usage

- **CLI:** Run tasks directly in terminal.  
- **UI:** Open `ui/` (modern JS frontend) for approvals, toggles, logs, and metrics.  
- **Voice:** Hold push-to-talk (PTT) hotkey to speak; system responds via Jarvis-like voice.  

---

## 📂 Documentation

See `/docs/` for specifications:

- [Requirements](docs/requirements.md)  
- [Capabilities](docs/capabilities.md)  
- [Architecture](docs/architecture.md)  
- [Model Strategy](docs/model.md)  
- [Project Plan](docs/project.md)

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 🔐 Security

See [SECURITY.md](SECURITY.md).

---

## 📜 Changelog

See [CHANGELOG.md](CHANGELOG.md).
