.PHONY: test coverage lint security docker-build docker-run install clean help

PYTHON := python3
PIP := $(PYTHON) -m pip
PACKAGE := ccc_os
TEST_DIR := tests

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package in editable mode with dev dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev]
	$(PIP) install pre-commit
	pre-commit install

test: ## Run the test suite
	$(PYTHON) -m pytest tests/ ccc_os/tests/ -x -v $(TEST_DIR)

coverage: ## Run tests with coverage report (fail if < 75%)
	$(PYTHON) -m pytest tests/ ccc_os/tests/ -x -v --cov=$(PACKAGE) --cov-report=term-missing --cov-report=html --cov-fail-under=75 $(TEST_DIR)

lint: ## Run ruff linting and mypy type checking
	ruff check .
	mypy $(PACKAGE)/ || true

security: ## Run bandit and pip-audit locally
	bandit -r $(PACKAGE)/ -ll
	pip-audit --desc

docker-build: ## Build Docker image
	docker build -t ccc-os:latest .

docker-run: ## Run with docker-compose
	docker compose up --build -d

clean: ## Remove build artifacts, caches, and temp files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
