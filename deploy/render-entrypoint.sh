#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${WTP_MIGRATION_HOLD:-0}" == "1" ]]; then
  echo "Starting in migration-hold mode; the application database is not open."
  exec python /app/deploy/migration_hold_server.py
fi

python /app/deploy/verify_render_db.py

runtime_dir="${WTP_RUNTIME_DIR:-/app/data/runtime}"
mkdir -p "${runtime_dir}" "${runtime_dir}/logs"

scheduler_pid=""
api_pid=""

shutdown() {
  local status="${1:-0}"
  trap - INT TERM EXIT
  if [[ -n "${scheduler_pid}" ]] && kill -0 "${scheduler_pid}" 2>/dev/null; then
    kill -TERM "${scheduler_pid}" 2>/dev/null || true
  fi
  if [[ -n "${api_pid}" ]] && kill -0 "${api_pid}" 2>/dev/null; then
    kill -TERM "${api_pid}" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  exit "${status}"
}

trap 'shutdown 143' INT TERM

if [[ "${WTP_SCHEDULER_ENABLED:-0}" == "1" ]]; then
  python /app/jobs/scheduler.py &
  scheduler_pid=$!
  echo "Scheduler started as PID ${scheduler_pid}."
fi

workers="${WTP_WEB_CONCURRENCY:-1}"
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8006}" --workers "${workers}" &
api_pid=$!
echo "API started as PID ${api_pid} with ${workers} worker(s)."

set +e
if [[ -n "${scheduler_pid}" ]]; then
  wait -n "${api_pid}" "${scheduler_pid}"
else
  wait "${api_pid}"
fi
status=$?
set -e

shutdown "${status}"
