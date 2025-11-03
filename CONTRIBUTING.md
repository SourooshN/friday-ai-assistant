# Contributing to Friday

We welcome contributions! Please follow these rules to ensure consistency and safety.

---

## Branching Strategy

- `feature/<slug>` — new features
- `fix/<slug>` — bug fixes
- `ops/<slug>` — ops/cyber module changes
- `docs/<slug>` — documentation updates

---

## Commit Style

Use **Conventional Commits**:

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation only
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `test:` — adding or correcting tests
- `chore:` — misc changes (build, tooling)

Example:
```
feat: add OS automation plugin for file operations
```

---

## PR Workflow

1. Create feature branch.
2. Commit changes with linted, tested code.
3. Open a PR against `main`.
4. CI/CD runs: lint + unit tests + docker staging deploy.
5. Pull Requests are auto-reviewed by CodeRabbit; ensure pytest passes before pushing.
6. Human approval required before merge.

---

## Code Style

- Python: **PEP8** enforced via `ruff` or `flake8`.
- JavaScript: **ESLint + Prettier**.
- Tests: all new code must include tests.
- Secrets: never hardcode; only use volatile secret store.

---

## Docs

- Update `/docs/` when adding/updating functionality.
- Update `CHANGELOG.md` with every PR.

---

Thank you for contributing!
