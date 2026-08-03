.PHONY: check lint type test bench demo setup

# Phase 0 quality gates
check: lint type test
	@echo "=== make check: ALL GATES PASS ==="

lint:
	ruff check .

type:
	mypy core memory funnel llm_bridge orchestrator

test:
	python -m pytest -q

bench:
	python -m benchmarks.bench_core

demo:
	python demo.py

setup:
	bash setup.sh