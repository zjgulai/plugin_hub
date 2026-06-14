#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

: "${PLUGIN_HUB_COLLECTION_TASK_MAX_ATTEMPTS:=3}"
: "${PLUGIN_HUB_COLLECTION_TASK_RETRY_DELAY_SECONDS:=300}"
: "${PLUGIN_HUB_COLLECTION_TASK_CLAIM_TTL_SECONDS:=900}"
: "${PLUGIN_HUB_COLLECTION_TASK_WORKER_ID:=collection-worker-1}"

export PLUGIN_HUB_COLLECTION_TASK_MAX_ATTEMPTS
export PLUGIN_HUB_COLLECTION_TASK_RETRY_DELAY_SECONDS
export PLUGIN_HUB_COLLECTION_TASK_CLAIM_TTL_SECONDS
export PLUGIN_HUB_COLLECTION_TASK_WORKER_ID

if [[ ! -f package.json ]]; then
  echo "project root not found: ${PROJECT_ROOT}"
  exit 1
fi

export PLUGIN_HUB_DATABASE_URL="${PLUGIN_HUB_DATABASE_URL:-sqlite+pysqlite:///./tmp/debug/plugin-hub-worker-preview.db}"

exec pnpm collection:worker "$@"
