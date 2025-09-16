# Friday Project Overview & Plan (Final Draft)

**Purpose:** Define scope, milestones, deliverables, workflows, and acceptance criteria to ship Friday from Dev → Staging → Prod, aligned with Requirements, Capabilities, Architecture, and Model Strategy.

---

## 1) Scope

- Build Friday as a **monolithic core with plugin architecture**, single-machine/local-first.
- Implement core modules: OS Automation, Coding/DevOps, Web Automation, Social, Voice, Memory, UI, and **Ops Module** (separate).
- Environments: **Dev = WSL + VS Code**, **Staging = Docker**, **Prod = Hybrid (Windows/Linux)**.
- Frontend: Any modern JavaScript framework.
- Git policy: **feature branches + PRs only**; human approval required for *all* merges and social posting.

---

## 2) Roles & Automation

- **Friday (AI):** planning, coding, tests, docs, PR creation, self-review reports.
- **Human Owner:** approves PRs, approves social content, adjudicates high-risk Ops changes.
- **CI/CD:** run tests/lint, build docker images, spin up staging, post results on PR.

---

## 3) Milestones & Deliverables

### M1 — Foundations (Week 1)
- Repo hygiene: directory layout, base configs (`config/dev|staging|prod.yaml`), logging scaffold.
- Core Kernel + Orchestrator skeleton with Plugin Host.
- Memory adapters (ChromaDB + SQLite) wired; volatile secret store stub.
- Deliverables: runnable CLI, logs in `./data/logs/`, unit test skeleton.

### M2 — OS Automation & UI (Week 2)
- OS plugin: file ops, app launch/close, window control, guard rails.
- UI shell: approvals, toggles, logs view, resource panel, PTT indicator (placeholder).
- Deliverables: E2E demo: “create/edit/delete a file” via UI and CLI; metrics view.

### M3 — Coding/DevOps Loop (Week 3)
- Claude Code integration; test-runner wiring (pytest/npm).
- Git flow automation: branch → edits → tests → PR with summary.
- Deliverables: PRs opened automatically from feature tasks; tests green.

### M4 — Web Automation & Social Drafts (Week 4)
- Playwright/Selenium flows; CSV export to `./data/exports/`.
- Social agent (draft-only with human approval): content calendar + asset pipeline.
- Deliverables: scripted site flow; one-week content plan with draft assets (no posting).

### M5 — Ops Module (Week 5)
- Sandbox config; nmap/scapy/ZAP; traffic shaping stubs; target scopes file.
- Deliverables: safe lab scan demo + report markdown with findings/mitigations.

### M6 — Self-Modification Pipeline (Week 6)
- dev → sandbox → adversarial → optional human → staging → prod pipeline enforced.
- Weekly self-review report generation.
- Deliverables: one successful self-mod improvement merged via PR.

> Schedule is indicative; Friday may reorder based on dependencies. Each milestone ends with a **version tag** and CHANGELOG update.

---

## 4) Work Breakdown (Epics → Stories)

- **EP1 Core/Kernel**
  - Task routing, policy checks, logging, config profiles, plugin loader.
- **EP2 OS Automation**
  - Files, processes, windows, clipboard, screenshots; guard rails + tests.
- **EP3 UI/Frontend**
  - Approvals dashboard, logs/metrics, autonomy toggles, PTT indicator.
- **EP4 Coding/DevOps**
  - Claude Code wiring, repo map, test integration, PR prep templates.
- **EP5 Web Automation**
  - Playwright flows, scraping adapters, export formats (CSV/Parquet).
- **EP6 Social Agent**
  - Draft generator, content calendar, asset builder; human approval gate.
- **EP7 Ops Module**
  - Sandbox, scanners, traffic shaping config; reports; strict scopes.
- **EP8 Memory & Retrieval**
  - Chroma embeddings, SQLite state, cloud memory (Supabase/Softr/Memori).
- **EP9 Self-Modification**
  - Pipeline enforcement, adversarial tests, staging deploy scripts.
- **EP10 Observability**
  - JSONL logs, metrics endpoint, dashboards (optional).

---

## 5) Definition of Done (per feature)

- Acceptance tests pass locally and in staging.
- Logs reflect each step with timestamps and redacted secrets.
- CHANGELOG updated under **Unreleased** with succinct bullets.
- Documentation updated in `/docs/` (requirements/capabilities/architecture/model/this plan).

---

## 6) CI/CD Pipeline (Sketch)

- **On PR:** lint + unit tests + build docker images + staging E2E; post results.
- **Artifacts:** test reports, coverage, container images, exported assets.
- **Manual Gates:** human approval required to merge into `main`.

---

## 7) Branching & Versioning

- Branch naming: `feature/<slug>`; `fix/<slug>`; `ops/<slug>`.
- Conventional commits recommended (feat/fix/docs/refactor/test/chore).
- Semantic versioning; tag each milestone release (e.g., v0.1.0 … v0.6.0).

---

## 8) Risk Register (trimmed)

- **R1 Model regressions:** mitigated by staging tests + rollback.
- **R2 Resource contention:** background throttling when user active.
- **R3 Sensitive actions:** deny-by-default policies; explicit gates.
- **R4 Tool drift:** weekly self-review proposes dependency upgrades.
- **R5 Social misposts:** mandatory human approval before publish.

---

## 9) Acceptance Criteria (Project)

- Runs in Dev (WSL), Staging (Docker), and Prod (Windows/Linux).
- UI + CLI both functional; autonomy toggles respected.
- PR-only workflow; social posts require approval; Ops respects scopes.
- Self-mod pipeline blocks unsafe changes from reaching prod.
- Weekly self-review report present with actionable proposals.

---

## 10) Kickoff Checklist

- [ ] Repo baseline committed; `docs/` updated.
- [ ] Local Ollama running; Claude Code authenticated.
- [ ] `.env` not used for secrets; volatile store verified.
- [ ] `config/dev|staging|prod.yaml` created.
- [ ] CI stub active; staging docker-compose up.
- [ ] CHANGELOG started; version v0.1.0 tagged after M1.
