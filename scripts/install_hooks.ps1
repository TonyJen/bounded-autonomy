# One-time setup: point git at the repo-tracked hooks directory.
# Run from the repo root: powershell -File scripts/install_hooks.ps1
git config core.hooksPath .githooks
Write-Host "core.hooksPath set to .githooks — pre-commit gate active (pytest + mock-mode evals)."
