#!/usr/bin/env bash
# AZ-OS one-click install. Counted download via this project's Worker.
# Usage: curl -fsSL https://azos-download-tracker.vibelock.workers.dev/install.sh | bash
set -euo pipefail

HOST="${AZOS_HOME_HOST:-https://azos-download-tracker.vibelock.workers.dev}"
ASSET="${AZOS_HOME_ASSET:-azos-0.3.0.tar.gz}"
WORKDIR="${AZOS_HOME:-$HOME/azos}"

mkdir -p "$WORKDIR"
cd "$WORKDIR"

echo "Downloading counted tarball from ${HOST}/download (User-Agent Mozilla/5.0)…"
curl -fsSL -A 'Mozilla/5.0' "${HOST}/download?asset=${ASSET}" -o "${ASSET}"

tar -xzf "${ASSET}"
DIR="$(find . -maxdepth 1 -type d -name 'azos-*' | head -n 1)"
if [ -n "${DIR}" ]; then
  cd "${DIR}"
fi

python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .

echo
echo "Installed AZ-OS."
echo "1. Run: azos ui"
echo "2. Open http://127.0.0.1:8800/"
echo "3. Choose Open shell"
echo "Author: Aziel Eliab."
