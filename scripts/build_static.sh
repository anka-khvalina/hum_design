#!/usr/bin/env bash
# Build Mini App into human-design-service/app/static for single-service deploy.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/mini-app"
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-}"
npm ci
npm run build
rm -rf "$ROOT/human-design-service/app/static"
mkdir -p "$ROOT/human-design-service/app/static"
cp -a "$ROOT/mini-app/dist/." "$ROOT/human-design-service/app/static/"
echo "Mini App copied to human-design-service/app/static"
