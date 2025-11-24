# Check if uv is installed
if (!(Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Host "uv not found. Installing..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
}

# Run the application using uv
# uv run automatically creates the venv and installs dependencies if needed
uv run pavatools
