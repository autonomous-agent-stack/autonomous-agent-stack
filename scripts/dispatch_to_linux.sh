#!/usr/bin/env bash
set -euo pipefail

LINUX_HOST="${LINUX_HOST:-lisa@100.68.246.67}"
LINUX_REPO="${LINUX_REPO:-~/autonomous-agent-stack}"
LINUX_ENV_FILE="${LINUX_ENV_FILE:-}"
TASK="${1:?usage: dispatch_to_linux.sh 'task prompt'}"

QUOTED_LINUX_REPO="$(printf '%q' "$LINUX_REPO")"
QUOTED_LINUX_ENV_FILE="$(printf '%q' "$LINUX_ENV_FILE")"
QUOTED_TASK="$(printf '%q' "$TASK")"

read -r -d '' REMOTE_SCRIPT <<EOF || true
set -euo pipefail

cd ${QUOTED_LINUX_REPO}

ENV_FILE=""
if [[ -n ${QUOTED_LINUX_ENV_FILE} ]]; then
  ENV_FILE=${QUOTED_LINUX_ENV_FILE}
elif [[ -f .env.linux ]]; then
  ENV_FILE=.env.linux
elif [[ -f ai_lab.env ]]; then
  ENV_FILE=ai_lab.env
else
  echo "missing .env.linux or ai_lab.env in ${LINUX_REPO}" >&2
  exit 40
fi

set -a
source "\${ENV_FILE}"
set +a
source .venv/bin/activate

bash ./scripts/linux_housekeeper.sh enqueue ${QUOTED_TASK}
EOF

ssh "$LINUX_HOST" "bash -lc $(printf '%q' "$REMOTE_SCRIPT")"
