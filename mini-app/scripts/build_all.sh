#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Building all tenants ==="
for config in "$PROJECT_DIR/tenants"/*.json; do
  slug="$(basename "$config" .json)"
  echo ""
  echo "--- Tenant: $slug ---"
  TENANT="$slug" bash "$SCRIPT_DIR/build_one.sh"
done
echo ""
echo "=== All builds complete ==="
ls -d "$PROJECT_DIR/dist"/*/
