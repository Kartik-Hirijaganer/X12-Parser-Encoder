PYTHON ?= python3
DOCKER_COMPOSE ?= docker compose
AWS_REGION ?= us-east-2
AWS_ACCOUNT_ID ?= 306980977180
APP_NAME ?= x12-parser-encoder

LIB_DIR := packages/x12-edi-tools
API_DIR := apps/api
WEB_DIR := apps/web
VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
VENV_BIN := $(CURDIR)/$(VENV_DIR)/bin
WEB_UI_URL := http://localhost:5173
API_URL := http://localhost:8000
S3_BUCKET ?= $(APP_NAME)-web-$(AWS_ACCOUNT_ID)-$(AWS_REGION)
ECR_REPOSITORY ?= $(APP_NAME)-api
APP_RUNNER_SERVICE ?= $(APP_NAME)-api
APP_RUNNER_ECR_ACCESS_ROLE ?= $(APP_NAME)-apprunner-ecr-access

.PHONY: install lint typecheck format test test-lib test-api test-web coverage-lib coverage-api coverage-web coverage build-lib check-version-sync check-oss check-hygiene docs rebuild deploy clean

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
	cd $(LIB_DIR) && PATH="$(VENV_BIN):$$PATH" pytest --cov=src/x12_edi_tools --cov-report=term-missing --cov-report=xml --cov-fail-under=95

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

check-hygiene: $(VENV_PYTHON)
	PATH="$(VENV_BIN):$$PATH" $(VENV_PYTHON) scripts/check_repo_hygiene.py

docs: $(VENV_PYTHON)
	PATH="$(VENV_BIN):$$PATH" $(VENV_PYTHON) -m openapi_spec_validator docs/api/openapi.yaml
	@if [ ! -f docs/erd.er ]; then \
		echo "docs/erd.er not present; skipping ERD regeneration"; \
	elif ! command -v dot >/dev/null 2>&1; then \
		echo "graphviz ('dot') binary not installed; skipping ERD render. Install with 'brew install graphviz' or 'apt-get install graphviz'."; \
	elif ! PATH="$(VENV_BIN):$$PATH" $(VENV_PYTHON) -c "import graphviz" >/dev/null 2>&1 && \
	     ! PATH="$(VENV_BIN):$$PATH" $(VENV_PYTHON) -c "import pygraphviz" >/dev/null 2>&1; then \
		echo "Python 'graphviz' or 'pygraphviz' not installed in venv; skipping ERD render. Run 'make install' to pick up dev extras."; \
	else \
		PATH="$(VENV_BIN):$$PATH" eralchemy -i docs/erd.er -o docs/erd.svg && \
		echo "Regenerated docs/erd.svg"; \
	fi

rebuild:
	$(DOCKER_COMPOSE) down --remove-orphans
	$(DOCKER_COMPOSE) up --build -d
	@printf "\nApplication is running.\nWeb UI: %s\nAPI: %s\n\n" "$(WEB_UI_URL)" "$(API_URL)"

deploy:
	AWS_REGION="$(AWS_REGION)" \
	AWS_ACCOUNT_ID="$(AWS_ACCOUNT_ID)" \
	APP_NAME="$(APP_NAME)" \
	S3_BUCKET="$(S3_BUCKET)" \
	ECR_REPOSITORY="$(ECR_REPOSITORY)" \
	APP_RUNNER_SERVICE="$(APP_RUNNER_SERVICE)" \
	APP_RUNNER_ECR_ACCESS_ROLE="$(APP_RUNNER_ECR_ACCESS_ROLE)" \
	bash scripts/deploy_aws.sh

clean:
	rm -rf $(VENV_DIR)
	rm -rf $(LIB_DIR)/.pytest_cache $(LIB_DIR)/.mypy_cache $(LIB_DIR)/.ruff_cache $(LIB_DIR)/dist $(LIB_DIR)/build
	rm -rf $(API_DIR)/.pytest_cache $(API_DIR)/.mypy_cache $(API_DIR)/.ruff_cache $(API_DIR)/dist $(API_DIR)/build
	rm -rf $(WEB_DIR)/node_modules $(WEB_DIR)/dist $(WEB_DIR)/coverage
