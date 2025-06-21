# Makefile for easy development workflows.
# See development.md for docs.
# Note GitHub Actions call uv directly, not this Makefile.

.DEFAULT_GOAL := default

.PHONY: default install lint test test-full upgrade build clean agent-rules

default: agent-rules install lint test 

install:
	uv sync --all-extras --dev

lint:
	uv run python devtools/lint.py

test:
	uv run pytest

test-full:
	ENABLE_TESTS_ONLINE=1 ENABLE_TESTS_INTEGRATION=1 uv run pytest

run: install lint test
	uv run kash

upgrade:
	uv sync --upgrade --all-extras --dev

build:
	uv build

agent-rules: CLAUDE.md AGENTS.md

# Use .cursor/rules for sources of rules.
# Create Claude and Codex rules from these.
CLAUDE.md: .cursor/rules/general.mdc .cursor/rules/python.mdc
	cat .cursor/rules/general.mdc .cursor/rules/python.mdc > CLAUDE.md

AGENTS.md: .cursor/rules/general.mdc .cursor/rules/python.mdc
	cat .cursor/rules/general.mdc .cursor/rules/python.mdc > AGENTS.md

clean:
	-rm -rf dist/
	-rm -rf *.egg-info/
	-rm -rf .pytest_cache/
	-rm -rf .mypy_cache/
	-rm -rf .venv/
	-rm -rf CLAUDE.md AGENTS.md
	-find . -type d -name "__pycache__" -exec rm -rf {} +
