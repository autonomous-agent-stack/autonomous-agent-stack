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
OH_TASK ?= Please scan /opt/workspace/src/autoresearch/core, identify TODOs, implement production-grade fixes, and run tests after each fix.
OH_DRY_RUN ?= 0
OH_CHAIN_DRY_RUN ?= 0
OH_VALIDATE_CMD ?= python3 scripts/check_prompt_hygiene.py --root src --output-dir logs/audit/prompt_hygiene --min-repeat 3
OH_BACKEND ?= mock
OH_FAILURE_STRATEGY ?= human_in_loop
OH_MAX_RETRIES ?= 1
AEP_AGENT ?= openhands
AEP_TASK ?= Create src/demo_math.py with add(a,b).
AEP_RUN_ID ?=
AEP_RETRY ?= 0
AEP_FALLBACK_AGENT ?= mock
PROMOTE_RUN_ID ?=
PROMOTE_BASE_REF ?= main
PROMOTE_BRANCH_PREFIX ?= codex/auto-upgrade
PROMOTE_PUSH ?= 0
PROMOTE_OPEN_DRAFT_PR ?= 0

.PHONY: help setup doctor doctor-linux start test-quick clean
.PHONY: ai-lab ai-lab-setup ai-lab-check ai-lab-up ai-lab-down ai-lab-status ai-lab-shell ai-lab-run masfactory-flight hygiene-check openhands openhands-dry-run openhands-controlled openhands-controlled-dry-run openhands-demo agent-run promote-run
.PHONY: review-gates-local linux-housekeeper-start linux-housekeeper-stop linux-housekeeper-status linux-housekeeper-run-once linux-housekeeper-repair linux-housekeeper-enqueue-test

help:
	@echo "Autonomous Agent Stack - common commands"
	@echo ""
	@echo "  make setup       Create .venv and install dependencies"
	@echo "  make doctor      Run environment checks"
	@echo "  make doctor-linux Run Linux remote-worker checks"
	@echo "  make start       Run doctor then start local API"
	@echo "  make ai-lab      One-key launch AI lab shell"
	@echo "  make ai-lab-setup Initialize AI lab user and quota volume"
	@echo "  make ai-lab-check Run guardrail checks only"
	@echo "  make ai-lab-up   Start AI lab detached"
	@echo "  make ai-lab-down Stop AI lab"
	@echo "  make ai-lab-status Show AI lab status"
	@echo "  make ai-lab-run ARGS='python -V' Run a one-shot command"
	@echo "  make masfactory-flight GOAL='...' WATCH=1 Run MASFactory first flight demo"
	@echo "  make openhands OH_TASK='...' Launch OpenHands CLI with strict guardrails"
	@echo "  make openhands-dry-run Preview the OpenHands docker command"
	@echo "  make openhands-controlled OH_TASK='...' Run controlled backend chain (isolated workspace + validation + patch)"
	@echo "  make openhands-controlled-dry-run Preview controlled backend chain with dry-run OpenHands"
	@echo "  make openhands-demo OH_BACKEND=mock Run minimal closed-loop demo (contract + failure policy)"
	@echo "  make agent-run AEP_AGENT=openhands AEP_TASK='...' Run AEP v0 runner entrypoint"
	@echo "  make promote-run PROMOTE_RUN_ID='...' Turn a ready AEP run into branch/commit/draft PR payload"
	@echo "  make linux-housekeeper-start Start resident Linux execution supervisor"
	@echo "  make linux-housekeeper-stop Stop resident Linux execution supervisor"
	@echo "  make linux-housekeeper-status Show resident Linux execution supervisor state"
	@echo "  make linux-housekeeper-run-once Process one queued Linux supervisor task"
	@echo "  make linux-housekeeper-repair Mark orphaned running Linux tasks as infra_error"
	@echo "  make linux-housekeeper-enqueue-test Enqueue one Linux supervisor smoke task"
	@echo "  make hygiene-check FAIL_ON_FINDINGS=1 Run prompt hygiene audit for src/"
	@echo "  make review-gates-local Run mypy/bandit/semgrep on reviewer core modules"
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

doctor-linux:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	$(VENV_PYTHON) scripts/doctor.py --profile linux-remote --port $(PORT)

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
		if [[ "$(FAIL_ON_FINDINGS)" == "1" ]]; then STRICT_FLAG="--fail-on-findings"; fi; \
		$(VENV_PYTHON) scripts/check_prompt_hygiene.py --root "$(HYGIENE_ROOT)" --output-dir "$(HYGIENE_OUTPUT_DIR)" --min-repeat "$(HYGIENE_MIN_REPEAT)" $$STRICT_FLAG; \
	else \
		STRICT_FLAG=""; \
		if [[ "$(FAIL_ON_FINDINGS)" == "1" ]]; then STRICT_FLAG="--fail-on-findings"; fi; \
		$(PYTHON) scripts/check_prompt_hygiene.py --root "$(HYGIENE_ROOT)" --output-dir "$(HYGIENE_OUTPUT_DIR)" --min-repeat "$(HYGIENE_MIN_REPEAT)" $$STRICT_FLAG; \
	fi

review-gates-local:
	@set -euo pipefail; \
	MYPY_BIN="mypy"; \
	BANDIT_BIN="bandit"; \
	SEMGREP_BIN="semgrep"; \
	if [[ -x "$(VENV)/bin/mypy" ]]; then MYPY_BIN="$(VENV)/bin/mypy"; fi; \
	if [[ -x "$(VENV)/bin/bandit" ]]; then BANDIT_BIN="$(VENV)/bin/bandit"; fi; \
	if [[ -x "$(VENV)/bin/semgrep" ]]; then SEMGREP_BIN="$(VENV)/bin/semgrep"; fi; \
	$$MYPY_BIN --config-file mypy.ini src/gatekeeper/static_analyzer.py src/gatekeeper/business_enforcer.py src/gatekeeper/llm_reviewer.py src/gatekeeper/board_summarizer.py; \
	$$BANDIT_BIN -q src/gatekeeper/static_analyzer.py src/gatekeeper/business_enforcer.py src/gatekeeper/llm_reviewer.py src/gatekeeper/board_summarizer.py; \
	$$SEMGREP_BIN --error --config=p/python src/gatekeeper/static_analyzer.py src/gatekeeper/business_enforcer.py src/gatekeeper/llm_reviewer.py src/gatekeeper/board_summarizer.py

openhands:
	OPENHANDS_TASK='$(OH_TASK)' OPENHANDS_DRY_RUN='$(OH_DRY_RUN)' bash ./scripts/openhands_start.sh

openhands-dry-run:
	OPENHANDS_TASK='$(OH_TASK)' OPENHANDS_DRY_RUN=1 bash ./scripts/openhands_start.sh

openhands-controlled:
	OPENHANDS_TASK='$(OH_TASK)' OPENHANDS_CHAIN_DRY_RUN='$(OH_CHAIN_DRY_RUN)' OPENHANDS_VALIDATE_CMD='$(OH_VALIDATE_CMD)' bash ./scripts/openhands_controlled_backend.sh

openhands-controlled-dry-run:
	OPENHANDS_TASK='$(OH_TASK)' OPENHANDS_CHAIN_DRY_RUN=1 OPENHANDS_VALIDATE_CMD='$(OH_VALIDATE_CMD)' bash ./scripts/openhands_controlled_backend.sh

openhands-demo:
	@if [[ -x "$(VENV_PYTHON)" ]]; then \
		PYTHONPATH=src $(VENV_PYTHON) examples/openhands_minimal_closed_loop.py --backend "$(OH_BACKEND)" --failure-strategy "$(OH_FAILURE_STRATEGY)" --max-retries "$(OH_MAX_RETRIES)" --prompt "$(OH_TASK)"; \
	else \
		PYTHONPATH=src $(PYTHON) examples/openhands_minimal_closed_loop.py --backend "$(OH_BACKEND)" --failure-strategy "$(OH_FAILURE_STRATEGY)" --max-retries "$(OH_MAX_RETRIES)" --prompt "$(OH_TASK)"; \
	fi

agent-run:
	@CMD_ARGS="--agent \"$(AEP_AGENT)\" --task \"$(AEP_TASK)\" --retry \"$(AEP_RETRY)\""; \
	if [[ -n "$(strip $(AEP_RUN_ID))" ]]; then CMD_ARGS="$$CMD_ARGS --run-id \"$(AEP_RUN_ID)\""; fi; \
	if [[ -n "$(strip $(AEP_FALLBACK_AGENT))" ]]; then CMD_ARGS="$$CMD_ARGS --fallback-agent \"$(AEP_FALLBACK_AGENT)\""; fi; \
	if [[ -x "$(VENV_PYTHON)" ]]; then \
		eval "PYTHONPATH=src $(VENV_PYTHON) scripts/agent_run.py $$CMD_ARGS"; \
	else \
		eval "PYTHONPATH=src $(PYTHON) scripts/agent_run.py $$CMD_ARGS"; \
	fi

promote-run:
	@if [[ -z "$(strip $(PROMOTE_RUN_ID))" ]]; then \
		echo "Usage: make promote-run PROMOTE_RUN_ID='<run-id>'"; \
		exit 1; \
	fi

linux-housekeeper-start:
	bash ./scripts/linux_housekeeper.sh start

linux-housekeeper-stop:
	bash ./scripts/linux_housekeeper.sh stop

linux-housekeeper-status:
	bash ./scripts/linux_housekeeper.sh status

linux-housekeeper-run-once:
	bash ./scripts/linux_housekeeper.sh run-once

linux-housekeeper-repair:
	bash ./scripts/linux_housekeeper.sh repair

linux-housekeeper-enqueue-test:
	bash ./scripts/linux_housekeeper.sh enqueue-test
	@CMD_ARGS="--run-id \"$(PROMOTE_RUN_ID)\" --base-ref \"$(PROMOTE_BASE_REF)\" --branch-prefix \"$(PROMOTE_BRANCH_PREFIX)\""; \
	if [[ "$(PROMOTE_PUSH)" == "1" ]]; then CMD_ARGS="$$CMD_ARGS --push"; fi; \
	if [[ "$(PROMOTE_OPEN_DRAFT_PR)" == "1" ]]; then CMD_ARGS="$$CMD_ARGS --open-draft-pr"; fi; \
	if [[ -x "$(VENV_PYTHON)" ]]; then \
		eval "PYTHONPATH=src $(VENV_PYTHON) scripts/promote_run.py $$CMD_ARGS"; \
	else \
		eval "PYTHONPATH=src $(PYTHON) scripts/promote_run.py $$CMD_ARGS"; \
	fi
