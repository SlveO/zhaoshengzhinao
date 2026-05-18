#!/usr/bin/env bash
set -euo pipefail

TENANT="${TENANT:-gdufs}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Building tenant: $TENANT ==="

# Generate tenant.config.ts
node build.config.js

# Build the mini program
npx uni build -p mp-weixin

# Move output to tenant-specific directory
if [ -d "dist/build/mp-weixin" ]; then
  mkdir -p "dist/$TENANT"
  rm -rf "dist/$TENANT"/*
  cp -r dist/build/mp-weixin/* "dist/$TENANT/"
  echo "✓ Build complete: dist/$TENANT/"
else
  echo "✗ Build failed: dist/build/mp-weixin not found"
  exit 1
fi
