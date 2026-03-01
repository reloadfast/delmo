.PHONY: check lint type-check test install-hooks

## Run all checks that CI runs (lint + type-check + tests).
check: lint type-check test

## Lint only (fast — good for quick feedback).
lint:
	ruff check backend/
	cd frontend && npm run lint
	cd frontend && npm run format:check

## Type-check only.
type-check:
	mypy backend/app/
	cd frontend && npm run type-check

## Full test suite.
test:
	pytest --cov=backend/app --cov-fail-under=80
	cd frontend && npm run test:coverage

## Configure git to use the tracked hooks in .githooks/.
install-hooks:
	git config core.hooksPath .githooks
	@echo "Hooks installed — pre-push will run 'make lint type-check' before every push."
