#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-4173}"

echo "[INFO] 인증기 결산 시스템 서버를 시작합니다."
echo "[INFO] 브라우저에서 접속: http://localhost:${PORT}/index.html"
echo "[INFO] 종료: Ctrl + C"

python3 -m http.server "$PORT"
