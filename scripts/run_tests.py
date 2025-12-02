# scripts/run_tests.py
#!/usr/bin/env python3
"""
Test runner script for the YouTube Learning Pipeline.
"""

import sys
import argparse
import subprocess


def run_tests(test_type="all", coverage=False, verbose=False):
    """Run tests with specified options."""

    # Base pytest command
    cmd = ["pytest"]

    # Add coverage if requested
    if coverage:
        cmd.extend(
            ["--cov=src", "--cov-report=term-missing", "--cov-report=html"]
        )

    # Add verbose flag
    if verbose:
        cmd.append("-v")

    # Determine which tests to run
    if test_type == "unit":
        cmd.append("tests/unit/")
    elif test_type == "integration":
        cmd.append("tests/integration/")
    elif test_type == "mcp":
        cmd.append("tests/unit/mcp/")
    elif test_type == "main":
        cmd.append("tests/unit/test_main.py")
    else:
        cmd.append("tests/")

    # Add asyncio mode for async tests
    cmd.append("--asyncio-mode=auto")

    # Run the tests
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    return result.returncode


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Run tests for YouTube Learning Pipeline"
    )
    parser.add_argument(
        "--type",
        choices=["all", "unit", "integration", "mcp", "main"],
        default="all",
        help="Type of tests to run",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run linting checks before tests",
    )

    args = parser.parse_args()

    # Run linting if requested
    if args.lint:
        print("Running linting checks...")
        lint_result = subprocess.run(["ruff", "check", "."])
        if lint_result.returncode != 0:
            print("Linting failed. Fix issues before running tests.")
            return lint_result.returncode

        print("Running formatting check...")
        format_result = subprocess.run(["ruff", "format", "--check", "."])
        if format_result.returncode != 0:
            print("Formatting issues found.")
            return format_result.returncode

    # Run tests
    return run_tests(args.type, args.coverage, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
