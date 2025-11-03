# Friday Capability Specification (Final Draft)

**Goal:** Friday is an autonomous, modular AI assistant capable of system control, self-modification, cyber-ops (via a separate module), web and social media automation, and continuous self-improvement. This specification integrates all requirements, including user expansions.

---

## Global Principles

- **Autonomy:** Friday operates with unrestricted autonomy, but all destructive or high-risk actions follow a controlled pipeline (dev → sandbox → adversarial test → optional human review → staging → prod).
- **Auditability:** All actions logged to `./data/logs/`, short-term retention (30 days detailed logs), long-term encrypted archives (1 year) with Supabase / Softr DB / GibsonAI/Memori integration.
- **Separation of Concerns:** Advanced offensive/anonymity features implemented in a separate **Ops Module**, distinct from core assistant.
- **Extensibility:** Friday continuously researches GitHub and AI ecosystems for new models, frameworks, and tools to self-improve, with integration subject to sandbox pipeline.

---

## Core Capabilities

### 1. OS Automation & Device Control
- Launch/close apps, manipulate windows, manage files, run scripts.
- File read/write/delete within repo scope; outside paths controlled by policy flags.
- Low-priority mode when system in use, high-priority when idle.
- **Available Plugins:**
  - `os_hello`: Basic greeting functionality that prints "Hello, Friday!" - serves as a simple example and health check for the plugin system.

### 2. Autonomous Coding & DevOps
- Plan → edit code → run tests → iterate → commit → PR workflow.
- No direct commits to `main`. All changes via feature branches + PRs.
- Automated self-review, CI/CD, and staging environment deployment.

### 3. Web Automation & Data Extraction
- Automate web flows (logins, form submissions, scraping).
- Save structured outputs to `./data/exports/`.
- Domain allowlist enforced; credentials in volatile encrypted memory only.

### 4. Social Media Agent
- Platforms: X/Twitter, Reddit, LinkedIn, Instagram, TikTok, YouTube/Shorts.
- Functions: content creation (text, image, video, voice), scheduling, proactive engagement.
- **Human approval required before posting any content.**
- Integrates AI tools for image/video/audio generation (SeedDance, Waver, etc.).

### 5. Cybersecurity Module (Ops)
- Tools: nmap, scapy, OWASP ZAP, sandboxed exploit testing.
- Supports VPNs, proxy chains, Tor/onion routing, IP spoofing, behavioral obfuscation.
- All actions scoped to approved targets. Default enabled but isolated from core system.

### 6. Voice & Multimodal Interface
- Push-to-talk (PTT) input only. No always-on listening.
- Voice persona: neutral, professional, Jarvis-like, with adjustable emotional intensity.
- Frontend: web/app interface similar to ChatGPT/Claude for easy interaction.

### 7. Self-Modification & Training
- Friday reviews its own source code, identifies inefficiencies, rewrites modules.
- Pipeline: dev → sandbox → adversarial test → (optional) Red Team review → staging → prod.
- Crawls GitHub to compare other AI projects; integrates useful innovations safely.

### 8. Memory & Knowledge Management
- Vector DB (ChromaDB) + relational DB (SQLite) + cloud DB (Supabase/Softr/Memori).
- Supports both short-term recall and long-term memory persistence.
- All knowledge tagged with provenance for auditability.

### 9. Security & Trust Management
- Chain-of-trust enforced for modules and downloads.
- Cryptographic checks (hash verification, digital signatures).
- Secure inter-module communication.

### 10. Resource Management & Optimization
- Monitors CPU/GPU/memory/disk usage via psutil and OS APIs.
- Dynamically throttles/suspends background agents.
- Prompts user only for destructive or high-impact tasks.

### 11. Self-Optimization
- Weekly self-review reports at `./reports/self-review/`.
- Proposals for dependency upgrades, prompt improvements, and model swaps.
- Auto-apply gated by config flags.

---

## Configuration Summary (YAML)

```yaml
autonomy:
  unrestricted: true
  sandbox_pipeline: true
  ops_module: enabled

git:
  workflow: feature_branch_pr
  human_approval: required

logging:
  path: data/logs
  retention:
    detailed: 30d
    archive: 1y_encrypted

social_media:
  human_approval: true
  platforms: [twitter, reddit, linkedin, instagram, tiktok, youtube]

voice:
  mode: push_to_talk
  persona: jarvis_like_professional

memory:
  local: [sqlite, chromadb]
  cloud: [supabase, softr, memori]

security:
  chain_of_trust: true
  crypto_checks: true
```

---

## Frontend Requirement

- A user-facing frontend for interaction: web dashboard or native app.
- Must expose: logs, approvals, autonomy toggles, resource status, agent modules.

---

**End of Capabilities Specification.**
