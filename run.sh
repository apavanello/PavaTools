#!/bin/bash

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Run the application using uv
# uv run automatically creates the venv and installs dependencies if needed
uv run pavatools
