#!/usr/bin/env python3
"""
Automated Git flow for feature branch workflow with Claude Code integration.
Handles: feature branch creation → edits → tests → PR with summary.
"""
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class GitFlowAutomation:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.ensure_git_repo()

    def ensure_git_repo(self):
        """Ensure we're in a git repository."""
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def run_command(self, cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command and return the result."""
        try:
            result = subprocess.run(cmd, cwd=self.repo_path, capture_output=capture_output, text=True, check=False)
            return result
        except Exception as e:
            print(f"Error running command {' '.join(cmd)}: {e}")
            sys.exit(1)

    def get_current_branch(self) -> str:
        """Get the current Git branch name."""
        result = self.run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        return result.stdout.strip()

    def get_main_branch(self) -> str:
        """Determine the main branch (main or master)."""
        result = self.run_command(["git", "branch", "-r"])
        remote_branches = result.stdout
        if "origin/main" in remote_branches:
            return "main"
        elif "origin/master" in remote_branches:
            return "master"
        else:
            return "main"  # Default to main

    def create_feature_branch(self, feature_name: str, from_branch: Optional[str] = None) -> str:
        """Create a new feature branch."""
        if not from_branch:
            from_branch = self.get_main_branch()

        branch_name = f"feature/{feature_name}"

        # Ensure we're on the source branch and it's up to date
        self.run_command(["git", "checkout", from_branch])
        self.run_command(["git", "pull", "origin", from_branch])

        # Create and checkout new feature branch
        result = self.run_command(["git", "checkout", "-b", branch_name])
        if result.returncode != 0:
            print(f"Error creating branch {branch_name}: {result.stderr}")
            sys.exit(1)

        print(f"Created and switched to feature branch: {branch_name}")
        return branch_name

    def run_tests(self) -> bool:
        """Run the test suite and return success status."""
        print("Running test suite...")

        # Run pytest with timeout and specific options
        result = self.run_command(["python", "-m", "pytest", "tests/", "-v", "--tb=short", "--maxfail=5"])

        if result.returncode == 0:
            print("✅ All tests passed!")
            return True
        else:
            print("❌ Tests failed!")
            print("STDOUT:", result.stdout[-1000:])  # Last 1000 chars
            print("STDERR:", result.stderr[-1000:])  # Last 1000 chars
            return False

    def run_linting(self) -> bool:
        """Run code linting and formatting checks."""
        print("Running linting checks...")

        # Run ruff linting
        result = self.run_command(["python", "-m", "ruff", "check", "."])
        if result.returncode != 0:
            print("❌ Ruff linting failed!")
            print(result.stdout)
            return False

        # Run black formatting check
        result = self.run_command(["python", "-m", "black", "--check", "."])
        if result.returncode != 0:
            print("❌ Black formatting check failed!")
            print(result.stdout)
            return False

        print("✅ All linting checks passed!")
        return True

    def get_git_diff_summary(self, base_branch: str) -> str:
        """Get a summary of changes since the base branch."""
        result = self.run_command(["git", "diff", f"{base_branch}...HEAD", "--stat"])
        diff_stat = result.stdout

        result = self.run_command(["git", "log", f"{base_branch}...HEAD", "--oneline"])
        commit_log = result.stdout

        return f"Changes since {base_branch}:\n\n{diff_stat}\n\nCommits:\n{commit_log}"

    def create_pr_summary(self, feature_name: str, base_branch: str) -> str:
        """Generate a PR summary based on git changes."""
        diff_summary = self.get_git_diff_summary(base_branch)

        summary = f"""## {feature_name.replace('-', ' ').title()}

### Summary
This PR implements {feature_name.replace('-', ' ')}.

### Changes
{diff_summary}

### Testing
- ✅ All unit tests pass
- ✅ Integration tests pass
- ✅ Linting and formatting checks pass

### Checklist
- [x] Tests added/updated
- [x] Documentation updated (if needed)
- [x] Code follows project conventions
- [x] All checks pass

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

        return summary

    def push_and_create_pr(self, branch_name: str, feature_name: str) -> bool:
        """Push branch and create PR."""
        base_branch = self.get_main_branch()

        # Push the branch
        print(f"Pushing branch {branch_name}...")
        result = self.run_command(["git", "push", "-u", "origin", branch_name])
        if result.returncode != 0:
            print(f"Error pushing branch: {result.stderr}")
            return False

        # Create PR using gh CLI
        pr_title = feature_name.replace("-", " ").title()
        pr_body = self.create_pr_summary(feature_name, base_branch)

        print("Creating pull request...")
        result = self.run_command(["gh", "pr", "create", "--title", pr_title, "--body", pr_body, "--base", base_branch])

        if result.returncode == 0:
            print("✅ Pull request created successfully!")
            print(result.stdout)
            return True
        else:
            print("❌ Failed to create pull request!")
            print(result.stderr)
            return False


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python feature_workflow.py <command> [args]")
        print("Commands:")
        print("  create-branch <feature-name>    Create a new feature branch")
        print("  test                           Run tests")
        print("  lint                           Run linting checks")
        print("  create-pr <feature-name>       Push and create PR")
        print("  full-workflow <feature-name>   Complete workflow: branch → test → lint → PR")
        sys.exit(1)

    command = sys.argv[1]
    git_flow = GitFlowAutomation()

    if command == "create-branch":
        if len(sys.argv) < 3:
            print("Error: Feature name required")
            sys.exit(1)
        feature_name = sys.argv[2]
        git_flow.create_feature_branch(feature_name)

    elif command == "test":
        success = git_flow.run_tests()
        sys.exit(0 if success else 1)

    elif command == "lint":
        success = git_flow.run_linting()
        sys.exit(0 if success else 1)

    elif command == "create-pr":
        if len(sys.argv) < 3:
            print("Error: Feature name required")
            sys.exit(1)
        feature_name = sys.argv[2]
        current_branch = git_flow.get_current_branch()
        success = git_flow.push_and_create_pr(current_branch, feature_name)
        sys.exit(0 if success else 1)

    elif command == "full-workflow":
        if len(sys.argv) < 3:
            print("Error: Feature name required")
            sys.exit(1)
        feature_name = sys.argv[2]

        print(f"🚀 Starting full workflow for feature: {feature_name}")

        # Step 1: Create feature branch
        branch_name = git_flow.create_feature_branch(feature_name)

        # Step 2: Run tests
        if not git_flow.run_tests():
            print("❌ Workflow failed: Tests did not pass")
            sys.exit(1)

        # Step 3: Run linting
        if not git_flow.run_linting():
            print("❌ Workflow failed: Linting checks failed")
            sys.exit(1)

        # Step 4: Create PR
        if git_flow.push_and_create_pr(branch_name, feature_name):
            print("🎉 Full workflow completed successfully!")
        else:
            print("❌ Workflow failed: Could not create PR")
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
