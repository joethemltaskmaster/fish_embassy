#!/usr/bin/env bash
set -euo pipefail

echo "=== RAO Fish Embassy — fresh-clone verification ==="
echo

python --version
echo "  ✓ Python"

echo
echo "--- Django system check ---"
python manage.py check

echo
echo "--- Migration plan (should not fail) ---"
python manage.py makemigrations --check --dry-run

echo
echo "--- Migrate against a throwaway DB ---"
export POSTGRES_DB="${POSTGRES_DB:-rao_verify}"
python manage.py migrate --noinput

echo
echo "--- Seed ---"
python manage.py seed

echo
echo "--- Test suite ---"
python manage.py test --settings=config.settings.test

echo
echo "=== All checks complete ==="