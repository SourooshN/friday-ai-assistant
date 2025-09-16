# Friday Requirements Specification (Final Draft)

**Goal:** Define functional and non-functional requirements for the Friday AI Assistant.  
This document is authoritative and must guide all design, development, and testing.

---

## 1. System Overview

Friday is an autonomous, modular AI assistant capable of system control, coding, web/social automation, cybersecurity (via separate module), and self-improvement.  
It must operate cross-platform, with initial development in **Windows Subsystem for Linux (WSL)** + **VS Code**, while ensuring future compatibility with both Windows and Linux natively.  
Friday must support both **command-line interaction** and a **frontend UI**.

---

## 2. Functional Requirements

### 2.1 OS Automation
- Launch, close, and control applications across Windows + Linux.
- File system operations: read, write, edit, delete, and move files.
- Clipboard management, screenshots, and window control.
- **Performance metric:** OS commands must execute within **≤ 2 seconds**.

### 2.2 Coding & DevOps
- Implement end-to-end development workflows: plan → edit code → run tests → iterate → commit → PR workflow.
- Must integrate Claude Code and Ollama models for coding tasks.
- Git workflow: feature branch + PR; no direct commits to main.
- **Performance metric:** Able to resolve test failures autonomously within **3 iterations**.

### 2.3 Web Automation
- Automate logins, form submissions, navigation, scraping, and file downloads.
- Extract structured data into CSV/Parquet under `./data/exports/`.
- All credentials stored in **volatile encrypted memory** only.
- **Performance metric:** Complete a 3-step scripted web flow in **≤ 10 seconds**.

### 2.4 Social Media Management
- Platforms: X/Twitter, Reddit, LinkedIn, Instagram, TikTok, YouTube/Shorts.
- Tasks: content creation (text, images, video, voice), scheduling, basic engagement.
- **Human approval required** before any public post.
- **Performance metric:** Generate a week’s worth of draft content in **< 5 minutes**.

### 2.5 Cybersecurity (Ops Module)
- Scope: sandboxed scans, ethical testing, adversarial simulations.
- Tools: nmap, scapy, OWASP ZAP, Docker-sandboxed exploit testing.
- Supports VPN chaining, Tor/onion routing, IP spoofing, and behavioral obfuscation.
- **Performance metric:** Baseline scan of a local VM (top 1000 ports) in **≤ 60 seconds**.

### 2.6 Voice & Multimodal Interaction
- Input: Push-to-talk only (no always-on listening).
- Output: Professional Jarvis-like persona with dynamic emotion control.
- Frontend must display PTT state visually.
- **Performance metric:** Voice recognition accuracy **≥ 95%**, response latency **≤ 2 seconds**.

### 2.7 Self-Modification & Training
- Friday must analyze its own code, identify inefficiencies, and propose/implement changes via sandbox pipeline:
  - dev → sandbox test → adversarial test → optional human review → staging → prod.
- Must crawl GitHub/AI ecosystem for new tools and integrate innovations.
- **Performance metric:** Successfully self-modify and deploy **≥ 1 validated code improvement per week**.

### 2.8 Memory & Knowledge Management
- Use ChromaDB + SQLite for local memory.
- Integrate Supabase / Softr DB / GibsonAI/Memori for long-term recall.
- Knowledge items tagged with provenance metadata.
- **Performance metric:** Retrieve any logged item within **≤ 500 ms**.

---

## 3. Non-Functional Requirements

### 3.1 Reliability
- Auto-rollback to last green commit if deployment fails.
- Sandbox isolation for experimental features.

### 3.2 Security
- Cryptographic checks on downloads, chain of trust for modules.
- Secrets must never be written to disk; only volatile encrypted memory.

### 3.3 Auditability
- All actions logged to `./data/logs/`.
- Retention policy:  
  - Detailed logs kept for **30 days**.  
  - Encrypted archives stored for **1 year**.  

### 3.4 Performance
- OS automation: ≤ 2 seconds.  
- Web flow: ≤ 10 seconds.  
- Voice recognition: ≥ 95% accuracy.  
- Code iteration: ≤ 3 cycles per failure.  
- Memory retrieval: ≤ 500 ms.  

### 3.5 User Interaction
- Both **command-line** and **frontend UI** required.  
- Frontend must allow control over:  
  - Autonomy levels,  
  - Module toggles (Ops, Social, Voice, etc.),  
  - Resource monitoring,  
  - Approval workflows.

---

## 4. Future Extensions

- Expanded Ops Module for government-level operations.  
- Wake word voice activation (opt-in only).  
- Full multi-agent orchestration with independent subsystems.  
- Integration with new AI video/image/TTS tools as they emerge.  

---

**End of Requirements Specification.**
