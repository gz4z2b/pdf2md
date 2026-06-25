#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${PROJECT_ROOT}/.venv"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "未找到 Python，请先安装 Python 3.11 或更高版本。"
  exit 1
fi

"${PYTHON_BIN}" - <<'PY'
import sys

if sys.version_info < (3, 11):
    raise SystemExit("Python 版本过低，请安装 Python 3.11 或更高版本。")
PY

if [ ! -d "${VENV_DIR}" ]; then
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

VENV_PYTHON="${VENV_DIR}/bin/python"
"${VENV_PYTHON}" -m pip install --upgrade pip
"${VENV_PYTHON}" -m pip install -r "${PROJECT_ROOT}/requirements.txt"

PYTHONPATH="${PROJECT_ROOT}/src" "${VENV_PYTHON}" -m pdf2md.cli "$@"
