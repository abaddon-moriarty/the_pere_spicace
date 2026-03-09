#!/usr/bin/env python3
# scripts/run_tests.py
"""
Test runner script for the YouTube Learning Pipeline.
"""

import sys
import shutil
import logging
import argparse
import subprocess

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def run_tests(
    test_type: str = "all",
    *,
    coverage: bool = False,
    verbose: bool = False,
) -> int:
    """Run tests with specified options."""

    # Base pytest command
    cmd = ["pytest"]

    # Add coverage if requested
    if coverage:
        cmd.extend(
            ["--cov=src", "--cov-report=term-missing", "--cov-report=html"],
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
    logger.info(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)  # noqa: S603

    return result.returncode


def run_type_check():
    """Run mypy type checking."""
    logger.info("\n🔎 Running type checks...")
    result = subprocess.run(["mypy", "src/"])  # noqa: S607
    return result.returncode


def main() -> int:
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Run tests for YouTube Learning Pipeline",
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
    parser.add_argument(
        "--type-check",
        action="store_true",
        help="Run type checking before tests",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Run all checks (lint, type-check, tests) - simulates CI",
    )

    args = parser.parse_args()

    # CI mode runs everything
    if args.ci:
        args.lint = True
        args.type_check = True
        args.coverage = True
        args.verbose = True

    # Run linting if requested
    if args.lint:
        logger.info("Running linting checks...")
        _ruff = shutil.which("ruff") or "ruff"
        lint_result = subprocess.run([_ruff, "check", "."])  # noqa: S603

        if lint_result.returncode != 0:
            logger.error("Linting failed. Fix issues before running tests.")
            return lint_result.returncode

        logger.info("Running formatting check...")
        format_result = subprocess.run([_ruff, "format", "--check", "."])  # noqa: S603
        if format_result.returncode != 0:
            logger.error("Formatting issues found.")
            return format_result.returncode

        logger.info("Linting passed!\n")

    # Run type checking if requested
    if args.type_check:
        type_result = run_type_check()
        if type_result != 0:
            logger.error("Type checking failed.")
            return type_result
        logger.info("Type checking passed!\n")

    # Run tests
    logger.info("Running tests...")
    test_result = run_tests(
        args.type,
        coverage=args.coverage,
        verbose=args.verbose,
    )

    if test_result == 0:
        logger.info("\nAll checks passed!")
    else:
        logger.error("\nTests failed!")

    return test_result


if __name__ == "__main__":
    sys.exit(main())
