set shell := ["bash", "-c"]

# List available recipes
default:
    @just --list

# Build the project (sdist + wheel)
build:
    uv build

# Run tests
test:
    uv run pytest

# Run the project (smoke check — there's no app entrypoint yet)
run:
    uv run python -c "import hypothesis_swarm; print(hypothesis_swarm.__version__)"

# Format source code
fmt:
    ruff format .

# Lint / static analysis
lint:
    ruff check .
    uv run pyright src tests

# Remove build artifacts
clean:
    rm -rf dist/ build/ __pycache__ .pytest_cache .venv .ruff_cache .mypy_cache
