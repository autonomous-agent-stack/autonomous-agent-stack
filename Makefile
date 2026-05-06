ifeq ($(OS),Windows_NT)
SHELL := cmd.exe
PYTHON ?= python
VENV_BIN_DIR := Scripts
VENV_PYTHON_NAME := python.exe
VENV_PIP_NAME := pip.exe
else
SHELL := /bin/bash
PYTHON ?= python3
VENV_BIN_DIR := bin
VENV_PYTHON_NAME := python
VENV_PIP_NAME := pip
endif

VENV ?= .venv
VENV_PYTHON := $(VENV)/$(VENV_BIN_DIR)/$(VENV_PYTHON_NAME)
VENV_PIP := $(VENV)/$(VENV_BIN_DIR)/$(VENV_PIP_NAME)
REVIEW_VENV ?= .venv-review
REVIEW_VENV_PYTHON := $(REVIEW_VENV)/$(VENV_BIN_DIR)/$(VENV_PYTHON_NAME)
REVIEW_VENV_PIP := $(REVIEW_VENV)/$(VENV_BIN_DIR)/$(VENV_PIP_NAME)
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
CREWAI_AGENT ?= aas_crewai_demo
CREWAI_TASK ?= Produce a governed CrewAI demo artifact.
AGENT ?= $(CREWAI_AGENT)
TASK ?= $(CREWAI_TASK)
FEDERATION_PEER ?= demo-peer
FEDERATION_CAPABILITY ?= echo

.PHONY: help setup doctor doctor-linux start test-quick smoke-local smoke-cpv2 validate-req4 clean
.PHONY: ai-lab ai-lab-setup ai-lab-check ai-lab-up ai-lab-down ai-lab-status ai-lab-shell ai-lab-run masfactory-flight hygiene-check openhands openhands-dry-run openhands-controlled openhands-controlled-dry-run openhands-demo agent-run promote-run
.PHONY: review-setup review-gates-local assistant-doctor assistant-triage assistant-execute assistant-review-pr assistant-release-plan assistant-schedule
.PHONY: telegram-butler-start telegram-butler-status telegram-butler-stop telegram-ingress-audit
.PHONY: butler-start butler-stop butler-restart butler-status agent-list agent-start agent-stop agent-drain agent-restart agent-status
.PHONY: crewai-setup crewai-new crewai-run crewai-demo mcp-doctor quota-doctor federation-doctor federation-demo runtime-doctor capability-doctor agent-reach-crewai-demo haystack-demo langgraph-demo a2a-demo evergreen-demo bypass-ga ga-release-gate

help:
	@echo "Autonomous Agent Stack - common commands"
	@echo ""
	@echo "  make setup       Create .venv and install dependencies"
	@echo "  make doctor      Run environment checks"
	@echo "  make doctor-linux Run Linux remote-worker checks"
	@echo "  make start       Run doctor then start local API"
	@echo "  make setup-win   Run Windows PowerShell bootstrap"
	@echo "  make doctor-win  Run Windows PowerShell doctor"
	@echo "  make start-win   Run Windows PowerShell start"
	@echo "  make smoke-win   Run Windows PowerShell smoke test"
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
	@echo "  make crewai-demo Run the governed CrewAI-compatible demo agent"
	@echo "  make crewai-new AGENT='...' Scaffold a CrewAI-compatible AAS agent"
	@echo "  make crewai-run AGENT='...' TASK='...' Run a CrewAI-compatible AAS agent"
	@echo "  make mcp-doctor Validate governed MCP registry and policy"
	@echo "  make runtime-doctor Validate RuntimeAdapter v1 registry and doctors"
	@echo "  make capability-doctor Validate CapabilityManifest v1 registry"
	@echo "  make agent-reach-crewai-demo Run CrewAI + Agent-Reach governed demo"
	@echo "  make haystack-demo Run Haystack knowledge runtime demo"
	@echo "  make langgraph-demo Run LangGraph workflow runtime demo"
	@echo "  make a2a-demo Run A2A server/client bridge demo"
	@echo "  make evergreen-demo Run all evergreen control-plane demos"
	@echo "  make quota-doctor Validate usage quota policy and ledger"
	@echo "  make federation-doctor Validate federation peer and lease config"
	@echo "  make federation-demo Run a local bilateral federation lease/task demo"
	@echo "  make bypass-ga Run Evergreen OS GA bypass security checks"
	@echo "  make ga-release-gate Run Evergreen OS GA blocking release gate"
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
	@echo "  make butler-start SERVICE=all Start Butler service layer"
	@echo "  make butler-stop SERVICE=all Stop Butler service layer"
	@echo "  make butler-restart SERVICE=all Restart Butler service layer"
	@echo "  make butler-status SERVICE=all Show Butler service layer status"
	@echo "  make agent-list List hot-pluggable Butler agents"
	@echo "  make agent-start AGENT=source_collect Enable a Butler agent"
	@echo "  make agent-stop AGENT=source_collect Disable a Butler agent"
	@echo "  make agent-drain AGENT=source_collect Drain a Butler agent"
	@echo "  make agent-restart AGENT=source_collect Drain then enable a Butler agent"
	@echo "  make hygiene-check FAIL_ON_FINDINGS=1 Run prompt hygiene audit for src/"
	@echo "  make review-setup Create .venv-review with mypy/bandit/semgrep"
	@echo "  make review-gates-local Run mypy/bandit/semgrep on reviewer core modules"
	@echo "  make test-quick  Run quick smoke tests"
	@echo "  make smoke-local Run stable single-machine baseline smoke test"
	@echo "  make smoke-cpv2 固化 Control Plane v2 E2E smoke / Run Control Plane v2 E2E smoke"
	@echo "  make validate-req4 Validate requirement #4 scaffold readiness"
	@echo "  make clean       Remove Python cache folders"
	@echo ""
	@echo "Optional vars: HOST=127.0.0.1 PORT=8001"

setup:
	$(PYTHON) scripts/local_dev.py --venv $(VENV) setup --python $(PYTHON)

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
	$(PYTHON) scripts/local_dev.py --venv $(VENV) doctor --port $(PORT)

doctor-linux:
	$(PYTHON) scripts/local_dev.py --venv $(VENV) doctor --profile linux-remote --port $(PORT)

start:
	$(PYTHON) scripts/local_dev.py --venv $(VENV) start --host $(HOST) --port $(PORT)

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

crewai-setup:
	@if [[ ! -x "$(VENV_PIP)" ]]; then \
		echo "Missing $(VENV_PIP). Run 'make setup' first."; \
		exit 1; \
	fi
	$(VENV_PIP) install "crewai>=0.100"

crewai-new:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/crewai_scaffold.py $(AGENT)

crewai-run:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/agent_run.py --agent $(AGENT) --task "$(TASK)" --no-human-review

crewai-demo:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/crewai_demo_smoke.py --task "$(CREWAI_TASK)"

mcp-doctor:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/federation_ready_smoke.py mcp-doctor

quota-doctor:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/federation_ready_smoke.py quota-doctor

federation-doctor:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/federation_ready_smoke.py federation-doctor

federation-demo:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/federation_ready_smoke.py federation-demo --peer-id $(FEDERATION_PEER) --capability-id $(FEDERATION_CAPABILITY)

runtime-doctor:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/evergreen_smoke.py runtime-doctor

capability-doctor:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/evergreen_smoke.py capability-doctor

agent-reach-crewai-demo:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/evergreen_smoke.py agent-reach-crewai-demo

haystack-demo:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/evergreen_smoke.py haystack-demo

langgraph-demo:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/evergreen_smoke.py langgraph-demo

a2a-demo:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/evergreen_smoke.py a2a-demo

evergreen-demo:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/evergreen_smoke.py evergreen-demo

bypass-ga:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/bypass_ga.py

ga-release-gate:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) scripts/ga_release_gate.py

smoke-local:
	@if [[ ! -x "$(VENV_PYTHON)" ]]; then \
		echo "Missing $(VENV_PYTHON). Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "Running stable single-machine baseline smoke test..."
	AUTORESEARCH_MODE=minimal PYTHONPATH=src $(VENV_PYTHON) -m pytest tests/test_stable_local_smoke.py -v

smoke-cpv2:
	uv run --no-project --with-requirements requirements.txt python scripts/control_plane_v2_e2e_smoke.py

validate-req4:
	@echo "Validating requirement #4 scaffold readiness..."
	bash ./scripts/validate_stable_baseline.sh

setup-win:
	powershell -ExecutionPolicy Bypass -File .\setup.ps1

doctor-win:
	powershell -ExecutionPolicy Bypass -File .\doctor.ps1

start-win:
	powershell -ExecutionPolicy Bypass -File .\start.ps1

smoke-win:
	powershell -ExecutionPolicy Bypass -File .\scripts\windows_smoke.ps1

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

butler-start:
	scripts/butlerctl start $(or $(SERVICE),all)

butler-stop:
	scripts/butlerctl stop $(or $(SERVICE),all)

butler-restart:
	scripts/butlerctl restart $(or $(SERVICE),all)

butler-status:
	scripts/butlerctl status $(or $(SERVICE),all)

agent-list:
	scripts/butlerctl agent list

agent-status:
	scripts/butlerctl agent status $(AGENT)

agent-start:
	@if [[ -z "$(strip $(AGENT))" ]]; then echo "Usage: make agent-start AGENT=source_collect"; exit 1; fi
	scripts/butlerctl agent start "$(AGENT)"

agent-stop:
	@if [[ -z "$(strip $(AGENT))" ]]; then echo "Usage: make agent-stop AGENT=source_collect"; exit 1; fi
	scripts/butlerctl agent stop "$(AGENT)"

agent-drain:
	@if [[ -z "$(strip $(AGENT))" ]]; then echo "Usage: make agent-drain AGENT=source_collect"; exit 1; fi
	scripts/butlerctl agent drain "$(AGENT)"

agent-restart:
	@if [[ -z "$(strip $(AGENT))" ]]; then echo "Usage: make agent-restart AGENT=source_collect"; exit 1; fi
	scripts/butlerctl agent restart "$(AGENT)"

# 最近日志中的 409 / conflict 线索 + worker_run_queue 里 Hermes runtime 占比（默认 24h）
# Recent log hints for 409/conflict + Hermes runtime share in worker_run_queue (default 24h)
telegram-ingress-audit:
	$(PYTHON) scripts/telegram_ingress_health.py
