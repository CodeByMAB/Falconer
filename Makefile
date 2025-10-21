.PHONY: help dev test lint format type-check clean install

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: format lint type-check test ## Run all development checks

install: ## Install the package in development mode
	pip install -e ".[dev]"

test: ## Run tests
	pytest

lint: ## Run linting
	flake8 src tests
	black --check src tests
	isort --check-only src tests

format: ## Format code
	black src tests
	isort src tests

type-check: ## Run type checking
	mypy src

clean: ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .tox/
	rm -rf .coverage*
	rm -rf htmlcov/

setup: ## Initial setup for development
	pip install -e ".[dev]"
	pre-commit install

regtest: ## Start regtest environment
	docker-compose -f ops/docker-compose.regtest.yml up -d

regtest-down: ## Stop regtest environment
	docker-compose -f ops/docker-compose.regtest.yml down
