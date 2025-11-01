# Friday AI Assistant – Future Features Roadmap

This document tracks **planned but deferred features** for Friday AI Assistant.
These features are **not yet implemented**, but the project architecture is designed to support them later.

---

## 1. Cross-Platform Plugin Support
Friday currently targets **Ubuntu (WSL/Linux)**.
Future plans include:

- **Windows OS**
  - System control using `psutil` (native Windows metrics).
  - File operations via standard Python libraries (already portable).
  - Media control via:
    - `pycaw` (Core Audio API) for volume/mute/unmute.
    - `ctypes` wrappers for advanced system hooks.

- **macOS**
  - System metrics via `psutil` + `platform`.
  - Media control via AppleScript or `osascript`.
  - File ops already portable.

- **Auto-detection Utility**
  - At startup, Friday will log the host OS (Linux/WSL, Windows, macOS).
  - Plugins will load platform-specific implementations.

---

## 2. Enhanced Media Control
- WSL stub currently logs warnings if `pactl` is unavailable.
- Future: add **audio passthrough support** in WSL2 with PulseAudio or PipeWire.
- Windows/macOS branches (see above).

---

## 3. Semantic Memory Enhancements
- Current ChromaDB integration provides vector search.
- Planned:
  - Episodic memory layer (e.g. GibsonAI/memori integration).
  - Long-term storage with pruning/archival.
  - Memory replay for reflection/self-improvement.

---

## 4. Advanced UI
- Current: CLI only.
- Planned:
  - System tray UI (Windows/macOS/Linux).
  - Web dashboard (React/Tailwind + FastAPI backend).
  - Voice PTT (push-to-talk) indicator.

---

## 5. Agent Extensions
- Sandbox execution with rollback.
- Self-healing tasks (auto-retry with context).
- External API plugins (Slack, Discord, Jira, etc.).

---

## 6. DevOps/Release Flow
- Current: Git flow + CI/CD pipeline.
- Planned:
  - Auto-changelog from commit history.
  - Release notes generator (Markdown + HTML).
  - Optional auto-publish to PyPI.

---

### Notes
- Each feature is logged here instead of immediately implemented to **avoid project bloat**.
- Features are considered for **Milestone 7+** or when Ubuntu core is fully stable.
