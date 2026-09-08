.PHONY: help install install-dev test lint format typecheck clean build run all


# Prefer the project virtualenv interpreter if it exists, so targets work
# without needing the venv to be activated. Override with `make PYTHON=...`.
PYTHON ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)
PIP ?= $(PYTHON) -m pip


help:
	@echo "mydba-tui development commands"
	@echo ""
	@echo "  install       Install project dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo "  run           Run mydba"
	@echo "  test          Run tests"
	@echo "  lint          Run lint checks"
	@echo "  format        Format source code"
	@echo "  typecheck     Run mypy checks"
	@echo "  build         Build package"
	@echo "  clean         Remove generated files"
	@echo "  all           Format, lint, typecheck, test, then run the app"


install:
	$(PIP) install .


install-dev:
	$(PIP) install -e ".[dev]"


all: format lint typecheck test run


run:
	$(PYTHON) -m mydba_tui


test:
	$(PYTHON) -m pytest


lint:
	$(PYTHON) -m ruff check .


format:
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .


typecheck:
	$(PYTHON) -m mypy src


build:
	$(PYTHON) -m build


clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete