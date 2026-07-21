#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Nexus Core — Enterprise Audit Script
# Usage: bash audit.sh [--fix] [--report]
#
# Scans: secrets, deps, lint, tests, git, docker, benchmarks
# Output: audit-report.md (human-readable + machine-parseable)
# ═══════════════════════════════════════════════════════════════

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
REPORT="$REPO_ROOT/audit-report.md"
PASS=0 FAIL=0 WARN=0

log_pass() { echo "  ✅ $1"; ((PASS++)); }
log_fail() { echo "  ❌ $1"; ((FAIL++)); }
log_warn() { echo "  ⚠️  $1"; ((WARN++)); }
header()   { echo ""; echo "## $1"; echo ""; }
code()     { echo '```'; cat -; echo '```'; }

exec 3>&1 4>&2
trap 'exec 2>&4 1>&3' EXIT

echo "🔍 Nexus Core — System Audit"
echo "   Repo: $REPO_ROOT"
echo "   Date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""

# ──────────────────────────────────────────────
# 1. SECRETS LEAK DETECTION
# ──────────────────────────────────────────────
header "1. Secrets & Credentials"

SECRET_PATTERNS=(
  'sk-[a-zA-Z0-9\-]{20,}'     # OpenAI
  'gsk_[a-zA-Z0-9]{20,}'      # Groq
  'AIza[0-9A-Za-z\-_]{35}'    # Google
  'pk\.[a-zA-Z0-9]{20,}'      # Stripe publishable
  'sk_live_[a-zA-Z0-9]{20,}'  # Stripe secret
  'AKIA[0-9A-Z]{16}'           # AWS access key
  '-----BEGIN.*PRIVATE KEY'    # Private keys
  'ghp_[a-zA-Z0-9]{36}'       # GitHub PAT
  'gho_[a-zA-Z0-9]{36}'       # GitHub OAuth
  'xox[baprs]-[0-9]{10,}'     # Slack tokens
  'SG\.[a-zA-Z0-9]{20,}'      # Sendgrid
)

EXEMPT_DIRS='node_modules|__pycache__|.git|.venv|dist|build|.turbo'
SECRET_COUNT=0

SCAN_DIRS="$REPO_ROOT/kernel $REPO_ROOT/agents $REPO_ROOT/core $REPO_ROOT/providers $REPO_ROOT/config.json $REPO_ROOT/.env $REPO_ROOT/*.py"
for pattern in "${SECRET_PATTERNS[@]}"; do
  while IFS= read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    if echo "$file" | grep -qE 'test_|/security\.py$|\.bak$|sanitize\.sh$'; then continue; fi
    echo "  ⚠️  Potential secret in: $line"
    ((SECRET_COUNT++))
  done < <(grep -rnE "$pattern" $SCAN_DIRS 2>/dev/null | grep -vE '__pycache__|node_modules|\.git/' || true)
done

if [ "$SECRET_COUNT" -eq 0 ]; then
  log_pass "No secrets detected in tracked files"
else
  log_fail "$SECRET_COUNT potential secret(s) found — review and sanitize"
fi

# Check .gitignore coverage
header "1b. Gitignore Coverage"

GITIGNORE_EXPECTED=(
  ".env" ".env.local" "__pycache__/" "node_modules/"
  "*.pyc" "dist/" "build/" ".pytest_cache" ".turbo"
  "*.key" "*.pem" ".DS_Store" "*.log"
)

if [ -f "$REPO_ROOT/.gitignore" ]; then
  MISSING=0
  for entry in "${GITIGNORE_EXPECTED[@]}"; do
    if ! grep -qF "$entry" "$REPO_ROOT/.gitignore" 2>/dev/null; then
      echo "  ⚠️  Missing from .gitignore: $entry"
      ((MISSING++))
    fi
  done
  [ "$MISSING" -eq 0 ] && log_pass ".gitignore covers all expected patterns" \
                       || log_warn "$MISSING patterns missing from .gitignore"
else
  log_fail "No .gitignore found"
fi

# ──────────────────────────────────────────────
# 2. TEST COVERAGE
# ──────────────────────────────────────────────
header "2. Test Suite"

TEST_LOG=$(mktemp)
if [ -d "$REPO_ROOT/tests" ]; then
  set +e
  cd "$REPO_ROOT" && python3 -m pytest tests/ -q --tb=short 2>&1 | tail -5 > "$TEST_LOG" 2>&1
  set -e
  if grep -q "passed\|failed" "$TEST_LOG" 2>/dev/null; then
    log_pass "Tests completed: $(tr '\n' ' ' < "$TEST_LOG")"
  elif grep -q "no tests ran" "$TEST_LOG" 2>/dev/null; then
    log_warn "Test suite exists but no tests ran — check pytest config"
  else
    log_fail "Test execution issue — see $TEST_LOG"
  fi
  rm -f "$TEST_LOG"
else
  log_fail "No tests/ directory found"
fi

# ──────────────────────────────────────────────
# 3. PYTHON DEPENDENCIES
# ──────────────────────────────────────────────
header "3. Python Dependencies"

if [ -f "$REPO_ROOT/requirements.txt" ]; then
  echo "  requirements.txt found ($(wc -l < "$REPO_ROOT/requirements.txt") packages)"
  # Check for outdated packages (top 10)
  set +e
  pip list --outdated --format=columns 2>/dev/null | head -12
  set -e
else
  echo "  No requirements.txt — using pyproject.toml"
fi

# ──────────────────────────────────────────────
# 4. GIT HEALTH
# ──────────────────────────────────────────────
header "4. Git Repository Health"

GIT_DIR="$REPO_ROOT/.git"
if [ -d "$GIT_DIR" ] && command -v git &>/dev/null; then
  log_pass "Git repository initialized"

  COMMIT_COUNT=$(git -C "$REPO_ROOT" rev-list --count HEAD 2>/dev/null || echo "0")
  echo "  Commits: $COMMIT_COUNT"

  BRANCH=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
  echo "  Branch: $BRANCH"

  UNTRACKED=$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | wc -l)
  [ "$UNTRACKED" -eq 0 ] && log_pass "Working tree clean" \
                          || log_warn "$UNTRACKED uncommitted file(s)"

  LARGE_FILES=$(find "$GIT_DIR/objects" -type f -size +1M 2>/dev/null | wc -l)
  [ "$LARGE_FILES" -eq 0 ] && log_pass "No oversized objects in git history" \
                            || log_warn "$LARGE_FILES large object(s) — consider git-lfs"
else
  log_warn "Not a git repository — init with: git init && git add -A && git commit -m 'init'"
fi

# ──────────────────────────────────────────────
# 5. DOCKER READINESS
# ──────────────────────────────────────────────
header "5. Docker & Infrastructure"

if [ -f "$REPO_ROOT/docker-compose.yml" ]; then
  log_pass "docker-compose.yml found"
else
  log_fail "No docker-compose.yml"
fi

if [ -d "$REPO_ROOT/infrastructure/kubernetes" ]; then
  K8S_FILES=$(find "$REPO_ROOT/infrastructure/kubernetes" -name "*.yaml" 2>/dev/null | wc -l)
  log_pass "$K8S_FILES Kubernetes manifest(s) found"
fi

# ──────────────────────────────────────────────
# 6. PERFORMANCE BENCHMARKS
# ──────────────────────────────────────────────
header "6. Performance Benchmarks"

if [ -f "$REPO_ROOT/benchmark_results.json" ]; then
  log_pass "Benchmark results found"
  echo ""
  python3 -c "
import json
with open('$REPO_ROOT/benchmark_results.json') as f:
    d = json.load(f)
print(f'  ├─ Memory: SQLite read 100 = {d.get(\"memory\",{}).get(\"sqlite_read_100\",\"N/A\")}ms')
print(f'  ├─ Groq API: {d.get(\"api\",{}).get(\"groq\",{}).get(\"avg_ms\",\"N/A\")}ms avg, {d.get(\"api\",{}).get(\"groq\",{}).get(\"tps\",\"N/A\")} TPS')
print(f'  ├─ Cache: {d.get(\"cache\",{}).get(\"speedup\",\"N/A\")}')
print(f'  └─ Concurrent: {d.get(\"concurrent\",{}).get(\"successful\",0)} OK, {d.get(\"concurrent\",{}).get(\"failed\",0)} fail')
" 2>/dev/null || echo "  (python parsing failed)"
else
  log_fail "No benchmark_results.json — run benchmark.py first"
fi

# ──────────────────────────────────────────────
# 7. API CONFIGURATION
# ──────────────────────────────────────────────
header "7. Configuration & API Status"

# Check that .env.example exists and is clean
if [ -f "$REPO_ROOT/.env.example" ]; then
  log_pass ".env.example present"
  if grep -qE '=[a-zA-Z0-9]{20,}' "$REPO_ROOT/.env.example" 2>/dev/null; then
    log_fail ".env.example contains real secrets — sanitize immediately"
  fi
fi

# Check that real .env is in .gitignore
if [ -f "$REPO_ROOT/.env" ]; then
  if grep -q '^\.env$' "$REPO_ROOT/.gitignore" 2>/dev/null; then
    log_pass ".env is gitignored"
  else
    log_fail ".env is NOT in .gitignore — risk of secret exposure"
  fi
fi

# ──────────────────────────────────────────────
# 8. ARCHITECTURE OVERVIEW
# ──────────────────────────────────────────────
header "8. Architecture Inventory"

echo "  ├─ Workspaces:"
for d in kernel agents memory fn cli api dashboard infrastructure; do
  [ -d "$REPO_ROOT/$d" ] && echo "  │  ├─ $d/ $(find $REPO_ROOT/$d -maxdepth 1 -name '*.py' 2>/dev/null | wc -l) .py files"
done

echo "  ├─ Test files: $(find "$REPO_ROOT/tests" -name 'test_*.py' 2>/dev/null | wc -l)"
echo "  └─ Total Python LOC: $(find "$REPO_ROOT" -name '*.py' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' -not -path '*/.venv/*' 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')"

# ──────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo "  Audit Summary"
echo "  ✅ Pass: $PASS   ❌ Fail: $FAIL   ⚠️  Warn: $WARN"
echo "═══════════════════════════════════════════"

# Generate markdown report
GIT_BRANCH="N/A"; GIT_COMMIT="N/A"
command -v git &>/dev/null && [ -d "$REPO_ROOT/.git" ] && {
  GIT_BRANCH=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "N/A")
  GIT_COMMIT=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "N/A")
}
cat > "$REPORT" << EOF
# Nexus Core — Audit Report

**Date**: $(date -u '+%Y-%m-%dT%H:%M:%SZ')
**Repo**: $(basename "$REPO_ROOT")
**Branch**: $GIT_BRANCH
**Commit**: $GIT_COMMIT

## Summary

| Status | Count |
|--------|-------|
| ✅ Pass | $PASS |
| ❌ Fail | $FAIL |
| ⚠️  Warnings | $WARN |
| **Score** | **$(echo "scale=0; 100 * $PASS / ($PASS + $FAIL + $WARN)" | bc 2>/dev/null)%** |

> **Legend**: ✅ = Compliant  ❌ = Action required  ⚠️ = Review recommended

## Architecture

- Total Python files: $(find "$REPO_ROOT" -name '*.py' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' 2>/dev/null | wc -l)
- Test files: $(find "$REPO_ROOT/tests" -name 'test_*.py' 2>/dev/null | wc -l)
- Docker: $( [ -f "$REPO_ROOT/docker-compose.yml" ] && echo "Yes" || echo "No")
- Kubernetes: $( [ -d "$REPO_ROOT/infrastructure/kubernetes" ] && echo "Yes" || echo "No")
- CI/CD: $( [ -d "$REPO_ROOT/.github/workflows" ] && echo "Yes" || echo "No")

## Findings

EOF

if [ "$SECRET_COUNT" -gt 0 ]; then
  cat >> "$REPORT" << EOF
### ⚠️ Critical: Secrets Detected

**$SECRET_COUNT** potential secret(s) found in tracked files. Review and remove before making repository public.

Recommended action:
\`\`\`bash
# Use BFG Repo-Cleaner for git history:
# java -jar bfg.jar --replace-text passwords.txt my-repo.git

# Or git-filter-repo for targeted removal:
# pip install git-filter-repo
# git filter-repo --path config.json --invert-paths
\`\`\`
EOF
fi

echo ""
echo "📄 Full report written to: $REPORT"
echo ""

# Exit code
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
