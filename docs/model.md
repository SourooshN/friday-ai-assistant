# Friday Model Strategy & Orchestration (Final Draft)

**Objective:** Define the end-to-end model layer for Friday: model inventory, routing, context/memory, prompting conventions, self-modification/training pipeline, evaluation, and deployment profiles.

**Design Stance:** Local-first, single-machine friendly. Core reasoning uses a customized open-source **GPT-OSS** (“core brain”), complemented by **Claude Code** for high-precision coding and **Ollama**-served local models for speed and privacy.

---

## 1) Model Inventory

- **Core Brain — GPT-OSS (customized, open-source):**
  - Role: primary general reasoning, planning, multi-step task decomposition.
  - Deployment: local container or process; quantized variants available for lower VRAM.
  - Retraining: supports fine-tuning/LoRA for domain adaptation.
- **Claude Code (Anthropic):**
  - Role: agentic coding, repo refactors, test-driven fixes, PR message synthesis.
  - Invocation: via Claude Code CLI inside VS Code (WSL), or headless for CI agents.
- **Local LLMs (via Ollama):** OpenHermes, Mistral, CodeLlama, Nous-Hermes.
  - Role: fast drafts, code stubs, summarization, lightweight reasoning when latency matters.
  - Selection: auto-routed by task type and token budget.
- **ASR/TTS (pluggable):** Vosk/Whisper (ASR), Waver/pyttsx3 (TTS).
  - Role: push-to-talk interface only (no always-on).
- **Vision/Media (pluggable):** Image/video generators (e.g., SeedDance) for social content.
  - Role: asset generation for social media workflows (human approval required).

---

## 2) Routing Policy

**Goal:** Minimize latency and cost while maximizing correctness. Routing is deterministic with backoff/fallback.

### 2.1 Decision Tree (high-level)
1. **Coding task detected?** → route to **Claude Code** (primary).  
2. **Large-context analysis (≥100k tokens)?** → **Claude** (if available) else **GPT-OSS long-context**.  
3. **Quick draft / low-risk / summary?** → **Ollama** (Mistral/OpenHermes).  
4. **Refactoring or test fix loop?** → **Claude Code**, with test outputs streamed to model.  
5. **Sensitive/local-only data?** → prefer **Ollama** / **GPT-OSS** (offline).  
6. **Social content ideation?** → **Ollama** draft → **GPT-OSS** refine → **HUMAN APPROVAL**.  
7. **Ops Module (cyber/anonymity)** → use **offline/local models** where possible; route long plans to **GPT-OSS**.

### 2.2 Thresholds / SLAs
- Target latency (draft): **< 1.5s** with Ollama small models.
- Target latency (reasoning): **≤ 4s** with GPT-OSS (quantized) for 1–2k tokens.
- Coding PR loop end-to-end: **≤ 5 min** per typical change-set.

### 2.3 Fallbacks
- If model A fails → escalate to model B, preserving reasoning traces in logs.
- If remote API unavailable → fall back to local model with reduced context and staged retries.

---

## 3) Context, Memory & Retrieval

- **Short-term context window management**: sliding window, structured “facts” cache.
- **Vector memory (ChromaDB):** embeddings of codebase, docs, web captures; namespace by project/module.
- **Relational state (SQLite):** task DAGs, approvals, run metadata, model choices, artifacts.
- **Cloud memory:** Supabase / Softr / GibsonAI/Memori for long-term recall and cross-session continuity.
- **Retrieval policy:** top-k (k=8 default) + diversity penalty; max retrieved tokens capped by active model window.

**SLA:** Memory lookups **≤ 500 ms**; provenance stored for each retrieved chunk.

---

## 4) Prompting Conventions

- **System prompt template (core):** specify role, strict tool-use protocol, logging expectations, and output schema.
- **Coding prompt template (Claude Code):** include file diffs, repo map, failing tests; require minimal edits + tests-green criterion.
- **Social prompt template:** require “facts-first” research summary before any draft content; ALWAYS add “HUMAN_APPROVAL_REQUIRED” tag.
- **Ops Module prompts:** must enumerate scope, sandbox, allowed tools; include traffic-shaping guidelines (human-like pacing).

**Output contracts:** JSON-first where possible; strict schemas validated (pydantic) before action.

---

## 5) Self-Modification & Training Pipeline

**Pipeline (mandatory):** `dev → sandbox test → automated adversarial test → optional human review → staging → prod`.

- **Dev:** GPT-OSS proposes code diffs with rationale; unit tests generated/updated.
- **Sandbox test:** containerized env; run tests, lint, security scans; collect metrics.
- **Adversarial tests:** fuzzing, prompt-injection simulation, exploit probes (no network egress beyond sandbox).
- **Optional human review:** required for high-risk modules (Ops, social posting, security tooling).
- **Staging:** deploy feature branch; run integration tests & synthetic E2E user flows.
- **Prod:** merge via PR (never direct-to-main).

**RL/continuous learning:** reward signals from tests pass rates, latency, resource usage, and human approvals; store run summaries in SQLite; candidate policies versioned.

---

## 6) Evaluation & Benchmarks

- **Correctness:** unit/integration test pass rate must be **≥ 99%** on stable suites.
- **Latency:** see SLAs in §2.2; alerts if p95 exceeds thresholds for 15 min.
- **Resource usage:** GPU/CPU caps per profile; throttle if user active.
- **Coding quality:** static analysis scores (ruff/flake8/eslint), cyclomatic complexity budget.
- **Security posture:** no secrets in outputs; checksum verification for downloads; sandbox boundary tests pass.

**Reporting:** Weekly **Self-Review** report in `./reports/self-review/<date>.md` with scorecards and proposed changes.

---

## 7) Deployment Profiles

- **Dev (WSL + VS Code):** Ollama running locally; Claude Code via CLI; local Chroma/SQLite; hot reload.
- **Staging (Docker):** containers for core, memory, UI, and test agents; CI triggers pipeline.
- **Prod (Hybrid):** single-machine Windows/Linux; GPU optional; profiles tuned per hardware.

**Config:** `config/models.dev.yaml`, `config/models.staging.yaml`, `config/models.prod.yaml`

### Example YAML (trimmed)
```yaml
routing:
  code: claude_code
  quick_draft: ollama_mistral
  reasoning: gpt_oss
  long_context: claude_or_gpt_oss_long

ollama:
  models:
    - name: mistral:7b-instruct-q4
    - name: openhermes:7b-q5
    - name: codellama:13b-instruct-q4

gpt_oss:
  variant: 13b-lora-custom
  context: 32k
  quantization: q4

limits:
  max_tokens: 2048
  temperature: 0.2
```

---

## 8) Observability & Controls

- **Logs:** prompt, tool calls, retrieval chunks (redacted), decisions, fallbacks; JSONL append-only.
- **Metrics:** per-model latency, usage, error rates; `/metrics` endpoint (optional).
- **Toggles:** UI controls to switch routing strategies, throttle levels, Ops Module enablement, and autonomy levels.
- **Versioning:** model/routing configs versioned and tied to CHANGELOG entries.

---

## 9) Acceptance Criteria

- Tasks route to correct model per policy, with logged decisions.
- Claude Code reliably handles repo edits/tests/PR flow.
- Offline operation succeeds with Ollama-only profile for supported tasks.
- Self-mod pipeline prevents unsafe changes from reaching prod.
- Weekly self-review report generated with measurable improvements.

---

**End of Model Strategy & Orchestration.**
