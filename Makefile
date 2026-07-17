.PHONY: help install install-dev test lint format typecheck clean build run


PYTHON ?= python3
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


install:
	$(PIP) install .


install-dev:
	$(PIP) install -e ".[dev]"


run:
	$(PYTHON) -m mydba_tui


test:
	pytest


lint:
	ruff check .


format:
	ruff format .
	ruff check --fix .


typecheck:
	mypy src


build:
	$(PYTHON) -m build


clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete