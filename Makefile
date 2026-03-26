SHELL := /bin/bash

PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
HOST ?= 127.0.0.1
PORT ?= 8001
GOAL ?= 检查 M1 原生算力与工作区可写性
WATCH ?= 0
HYGIENE_ROOT ?= src
HYGIENE_OUTPUT_DIR ?= logs/audit/prompt_hygiene
HYGIENE_MIN_REPEAT ?= 3
FAIL_ON_FINDINGS ?= 0
HYGIENE_PROFILE ?= dev

.PHONY: help setup doctor start test-quick clean
.PHONY: ai-lab ai-lab-setup ai-lab-check ai-lab-up ai-lab-down ai-lab-status ai-lab-shell ai-lab-run masfactory-flight hygiene-check hygiene-check-dev hygiene-check-ci

help:
	@echo "Autonomous Agent Stack - common commands"
	@echo ""
	@echo "  make setup       Create .venv and install dependencies"
	@echo "  make doctor      Run environment checks"
	@echo "  make start       Run doctor then start local API"
	@echo "  make ai-lab      One-key launch AI lab shell"
	@echo "  make ai-lab-setup Initialize AI lab user and quota volume"
	@echo "  make ai-lab-check Run guardrail checks only"
	@echo "  make ai-lab-up   Start AI lab detached"
	@echo "  make ai-lab-down Stop AI lab"
	@echo "  make ai-lab-status Show AI lab status"
	@echo "  make ai-lab-run ARGS='python -V' Run a one-shot command on the host"
	@echo "  make masfactory-flight GOAL='...' WATCH=1 Run MASFactory first flight demo"
	@echo "  make hygiene-check HYGIENE_PROFILE=dev Run prompt hygiene audit for src/"
	@echo "  make hygiene-check-ci Strict prompt hygiene audit (fail on findings)"
	@echo "  make test-quick  Run quick smoke tests"
	@echo "  make clean       Remove Python cache folders"
	@echo ""
	@echo "Optional vars: HOST=127.0.0.1 PORT=8001"

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	@if [[ -f requirements.lock ]]; then \
		$(VENV_PIP) install -r requirements.lock; \
	else \
		$(VENV_PIP) install -r requirements.txt; \
	fi
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
	PORT=$(PORT) HOST=$(HOST) bash scripts/dev-start.sh

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

ai-lab-setup:
	@if [[ ! -f ai_lab.env ]]; then \
		cp ai_lab.env.example ai_lab.env; \
		echo "Created ai_lab.env from ai_lab.env.example"; \
	fi
	@if [[ ! -x ./scripts/setup_ai_lab.sh ]]; then \
		chmod +x ./scripts/setup_ai_lab.sh; \
	fi
	sudo bash ./scripts/setup_ai_lab.sh

ai-lab-check:
	bash ./scripts/check_ai_lab_guardrails.sh

ai-lab:
	bash ./scripts/launch_ai_lab.sh

ai-lab-up:
	bash ./scripts/launch_ai_lab.sh up

ai-lab-down:
	bash ./scripts/launch_ai_lab.sh down

ai-lab-status:
	bash ./scripts/launch_ai_lab.sh status

ai-lab-shell:
	bash ./scripts/launch_ai_lab.sh shell

ai-lab-run:
	@if [[ -z "$(strip $(ARGS))" ]]; then \
		echo "Usage: make ai-lab-run ARGS='python -V'"; \
		echo "Runs on the host and forwards the command into the ai-lab container."; \
		echo "Do not prefix ARGS with --; make already passes it for you."; \
		exit 1; \
	fi
	bash ./scripts/launch_ai_lab.sh run -- $(ARGS)

masfactory-flight:
	@if [[ -x "$(VENV_PYTHON)" ]]; then \
		MAS_FACTORY_GOAL="$(GOAL)" WATCH="$(WATCH)" $(VENV_PYTHON) examples/masfactory_first_flight.py; \
	else \
		MAS_FACTORY_GOAL="$(GOAL)" WATCH="$(WATCH)" $(PYTHON) examples/masfactory_first_flight.py; \
	fi

hygiene-check:
	@if [[ -x "$(VENV_PYTHON)" ]]; then \
		STRICT_FLAG=""; \
		OUTPUT_DIR="$(HYGIENE_OUTPUT_DIR)/$(HYGIENE_PROFILE)"; \
		MIN_REPEAT="$(HYGIENE_MIN_REPEAT)"; \
		if [[ "$(HYGIENE_PROFILE)" == "ci" ]]; then STRICT_FLAG="--fail-on-findings"; MIN_REPEAT=2; fi; \
		if [[ "$(FAIL_ON_FINDINGS)" == "1" ]]; then STRICT_FLAG="--fail-on-findings"; fi; \
		$(VENV_PYTHON) scripts/check_prompt_hygiene.py --root "$(HYGIENE_ROOT)" --output-dir "$$OUTPUT_DIR" --min-repeat "$$MIN_REPEAT" $$STRICT_FLAG; \
	else \
		STRICT_FLAG=""; \
		OUTPUT_DIR="$(HYGIENE_OUTPUT_DIR)/$(HYGIENE_PROFILE)"; \
		MIN_REPEAT="$(HYGIENE_MIN_REPEAT)"; \
		if [[ "$(HYGIENE_PROFILE)" == "ci" ]]; then STRICT_FLAG="--fail-on-findings"; MIN_REPEAT=2; fi; \
		if [[ "$(FAIL_ON_FINDINGS)" == "1" ]]; then STRICT_FLAG="--fail-on-findings"; fi; \
		$(PYTHON) scripts/check_prompt_hygiene.py --root "$(HYGIENE_ROOT)" --output-dir "$$OUTPUT_DIR" --min-repeat "$$MIN_REPEAT" $$STRICT_FLAG; \
	fi

hygiene-check-dev:
	@$(MAKE) hygiene-check HYGIENE_PROFILE=dev

hygiene-check-ci:
	@$(MAKE) hygiene-check HYGIENE_PROFILE=ci
