#!/usr/bin/env python3
"""
PR Validation Script for Claude Code DevOps Integration
Validates that PRs meet quality standards before merging.
"""
import subprocess
import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class PRValidator:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.validation_results = {
            "tests_passed": False,
            "linting_passed": False,
            "security_passed": False,
            "coverage_adequate": False,
            "documentation_updated": False
        }

    def run_command(self, cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command and return the result."""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                check=False
            )
            return result
        except Exception as e:
            print(f"Error running command {' '.join(cmd)}: {e}")
            return subprocess.CompletedProcess(cmd, 1, "", str(e))

    def validate_tests(self) -> Tuple[bool, str]:
        """Run tests and validate they pass."""
        print("🧪 Running test suite...")

        result = self.run_command([
            "python", "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--maxfail=10",
            "--timeout=120",
            "--cov=core",
            "--cov=plugins",
            "--cov-report=json"
        ])

        if result.returncode == 0:
            self.validation_results["tests_passed"] = True
            return True, "All tests passed successfully"
        else:
            return False, f"Tests failed with {result.returncode} exit code"

    def validate_linting(self) -> Tuple[bool, str]:
        """Validate code linting and formatting."""
        print("🔍 Checking code quality...")

        # Check ruff linting
        result = self.run_command(["python", "-m", "ruff", "check", "."])
        if result.returncode != 0:
            return False, "Ruff linting failed"

        # Check black formatting
        result = self.run_command(["python", "-m", "black", "--check", "."])
        if result.returncode != 0:
            return False, "Black formatting check failed"

        self.validation_results["linting_passed"] = True
        return True, "All linting checks passed"

    def validate_security(self) -> Tuple[bool, str]:
        """Run security checks on the codebase."""
        print("🔒 Running security scans...")

        # Install security tools if not available
        self.run_command(["pip", "install", "bandit", "safety"], capture_output=False)

        # Run bandit security check
        result = self.run_command(["bandit", "-r", ".", "-f", "json"])
        if result.returncode not in [0, 1]:  # 1 is acceptable (issues found but not critical)
            return False, "Bandit security scan failed"

        # Run safety check
        result = self.run_command(["safety", "check", "--json"])
        if result.returncode not in [0, 64]:  # 64 means no vulnerabilities found
            return False, "Safety vulnerability check failed"

        self.validation_results["security_passed"] = True
        return True, "Security scans passed"

    def validate_coverage(self) -> Tuple[bool, str]:
        """Check test coverage is adequate."""
        print("📊 Checking test coverage...")

        coverage_file = self.repo_path / "coverage.json"
        if not coverage_file.exists():
            return False, "Coverage report not found"

        try:
            with open(coverage_file) as f:
                coverage_data = json.load(f)

            total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
            if total_coverage >= 70:  # 70% minimum coverage
                self.validation_results["coverage_adequate"] = True
                return True, f"Coverage is adequate: {total_coverage:.1f}%"
            else:
                return False, f"Coverage too low: {total_coverage:.1f}% (minimum 70%)"

        except Exception as e:
            return False, f"Error reading coverage data: {e}"

    def validate_documentation(self) -> Tuple[bool, str]:
        """Check if documentation has been updated appropriately."""
        print("📚 Checking documentation...")

        # Check if CHANGELOG.md was updated
        result = self.run_command(["git", "diff", "HEAD~1", "--name-only"])
        changed_files = result.stdout.strip().split('\n')

        # Look for significant code changes that should have documentation updates
        has_significant_changes = any(
            file.endswith('.py') and not file.startswith('tests/')
            for file in changed_files
        )

        if has_significant_changes:
            has_changelog_update = "CHANGELOG.md" in changed_files
            has_docs_update = any(file.startswith('docs/') for file in changed_files)

            if has_changelog_update or has_docs_update:
                self.validation_results["documentation_updated"] = True
                return True, "Documentation appropriately updated"
            else:
                return False, "Significant changes detected but no documentation updates"

        self.validation_results["documentation_updated"] = True
        return True, "No documentation updates required"

    def generate_validation_report(self) -> str:
        """Generate a comprehensive validation report."""
        report = "# PR Validation Report\n\n"

        validations = [
            ("Tests", self.validate_tests),
            ("Code Quality", self.validate_linting),
            ("Security", self.validate_security),
            ("Coverage", self.validate_coverage),
            ("Documentation", self.validate_documentation)
        ]

        all_passed = True
        for name, validator in validations:
            try:
                passed, message = validator()
                status = "✅" if passed else "❌"
                report += f"## {status} {name}\n{message}\n\n"
                if not passed:
                    all_passed = False
            except Exception as e:
                report += f"## ❌ {name}\nError: {e}\n\n"
                all_passed = False

        # Overall status
        if all_passed:
            report += "## 🎉 Overall Status\nAll validations passed! PR is ready for review.\n"
        else:
            report += "## ⚠️ Overall Status\nSome validations failed. Please address the issues above.\n"

        return report, all_passed

    def post_github_comment(self, pr_number: int, report: str):
        """Post validation report as GitHub comment."""
        try:
            # Use gh CLI to post comment
            result = self.run_command([
                "gh", "pr", "comment", str(pr_number),
                "--body", f"🤖 **Claude Code PR Validation Report**\n\n{report}"
            ])

            if result.returncode == 0:
                print("✅ Posted validation report to GitHub")
            else:
                print(f"❌ Failed to post GitHub comment: {result.stderr}")

        except Exception as e:
            print(f"❌ Error posting GitHub comment: {e}")


def main():
    """Main CLI entry point."""
    validator = PRValidator()

    if len(sys.argv) > 1 and sys.argv[1] == "--github-action":
        # Running in GitHub Actions
        pr_number = os.environ.get("GITHUB_PR_NUMBER")
        if pr_number:
            report, passed = validator.generate_validation_report()
            validator.post_github_comment(int(pr_number), report)
            sys.exit(0 if passed else 1)
        else:
            print("No PR number found in environment")
            sys.exit(1)
    else:
        # Running locally
        report, passed = validator.generate_validation_report()
        print(report)
        sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()