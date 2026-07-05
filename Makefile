# CATHEDRAL ARKHE v5.1 — Makefile
# Arquiteto: ORCID 0009-0005-2697-4668

.PHONY: test test-v5 test-v5_1 lint clean demo demo-v5_1

test:
	python -m pytest tests/ -v --tb=short

test-v5:
	python -m pytest tests/test_orchestrator_v5.py -v --tb=short

test-v5_1:
	python -m pytest tests/test_orchestrator_v5_1.py -v --tb=short

lint:
	python -m py_compile cathedral_orchestrator_v5.py
	python -m py_compile cathedral_v5_1.py

clean:
	rm -rf __pycache__ .pytest_cache
	rm -f *.pyc *.jsonl

demo:
	python cathedral_orchestrator_v5.py

demo-v5_1:
	python cathedral_v5_1.py
