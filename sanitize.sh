#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Nexus Core — Sanitize Secrets
# Usage: bash sanitize.sh
#
# Finds hardcoded secrets and replaces with placeholders.
# Creates .bak files for each modified file.
# ═══════════════════════════════════════════════════════════════

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
DRY_RUN="${1:-}"  # pass --dry-run to preview without modifying

# Secrets found in the codebase (from audit)
# Hash-addressed secret references (not raw keys)
# Generated: sha256sum of original keys
declare -A SECRETS=(
  ["PLACEHOLDER__REPLACE_WITH_SECRET_1"]="GROQ_API_KEY_PLACEHOLDER"
  ["PLACEHOLDER__REPLACE_WITH_SECRET_2"]="GROQ_API_KEY_PLACEHOLDER_2"
)

COUNT=0
for secret in "${!SECRETS[@]}"; do
  placeholder="${SECRETS[$secret]}"
  while IFS= read -r file; do
    [ -z "$file" ] && continue
    if [ "$DRY_RUN" == "--dry-run" ]; then
      echo "  [DRY-RUN] Would sanitize: $file"
    else
      cp "$file" "$file.bak"
      sed -i "s/$secret/$placeholder/g" "$file"
      echo "  ✅ Sanitized: $file ($placeholder)"
    fi
    ((COUNT++))
  done < <(grep -rl "$secret" "$REPO_ROOT" --include="*.py" --include="*.json" --include="*.yaml" --include="*.yml" --include="*.sh" --include="*.env" --include="*.txt" --include="*.md" --include="*.toml" 2>/dev/null || true)
done

echo ""
if [ "$DRY_RUN" == "--dry-run" ]; then
  echo "🔍 Dry-run complete — $COUNT file(s) would be sanitized"
  echo "   Run: bash sanitize.sh  (without --dry-run) to apply"
else
  echo "🧹 Sanitized $COUNT file(s) — .bak backups created"
  echo "   Verify: grep -rn 'PLACEHOLDER' ."
  echo "   Then: find . -name '*.bak' -delete"
fi
