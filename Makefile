.PHONY: install test test-unit test-integration test-mcp lint format type-check ci-local docker-build docker-test all clean

# Install all dependencies
install:
	pip install --upgrade pip
	pip install -e ".[dev]"

# Run all tests
test:
	python scripts/run_tests.py --coverage -v

# Run specific test types
test-unit:
	python scripts/run_tests.py --type unit -v

test-integration:
	python scripts/run_tests.py --type integration -v

test-mcp:
	python scripts/run_tests.py --type mcp -v

test-main:
	python scripts/run_tests.py --type main -v

# Quick test without coverage
test-fast:
	python scripts/run_tests.py -v

# Lint and test together (uses your script's --lint flag)
test-all:
	python scripts/run_tests.py --coverage -v --lint

# Lint code
lint:
	ruff check .

# Format code
format:
	ruff format .

# Auto-fix linting issues
lint-fix:
	ruff check . --fix
	ruff format .

# Type checking
type-check:
	mypy src/

# Run all CI checks (what GitHub Actions runs)
ci-local: lint-fix type-check
	python scripts/run_tests.py --coverage -v
	@echo "✅ All CI checks passed!"

# Docker build
docker-build:
	docker build -f docker/Dockerfile -t the_pere_spicace:local .

# Test Docker image
docker-test: docker-build
	docker run --rm the_pere_spicace:local python -c "print('✅ Docker image works!')"

# Run everything
all: install ci-local docker-test

# Clean up
clean:
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +