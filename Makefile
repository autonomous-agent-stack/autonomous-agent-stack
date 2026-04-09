SHELL := /bin/bash

PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
REVIEW_VENV ?= .venv-review
REVIEW_VENV_PYTHON := $(REVIEW_VENV)/bin/python
REVIEW_VENV_PIP := $(REVIEW_VENV)/bin/pip
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

.PHONY: help setup doctor doctor-linux start test-quick smoke-local validate-req4 clean
.PHONY: ai-lab ai-lab-setup ai-lab-check ai-lab-up ai-lab-down ai-lab-status ai-lab-shell ai-lab-run masfactory-flight hygiene-check openhands openhands-dry-run openhands-controlled openhands-controlled-dry-run openhands-demo agent-run promote-run
.PHONY: review-setup review-gates-local assistant-doctor assistant-triage assistant-execute assistant-review-pr assistant-release-plan assistant-schedule
.PHONY: telegram-butler-start telegram-butler-status telegram-butler-stop

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
	@echo "  make assistant-doctor Validate GitHub assistant template setup"
	@echo "  make assistant-triage REPO='owner/repo' ISSUE=123 Triage a managed issue"
	@echo "  make assistant-execute REPO='owner/repo' ISSUE=123 Execute a managed issue"
	@echo "  make assistant-review-pr REPO='owner/repo' PR=123 Review a managed pull request"
	@echo "  make assistant-release-plan REPO='owner/repo' VERSION='v1.2.3' Build a release plan"
	@echo "  make assistant-schedule Run scheduled issue triage"
	@echo "  make telegram-butler-start Start API daemon + Telegram poller"
	@echo "  make telegram-butler-status Show API daemon + Telegram poller status"
	@echo "  make telegram-butler-stop Stop API daemon + Telegram poller"
	@echo "  make hygiene-check FAIL_ON_FINDINGS=1 Run prompt hygiene audit for src/"
	@echo "  make review-setup Create .venv-review with mypy/bandit/semgrep"
	@echo "  make review-gates-local Run mypy/bandit/semgrep on reviewer core modules"
	@echo "  make test-quick  Run quick smoke tests"
	@echo "  make smoke-local Run stable single-machine baseline smoke test"
	@echo "  make validate-req4 Validate requirement #4 scaffold readiness"
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

review-setup:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	$(VENV_PYTHON) -m venv $(REVIEW_VENV)
	$(REVIEW_VENV_PIP) install --upgrade pip
	@if [[ -f requirements-review.lock ]]; then \
		$(REVIEW_VENV_PIP) install -r requirements-review.lock; \
	else \
		echo "Missing requirements-review.lock."; \
		exit 1; \
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

smoke-local:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "Running stable single-machine baseline smoke test..."
	AUTORESEARCH_MODE=minimal PYTHONPATH=src $(VENV_PYTHON) -m pytest tests/test_stable_local_smoke.py -v

validate-req4:
	@echo "Validating requirement #4 scaffold readiness..."
	bash ./scripts/validate_stable_baseline.sh

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
	SEMGREP_HOME_DIR="$(CURDIR)/.semgrep-home"; \
	SEMGREP_CERT_FILE=""; \
	if [[ -x "$(REVIEW_VENV)/bin/mypy" ]]; then MYPY_BIN="$(REVIEW_VENV)/bin/mypy"; \
	elif [[ -x "$(VENV)/bin/mypy" ]]; then MYPY_BIN="$(VENV)/bin/mypy"; fi; \
	if [[ -x "$(REVIEW_VENV)/bin/bandit" ]]; then BANDIT_BIN="$(REVIEW_VENV)/bin/bandit"; \
	elif [[ -x "$(VENV)/bin/bandit" ]]; then BANDIT_BIN="$(VENV)/bin/bandit"; fi; \
	if [[ -x "$(REVIEW_VENV)/bin/semgrep" ]]; then SEMGREP_BIN="$(REVIEW_VENV)/bin/semgrep"; \
	elif [[ -x "$(VENV)/bin/semgrep" ]]; then SEMGREP_BIN="$(VENV)/bin/semgrep"; fi; \
	if ! command -v "$$MYPY_BIN" >/dev/null 2>&1; then echo "Missing mypy. Run 'make review-setup'."; exit 1; fi; \
	if ! command -v "$$BANDIT_BIN" >/dev/null 2>&1; then echo "Missing bandit. Run 'make review-setup'."; exit 1; fi; \
	if ! command -v "$$SEMGREP_BIN" >/dev/null 2>&1; then echo "Missing semgrep. Run 'make review-setup'."; exit 1; fi; \
	if [[ -x "$(REVIEW_VENV_PYTHON)" ]]; then \
		SEMGREP_CERT_FILE="$$("$(REVIEW_VENV_PYTHON)" -c 'import certifi; print(certifi.where())')"; \
	fi; \
	mkdir -p "$$SEMGREP_HOME_DIR"; \
	$$MYPY_BIN --config-file mypy.ini src/gatekeeper/static_analyzer.py src/gatekeeper/business_enforcer.py src/gatekeeper/llm_reviewer.py src/gatekeeper/board_summarizer.py; \
	$$BANDIT_BIN -q src/gatekeeper/static_analyzer.py src/gatekeeper/business_enforcer.py src/gatekeeper/llm_reviewer.py src/gatekeeper/board_summarizer.py; \
	HOME="$$SEMGREP_HOME_DIR" SSL_CERT_FILE="$$SEMGREP_CERT_FILE" $$SEMGREP_BIN --error --config=p/python src/gatekeeper/static_analyzer.py src/gatekeeper/business_enforcer.py src/gatekeeper/llm_reviewer.py src/gatekeeper/board_summarizer.py

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
	@CMD_ARGS="--run-id \"$(PROMOTE_RUN_ID)\" --base-ref \"$(PROMOTE_BASE_REF)\" --branch-prefix \"$(PROMOTE_BRANCH_PREFIX)\""; \
	if [[ "$(PROMOTE_PUSH)" == "1" ]]; then CMD_ARGS="$$CMD_ARGS --push"; fi; \
	if [[ "$(PROMOTE_OPEN_DRAFT_PR)" == "1" ]]; then CMD_ARGS="$$CMD_ARGS --open-draft-pr"; fi; \
	if [[ -x "$(VENV_PYTHON)" ]]; then \
		eval "PYTHONPATH=src $(VENV_PYTHON) scripts/promote_run.py $$CMD_ARGS"; \
	else \
		eval "PYTHONPATH=src $(PYTHON) scripts/promote_run.py $$CMD_ARGS"; \
	fi

assistant-doctor:
	@PYTHONPATH=src ./assistant doctor

assistant-triage:
	@if [[ -z "$(strip $(REPO))" || -z "$(strip $(ISSUE))" ]]; then \
		echo "Usage: make assistant-triage REPO='owner/repo' ISSUE=123"; \
		exit 1; \
	fi
	@PYTHONPATH=src ./assistant triage "$(REPO)" "$(ISSUE)"

assistant-execute:
	@if [[ -z "$(strip $(REPO))" || -z "$(strip $(ISSUE))" ]]; then \
		echo "Usage: make assistant-execute REPO='owner/repo' ISSUE=123"; \
		exit 1; \
	fi
	@PYTHONPATH=src ./assistant execute "$(REPO)" "$(ISSUE)"

assistant-review-pr:
	@if [[ -z "$(strip $(REPO))" || -z "$(strip $(PR))" ]]; then \
		echo "Usage: make assistant-review-pr REPO='owner/repo' PR=123"; \
		exit 1; \
	fi
	@PYTHONPATH=src ./assistant review-pr "$(REPO)" "$(PR)"

assistant-release-plan:
	@if [[ -z "$(strip $(REPO))" ]]; then \
		echo "Usage: make assistant-release-plan REPO='owner/repo' VERSION='v1.2.3'"; \
		exit 1; \
	fi
	@CMD_ARGS="release-plan \"$(REPO)\""; \
	if [[ -n "$(strip $(VERSION))" ]]; then CMD_ARGS="$$CMD_ARGS --version \"$(VERSION)\""; fi; \
	eval "PYTHONPATH=src ./assistant $$CMD_ARGS"

assistant-schedule:
	@PYTHONPATH=src ./assistant schedule run

telegram-butler-start:
	bash migration/openclaw/scripts/start-telegram-butler.sh

telegram-butler-status:
	bash migration/openclaw/scripts/status-api-daemon.sh
	bash migration/openclaw/scripts/status-telegram-poller.sh

telegram-butler-stop:
	bash migration/openclaw/scripts/stop-telegram-poller.sh
	bash migration/openclaw/scripts/stop-api-daemon.sh
