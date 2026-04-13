PYTHON ?= python3

LIB_DIR := packages/x12-edi-tools
API_DIR := apps/api
WEB_DIR := apps/web
VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
VENV_BIN := $(CURDIR)/$(VENV_DIR)/bin

.PHONY: install lint typecheck format test test-lib test-api test-web coverage-lib coverage-api coverage-web coverage build-lib check-version-sync check-oss clean

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV_DIR)

install: $(VENV_PYTHON)
	$(VENV_PIP) install -e "$(LIB_DIR)[dev]"
	$(VENV_PIP) install -e "$(API_DIR)[dev]"
	cd $(WEB_DIR) && npm install

lint: $(VENV_PYTHON)
	cd $(LIB_DIR) && PATH="$(VENV_BIN):$$PATH" ruff format --check .
	cd $(LIB_DIR) && PATH="$(VENV_BIN):$$PATH" ruff check .
	cd $(API_DIR) && PATH="$(VENV_BIN):$$PATH" ruff format --check .
	cd $(API_DIR) && PATH="$(VENV_BIN):$$PATH" ruff check .
	cd $(WEB_DIR) && npm run lint

typecheck: $(VENV_PYTHON)
	cd $(LIB_DIR) && PATH="$(VENV_BIN):$$PATH" mypy src
	cd $(API_DIR) && PATH="$(VENV_BIN):$$PATH" mypy app
	cd $(WEB_DIR) && npm run typecheck

format: $(VENV_PYTHON)
	cd $(LIB_DIR) && PATH="$(VENV_BIN):$$PATH" ruff format .
	cd $(LIB_DIR) && PATH="$(VENV_BIN):$$PATH" ruff check --fix .
	cd $(API_DIR) && PATH="$(VENV_BIN):$$PATH" ruff format .
	cd $(API_DIR) && PATH="$(VENV_BIN):$$PATH" ruff check --fix .
	cd $(WEB_DIR) && npm run lint -- --fix

test: test-lib test-api test-web

test-lib: $(VENV_PYTHON)
	cd $(LIB_DIR) && PATH="$(VENV_BIN):$$PATH" pytest

test-api: $(VENV_PYTHON)
	cd $(API_DIR) && PATH="$(VENV_BIN):$$PATH" pytest

test-web:
	cd $(WEB_DIR) && npm run test -- --run

coverage-lib: $(VENV_PYTHON)
	cd $(LIB_DIR) && PATH="$(VENV_BIN):$$PATH" pytest --cov=src/x12_edi_tools --cov-report=term-missing --cov-report=xml --cov-fail-under=90

coverage-api: $(VENV_PYTHON)
	cd $(API_DIR) && PATH="$(VENV_BIN):$$PATH" pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=85

coverage-web:
	cd $(WEB_DIR) && npm run test:coverage

coverage: coverage-lib coverage-api coverage-web

build-lib: $(VENV_PYTHON)
	cd $(LIB_DIR) && PATH="$(VENV_BIN):$$PATH" python -m build

check-version-sync: $(VENV_PYTHON)
	PATH="$(VENV_BIN):$$PATH" $(VENV_PYTHON) scripts/check_version_sync.py

check-oss: $(VENV_PYTHON)
	PATH="$(VENV_BIN):$$PATH" $(VENV_PYTHON) scripts/check_no_proprietary_content.py

clean:
	rm -rf $(VENV_DIR)
	rm -rf $(LIB_DIR)/.pytest_cache $(LIB_DIR)/.mypy_cache $(LIB_DIR)/.ruff_cache $(LIB_DIR)/dist $(LIB_DIR)/build
	rm -rf $(API_DIR)/.pytest_cache $(API_DIR)/.mypy_cache $(API_DIR)/.ruff_cache $(API_DIR)/dist $(API_DIR)/build
	rm -rf $(WEB_DIR)/node_modules $(WEB_DIR)/dist $(WEB_DIR)/coverage
