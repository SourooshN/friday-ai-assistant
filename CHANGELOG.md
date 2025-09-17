# Changelog
All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- N/A

### Changed
- N/A

### Fixed
- N/A

### Removed
- N/A

### Reverted
- N/A

## [0.2.0] - 2025-09-17
### Added
- ✅ **Milestone 3 Complete: Coding/DevOps Loop**
- Claude Code DevOps integration for automated workflow management
- Automated Git flow scripts (`scripts/devops/feature_workflow.py`)
- Feature branch creation → edits → tests → PR automation
- PR validation system with comprehensive checks (tests, linting, security, coverage)
- Claude DevOps CLI wrapper (`./claude-devops`) for common operations
- GitHub CI/CD pipeline with multi-Python version testing
- Security scanning integration (bandit, safety)
- Code quality checks (ruff, black, mypy)
- Automatic PR creation with detailed summaries

### Enhanced
- Updated `.github/workflows/ci.yml` with comprehensive CI/CD pipeline
- Test runner integration with pytest and timeout handling
- Linting and formatting automation
- Code coverage reporting and validation

### Technical Implementation
- DevOps automation scripts in `scripts/devops/`
- GitHub Actions integration for PR validation
- CLI commands: `test`, `lint`, `format`, `new`, `pr`, `workflow`, `status`
- Automated PR summaries with git diff analysis
- Security scanning and vulnerability detection
- Test coverage requirements (70% minimum)

### Usage Examples
```bash
./claude-devops new user-authentication    # Create feature branch
./claude-devops test                       # Run test suite
./claude-devops workflow api-improvements  # Full automation
```

## [0.1.0] - 2025-09-16
### Added
- ✅ **Milestone 1 Complete: Foundations**
- Repo hygiene: Clean directory layout, updated configs, modern architecture
- Base configs: `config/dev.yaml`, `config/staging.yaml`, `config/prod.yaml` with environment-specific settings
- Logging scaffold: Structured JSON logging with audit trails, sensitive data redaction, configurable outputs
- Core kernel: Main system controller with lifecycle management, component orchestration
- Orchestrator skeleton: Task management and coordination framework (basic implementation)
- Plugin host: Dynamic plugin loading system with `os_hello` example plugin
- Memory adapters: SQLite for relational data, ChromaDB integration stub (memory management)
- Volatile secret store: In-memory encrypted secret storage (never persisted to disk)
- Runnable CLI: Command-line interface with status, task execution, and interactive modes
- Logs structure: `./data/logs/` with rotation, compression, and retention policies
- Unit test skeleton: pytest-based testing framework for core components
- Complete project restructure: Aligned with architecture specifications

### Changed
- Migrated from old agent-based structure to modern kernel + plugin architecture
- Updated `requirements.txt` with properly organized dependencies
- Switched from `.env` files to YAML configuration system

### Removed
- Legacy agent files and outdated structure
- Hardcoded configuration and insecure secret storage
- Obsolete scripts and duplicate dependencies

### Technical Notes
- Environment: Tested on WSL + VS Code (development target achieved)
- Architecture: Monolithic core with plugin system as specified
- Security: Volatile-only secret storage, policy engine foundation
- Logging: Full audit trail with JSONL format for automation
- Plugin System: Working with `os_hello` example, ready for expansion

## [0.1.0] - YYYY-MM-DD
### Added
- Initial snapshot before Claude auto-mode (baseline import).
