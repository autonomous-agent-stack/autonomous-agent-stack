SHELL := /bin/bash

PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
HOST ?= 127.0.0.1
PORT ?= 8001

.PHONY: help setup doctor start test-quick clean

help:
	@echo "Autonomous Agent Stack - common commands"
	@echo ""
	@echo "  make setup       Create .venv and install dependencies"
	@echo "  make doctor      Run environment checks"
	@echo "  make start       Run doctor then start local API"
	@echo "  make test-quick  Run quick smoke tests"
	@echo "  make clean       Remove Python cache folders"
	@echo ""
	@echo "Optional vars: HOST=127.0.0.1 PORT=8001"

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	@if [[ ! -f .env && -f .env.template ]]; then \
		cp .env.template .env; \
		echo "Created .env from .env.template"; \
	fi

doctor:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	$(VENV_PYTHON) scripts/doctor.py --port $(PORT)

start:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PORT=$(PORT) HOST=$(HOST) scripts/dev-start.sh

test-quick:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	@if [[ -f tests/test_workflow_engine.py ]]; then \
		PYTHONPATH=src $(VENV_PYTHON) -m pytest tests/test_workflow_engine.py -q; \
	else \
		echo "Skipping tests/test_workflow_engine.py (file not found)."; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) tests/test_workflow_quick.py
	PYTHONPATH=src $(VENV_PYTHON) scripts/test_registry_simple.py

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
