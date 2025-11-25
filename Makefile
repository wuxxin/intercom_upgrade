# makefile
.DEFAULT_GOAL := help

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' | sort

check_deps:
	@echo "+ $@"
	@for tool in sox xxd; do \
	    if ! command -v $$tool > /dev/null; then \
			echo "Error: $$tool is not installed"; exit 1; \
		fi; \
	done

uv.lock: pyproject.toml check_deps
	@echo "+ $@"
	uv lock

.venv/bin/activate: uv.lock
	@echo "+ $@"
	if test -d .venv; then rm -rf .venv; fi
	uv venv

.venv/installed: .venv/bin/activate
	@echo "+++ $@"
	. .venv/bin/activate && uv sync --all-extras
	touch $@

.PHONY: buildenv
buildenv: .venv/installed ## Build python environment

.PHONY: py-clean
py-clean: ## Remove python related artifacts
	@echo "+ $@"
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type d -name '.ipynb_checkpoints' -exec rm -rf {} +
	find . -type f -name '*.py[co]' -exec rm -f {} +

.PHONY: buildenv-clean
buildenv-clean: py-clean ## Remove build environment artifacts
	@echo "+ $@"
	rm -rf .venv

sounds.h: sounds/*
	./convert-sounds.sh sounds/*

.PHONY: sounds
sounds: sounds.h ## Build sounds.h from sounds/*
	@echo "+ $@"

.PHONY: config
config: buildenv sounds ## Check correct esphome config yaml
	@echo "+ $@"
	esphome config intercom.yaml

.PHONY: compile
compile: buildenv sounds ## compile esphome config yaml
	@echo "+ $@"
	esphome compile intercom.yaml

.PHONY: docs
docs: buildenv ## rebuild wiring pdf
	@echo "+ $@"
	. .venv/bin/activate && python create_intercom_wiring.py

