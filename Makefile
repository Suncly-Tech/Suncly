# Thin wrapper for macOS and Linux. Windows users run `python tasks.py <task>`.
PYTHON ?= python

.PHONY: install lint format typecheck test check

install:
	$(PYTHON) tasks.py install

lint:
	$(PYTHON) tasks.py lint

format:
	$(PYTHON) tasks.py format

typecheck:
	$(PYTHON) tasks.py typecheck

test:
	$(PYTHON) tasks.py test

check:
	$(PYTHON) tasks.py check
