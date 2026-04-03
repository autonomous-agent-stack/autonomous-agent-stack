#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Create the 4 parallel subtitle worktrees from a clean checkpointed base ref.

Usage:
  scripts/create_parallel_subtitle_worktrees.sh [--base-ref <ref>] [--worktree-root <dir>] [--branch-prefix <prefix>]

Options:
  --base-ref <ref>        Git ref to branch from. Default: HEAD
  --worktree-root <dir>   Parent directory for sibling worktrees.
                          Default: parent of the current repo root
  --branch-prefix <name>  Prefix for the new branches. Default: codex
  -h, --help              Show this help text

Behavior:
  - Fails closed if the current worktree is dirty.
  - Creates 4 sibling worktrees from the requested base ref.
  - Initializes the minimal directory skeleton for each line.
  - Prints the first command to run in each worktree.

Notes:
  - This script does not auto-stash or auto-commit your current changes.
  - If subtitle-offline-dev-kit or routing files are still uncommitted, checkpoint
    them first or the new worktrees will not contain them.
EOF
}

BASE_REF="HEAD"
BRANCH_PREFIX="codex"
WORKTREE_ROOT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-ref)
      BASE_REF="${2:?missing value for --base-ref}"
      shift 2
      ;;
    --worktree-root)
      WORKTREE_ROOT="${2:?missing value for --worktree-root}"
      shift 2
      ;;
    --branch-prefix)
      BRANCH_PREFIX="${2:?missing value for --branch-prefix}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel)"
REPO_NAME="$(basename "$REPO_ROOT")"

if [[ -z "$WORKTREE_ROOT" ]]; then
  WORKTREE_ROOT="$(dirname "$REPO_ROOT")"
fi

mkdir -p "$WORKTREE_ROOT"
WORKTREE_ROOT="$(cd "$WORKTREE_ROOT" && pwd -P)"

ensure_clean_worktree() {
  if ! git -C "$REPO_ROOT" diff --quiet; then
    return 1
  fi
  if ! git -C "$REPO_ROOT" diff --cached --quiet; then
    return 1
  fi
  if [[ -n "$(git -C "$REPO_ROOT" ls-files --others --exclude-standard)" ]]; then
    return 1
  fi
  return 0
}

require_clean_checkpoint() {
  if ensure_clean_worktree; then
    return 0
  fi

  cat >&2 <<EOF
Refusing to create worktrees from a dirty base worktree.

Reason:
  New worktrees are created from $BASE_REF only. Uncommitted files such as
  subtitle-offline-dev-kit/, docs/agent-contract-and-routing-foundation.md, or
  routing foundation changes will be missing unless you checkpoint them first.

Suggested next steps:
  1. Review current changes:
     git -C "$REPO_ROOT" status --short
  2. Create a checkpoint commit or stash manually.
  3. Re-run this script.
EOF
  exit 1
}

require_ref() {
  if ! git -C "$REPO_ROOT" rev-parse --verify "${BASE_REF}^{commit}" >/dev/null 2>&1; then
    echo "Base ref does not resolve to a commit: $BASE_REF" >&2
    exit 1
  fi
}

branch_exists() {
  local branch="$1"
  git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$branch"
}

path_conflicts() {
  local worktree_path="$1"
  [[ -e "$worktree_path" ]]
}

create_one() {
  local label="$1"
  local branch="$2"
  local worktree_path="$3"
  local dirs_csv="$4"

  if branch_exists "$branch"; then
    echo "Branch already exists, refusing to reuse: $branch" >&2
    exit 1
  fi

  if path_conflicts "$worktree_path"; then
    echo "Target worktree path already exists: $worktree_path" >&2
    exit 1
  fi

  echo "Creating $label"
  git -C "$REPO_ROOT" worktree add -b "$branch" "$worktree_path" "$BASE_REF"

  local dir
  IFS=',' read -r -a dir_list <<< "$dirs_csv"
  for dir in "${dir_list[@]}"; do
    mkdir -p "$worktree_path/$dir"
  done
}

print_next_steps() {
  local batch_path="$WORKTREE_ROOT/${REPO_NAME}-batch-checker"
  local harvest_path="$WORKTREE_ROOT/${REPO_NAME}-fixture-harvest"
  local replay_path="$WORKTREE_ROOT/${REPO_NAME}-worker-harness"
  local chunker_path="$WORKTREE_ROOT/${REPO_NAME}-chunker"

  cat <<EOF

Created worktrees:
  batch-checker : $batch_path
  fixture-harvest : $harvest_path
  worker-replay : $replay_path
  notes-chunker : $chunker_path

Suggested first commands:
  [$batch_path]
  python subtitle-offline-dev-kit/scripts/check_subtitle_contract.py subtitle-offline-dev-kit/fixtures

  [$harvest_path]
  python subtitle-offline-dev-kit/scripts/harvest_real_subtitles.py --input-dir /absolute/path/to/subtitles --output-dir subtitle-offline-dev-kit/fixtures/harvested

  [$replay_path]
  python scripts/replay_openhands_worker_requests.py --input artifacts/worker-replay/recorded_requests.json --output artifacts/worker-replay/replay_results.json

  [$chunker_path]
  python subtitle-offline-dev-kit/scripts/chunk_subtitles_to_notes.py --input-dir subtitle-offline-dev-kit/fixtures --output-dir artifacts/subtitle-notes-ready

Suggested test file skeletons:
  subtitle-offline-dev-kit/tests/test_check_subtitle_contract_reports.py
  subtitle-offline-dev-kit/tests/test_harvest_real_subtitles.py
  tests/test_openhands_worker_replay.py
  subtitle-offline-dev-kit/tests/test_chunk_subtitles_to_notes.py
EOF
}

main() {
  require_ref
  require_clean_checkpoint

  local batch_branch="${BRANCH_PREFIX}/subtitle-contract-batch-checker"
  local harvest_branch="${BRANCH_PREFIX}/subtitle-fixture-harvest"
  local replay_branch="${BRANCH_PREFIX}/worker-replay-harness"
  local chunker_branch="${BRANCH_PREFIX}/subtitle-notes-chunker"

  local batch_path="$WORKTREE_ROOT/${REPO_NAME}-batch-checker"
  local harvest_path="$WORKTREE_ROOT/${REPO_NAME}-fixture-harvest"
  local replay_path="$WORKTREE_ROOT/${REPO_NAME}-worker-harness"
  local chunker_path="$WORKTREE_ROOT/${REPO_NAME}-chunker"

  create_one \
    "subtitle contract batch checker" \
    "$batch_branch" \
    "$batch_path" \
    "subtitle-offline-dev-kit/reports"

  create_one \
    "real subtitle fixture harvest" \
    "$harvest_branch" \
    "$harvest_path" \
    "subtitle-offline-dev-kit/fixtures/harvested,subtitle-offline-dev-kit/reports"

  create_one \
    "worker replay harness" \
    "$replay_branch" \
    "$replay_path" \
    "artifacts/worker-replay"

  create_one \
    "subtitle notes chunker" \
    "$chunker_branch" \
    "$chunker_path" \
    "artifacts/subtitle-notes-ready"

  print_next_steps
}

main
