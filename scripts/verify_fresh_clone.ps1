$ErrorActionPreference = "Stop"

Write-Host "=== RAO Fish Embassy - fresh-clone verification ===" -ForegroundColor Cyan
Write-Host ""

python --version
Write-Host "  OK Python" -ForegroundColor Green

Write-Host ""
Write-Host "--- Django system check ---"
python manage.py check
if ($LASTEXITCODE -ne 0) { throw "check failed" }

Write-Host ""
Write-Host "--- Migration plan ---"
python manage.py makemigrations --check --dry-run
if ($LASTEXITCODE -ne 0) { throw "missing migrations" }

Write-Host ""
Write-Host "--- Migrate ---"
python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw "migrate failed" }

Write-Host ""
Write-Host "--- Seed ---"
python manage.py seed
if ($LASTEXITCODE -ne 0) { throw "seed failed" }

Write-Host ""
Write-Host "--- Test suite ---"
python manage.py test --settings=config.settings.test
if ($LASTEXITCODE -ne 0) { throw "tests failed" }

Write-Host ""
Write-Host "=== All checks complete ===" -ForegroundColor Green