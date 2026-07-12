#!/usr/bin/env bash
# Runs one arm of the agentic benchmark against one task, n reps, scored on
# git diff. Does NOT flip plugin enable/disable state itself — that's global
# (~/.claude/settings.json, not project-scoped, see README gotcha) and
# switching it automatically between reps would be mutating shared state
# behind the user's back. Instead this script checks the arm's expected
# state and refuses to run if it doesn't match, telling you the one command
# to run first.
#
# Usage:
#   ./run-agentic.sh <task-file> <baseline|terse|eds> [n-reps] [model]
#
# Example:
#   ./run-agentic.sh tasks/01-build-churn-model.md eds 4
#   ./run-agentic.sh tasks/01-build-churn-model.md eds 2 claude-haiku-4-5-20251001
#
# [model] can also be set via the MODEL env var; the positional arg wins if
# both are given. Omit both to use the CLI's own default model.

set -euo pipefail

TASK_FILE="${1:?usage: run-agentic.sh <task-file> <baseline|terse|eds> [n-reps] [model]}"
ARM="${2:?usage: run-agentic.sh <task-file> <baseline|terse|eds> [n-reps] [model]}"
N_REPS="${3:-4}"
MODEL="${4:-${MODEL:-}}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURE="$HERE/fixtures/ecommerce"
RESULTS_ROOT="$HERE/results"

if [[ ! -f "$TASK_FILE" ]]; then
  echo "task file not found: $TASK_FILE" >&2
  exit 1
fi

# `claude plugin list` prints "eds@eds" then, 3 lines later, "Status: <icon> <state>".
eds_enabled() {
  claude plugin list 2>/dev/null | grep -A3 "eds@eds" | grep -q "Status:.*enabled"
}

case "$ARM" in
  baseline|terse)
    if eds_enabled; then
      echo "arm=$ARM requires the eds plugin DISABLED. Run: claude plugin disable eds@eds" >&2
      exit 1
    fi
    ;;
  eds)
    if ! eds_enabled; then
      echo "arm=eds requires the eds plugin ENABLED. Run: claude plugin enable eds@eds" >&2
      exit 1
    fi
    ;;
  *)
    echo "unknown arm '$ARM' — expected baseline|terse|eds" >&2
    exit 1
    ;;
esac

TASK_ID="$(basename "$TASK_FILE" .md)"
TICKET="$(sed -n '/^## Ticket/,/^## /p' "$TASK_FILE" | sed '1d;$d' | sed 's/^> //')"

for rep in $(seq 1 "$N_REPS"); do
  WORKDIR="$(mktemp -d)"
  cp -R "$FIXTURE/." "$WORKDIR/"
  (
    cd "$WORKDIR"
    git init -q
    git add -A
    git -c user.email=bench@local -c user.name=bench commit -q -m "baseline"

    if [[ "$ARM" == "terse" ]]; then
      echo "Be concise, prefer simple models. Skip anything the request doesn't need." > CLAUDE.md
      git add CLAUDE.md
      git -c user.email=bench@local -c user.name=bench commit -q -m "terse control prompt"
    fi

    OUT_DIR="$RESULTS_ROOT/$TASK_ID/$ARM/rep-$rep"
    mkdir -p "$OUT_DIR"

    CLAUDE_ARGS=(-p "$TICKET" --output-format text)
    if [[ -n "$MODEL" ]]; then
      CLAUDE_ARGS+=(--model "$MODEL")
    fi
    claude "${CLAUDE_ARGS[@]}" > "$OUT_DIR/transcript.txt" 2>&1 || true
    git diff > "$OUT_DIR/diff.patch"
    git status --porcelain > "$OUT_DIR/status.txt"
  )
  rm -rf "$WORKDIR"
  echo "done: $TASK_ID / $ARM / rep-$rep -> $RESULTS_ROOT/$TASK_ID/$ARM/rep-$rep"
done
