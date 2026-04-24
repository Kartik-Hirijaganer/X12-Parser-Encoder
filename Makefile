PYTHON ?= python3
DOCKER_COMPOSE ?= docker compose
AWS_REGION ?= us-east-2
AWS_ACCOUNT_ID ?= $(shell aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 306980977180)
APP_NAME ?= x12-parser-encoder
ENV ?=
LAMBDA_ARCHITECTURE ?= x86_64
LAMBDA_VERSION_KEEP_COUNT ?= 3
LAMBDA_ZIP_S3_KEY ?=
TERRAFORM ?= terraform
AWS ?= aws

LIB_DIR := packages/x12-edi-tools
API_DIR := apps/api
WEB_DIR := apps/web
TF_DIR := infra/terraform
VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
VENV_BIN := $(CURDIR)/$(VENV_DIR)/bin
WEB_UI_URL := http://localhost:5173
API_URL := http://localhost:8000
S3_BUCKET ?= $(APP_NAME)-web-$(AWS_ACCOUNT_ID)-$(AWS_REGION)
TFSTATE_BUCKET ?= $(APP_NAME)-tfstate-$(AWS_ACCOUNT_ID)-$(AWS_REGION)
GIT_SHA := $(shell git rev-parse HEAD 2>/dev/null || echo local)
LAMBDA_ARTIFACT_KEY ?= lambda-artifacts/$(ENV)/$(GIT_SHA).zip

.PHONY: install lint typecheck format test test-lib test-api test-web coverage-lib coverage-api coverage-web coverage build-lib check-version-sync check-oss check-hygiene design-lint docs docs-regenerate docs-check rebuild require-env lambda-package lambda-prune-versions terraform-plan terraform-apply deploy deploy-invalidate clean

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

design-lint:
	cd $(WEB_DIR) && npm run lint:design

docs: $(VENV_PYTHON)
	PATH="$(VENV_BIN):$$PATH" $(VENV_PYTHON) -m openapi_spec_validator docs/api/openapi.yaml
	@if command -v mmdc >/dev/null 2>&1; then \
		find docs/diagrams -name '*.mmd' -exec sh -c 'for diagram do out="$${diagram%.mmd}.svg"; mmdc -i "$$diagram" -o "$$out"; echo "Rendered $$out"; done' sh {} +; \
	else \
		echo "Mermaid CLI ('mmdc') not installed; skipping Mermaid SVG render."; \
	fi
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

docs-regenerate: $(VENV_PYTHON)
	PATH="$(VENV_BIN):$$PATH" $(VENV_PYTHON) scripts/docs_regenerate.py

docs-check: $(VENV_PYTHON)
	@set -e; \
	tmpdir="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	mkdir -p "$$tmpdir/repo"; \
	rsync -a \
		--exclude .git \
		--exclude .venv \
		--exclude node_modules \
		--exclude dist \
		--exclude build \
		--exclude .pytest_cache \
		--exclude .mypy_cache \
		--exclude .ruff_cache \
		./ "$$tmpdir/repo/"; \
	PYTHONPATH="$$tmpdir/repo/apps/api:$$tmpdir/repo/packages/x12-edi-tools/src" \
		PATH="$(VENV_BIN):$$PATH" \
		$(VENV_PYTHON) "$$tmpdir/repo/scripts/docs_regenerate.py" --repo-root "$$tmpdir/repo"; \
	diff_status=0; \
	diff -ru README.md "$$tmpdir/repo/README.md" || diff_status=1; \
	diff -ru docs "$$tmpdir/repo/docs" || diff_status=1; \
	exit "$$diff_status"

rebuild:
	$(DOCKER_COMPOSE) down --remove-orphans
	$(DOCKER_COMPOSE) up --build -d
	@printf "\nApplication is running.\nWeb UI: %s\nAPI: %s\n\n" "$(WEB_UI_URL)" "$(API_URL)"

require-env:
	@if [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ]; then \
		echo "ENV must be set to staging or production."; \
		exit 1; \
	fi

lambda-package:
	LAMBDA_ARCHITECTURE="$(LAMBDA_ARCHITECTURE)" bash scripts/package_lambda.sh

lambda-prune-versions: require-env
	FUNCTION_NAME="$$($(TERRAFORM) -chdir="$(TF_DIR)/environments/$(ENV)" output -raw lambda_function_name)" && \
	AWS="$(AWS)" AWS_REGION="$(AWS_REGION)" LAMBDA_VERSION_KEEP_COUNT="$(LAMBDA_VERSION_KEEP_COUNT)" \
		bash scripts/prune_lambda_versions.sh "$${FUNCTION_NAME}"

terraform-plan: require-env lambda-package
	$(AWS) s3 cp build/lambda.zip "s3://$(TFSTATE_BUCKET)/$(LAMBDA_ARTIFACT_KEY)"
	$(TERRAFORM) -chdir="$(TF_DIR)/environments/$(ENV)" init -backend-config=backend.hcl
	$(TERRAFORM) -chdir="$(TF_DIR)/environments/$(ENV)" plan \
		-var "lambda_zip_s3_bucket=$(TFSTATE_BUCKET)" \
		-var "lambda_zip_s3_key=$(LAMBDA_ARTIFACT_KEY)" \
		-var-file=terraform.tfvars

terraform-apply: require-env lambda-package
	$(AWS) s3 cp build/lambda.zip "s3://$(TFSTATE_BUCKET)/$(LAMBDA_ARTIFACT_KEY)"
	$(TERRAFORM) -chdir="$(TF_DIR)/environments/$(ENV)" init -backend-config=backend.hcl
	$(TERRAFORM) -chdir="$(TF_DIR)/environments/$(ENV)" apply -auto-approve \
		-var "lambda_zip_s3_bucket=$(TFSTATE_BUCKET)" \
		-var "lambda_zip_s3_key=$(LAMBDA_ARTIFACT_KEY)" \
		-var-file=terraform.tfvars
	$(MAKE) lambda-prune-versions ENV="$(ENV)" AWS_REGION="$(AWS_REGION)" LAMBDA_VERSION_KEEP_COUNT="$(LAMBDA_VERSION_KEEP_COUNT)"

deploy: require-env
	@echo "make deploy now deploys via Lambda+CloudFront. ENV=$(ENV). Ctrl-C to abort."
	@sleep 3
	cd $(WEB_DIR) && npm run build
	$(MAKE) terraform-apply ENV="$(ENV)" LAMBDA_ARCHITECTURE="$(LAMBDA_ARCHITECTURE)" AWS_ACCOUNT_ID="$(AWS_ACCOUNT_ID)" AWS_REGION="$(AWS_REGION)" APP_NAME="$(APP_NAME)"
	SPA_BUCKET="$$($(TERRAFORM) -chdir="$(TF_DIR)/environments/$(ENV)" output -raw spa_bucket_name)" && \
	$(AWS) s3 sync "$(WEB_DIR)/dist/" "s3://$${SPA_BUCKET}/" --delete
	$(MAKE) deploy-invalidate ENV="$(ENV)"

deploy-invalidate: require-env
	DISTRIBUTION_ID="$$($(TERRAFORM) -chdir="$(TF_DIR)/environments/$(ENV)" output -raw cloudfront_distribution_id)" && \
	$(AWS) cloudfront create-invalidation --distribution-id "$${DISTRIBUTION_ID}" --paths "/*"

clean:
	rm -rf $(VENV_DIR)
	rm -rf $(LIB_DIR)/.pytest_cache $(LIB_DIR)/.mypy_cache $(LIB_DIR)/.ruff_cache $(LIB_DIR)/dist $(LIB_DIR)/build
	rm -rf $(API_DIR)/.pytest_cache $(API_DIR)/.mypy_cache $(API_DIR)/.ruff_cache $(API_DIR)/dist $(API_DIR)/build
	rm -rf $(WEB_DIR)/node_modules $(WEB_DIR)/dist $(WEB_DIR)/coverage
