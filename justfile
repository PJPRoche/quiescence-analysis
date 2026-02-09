# Quiescence Analysis - Task Runner

# Show available commands
default:
    @just --list

# Setup: Install dependencies and create virtual environment
setup:
    uv venv
    uv pip install -e .
    @echo "✓ Environment ready. Activate with: source .venv/bin/activate"

# Update dependencies
update-deps:
    uv pip install --upgrade -e .

# Show Python environment info
env-info:
    @echo "=== Python Environment ==="
    @which python
    @python --version
    @echo "\n=== UV Version ==="
    @uv --version
    @echo "\n=== Installed Packages ==="
    @uv pip list

# Validate configuration
check-config:
    @python -c "import sys; sys.path.insert(0, 'analysis'); from utilities import *; print('✓ Utilities module imported successfully')" 2>/dev/null || echo "⚠️  Could not import utilities module"

# Clean Python cache files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    @echo "✓ Python cache files cleaned"

# Clean virtual environment
clean-venv:
    rm -rf .venv
    @echo "✓ Virtual environment removed"
