#!/usr/bin/env bash
set -euo pipefail

BENCH_ROOT="${BENCH_ROOT:-/home/runner/frappe-bench}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "${SCRIPT_DIR}/ensure_bench_web.sh"

cd "${BENCH_ROOT}"
set -o pipefail
source env/bin/activate
python -m playwright install --with-deps chromium
pytest apps/approvals/approvals/tests \
	--browser chromium \
	--cov=approvals \
	--cov-report=xml \
	--cov-report=term-missing \
	--disable-warnings -s | tee apps/approvals/pytest-coverage.txt
