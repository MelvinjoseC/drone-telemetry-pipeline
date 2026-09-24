.PHONY: help install lint format test coverage simulate benchmark health-check tf-init tf-fmt tf-validate tf-plan local-up local-down clean

PYTHON ?= python

help:
	@echo "Drone Telemetry Pipeline — Developer Commands:"
	@echo "  make install        Install development and pipeline dependencies"
	@echo "  make lint           Check code quality with Ruff"
	@echo "  make format         Auto-format code with Ruff"
	@echo "  make test           Run unit test suite"
	@echo "  make coverage       Run unit tests with coverage reporting"
	@echo "  make simulate       Run dry-run fleet simulator"
	@echo "  make benchmark      Execute ingestion throughput benchmark"
	@echo "  make health-check   Run pipeline diagnostics"
	@echo "  make tf-init        Initialize Terraform provider plugins"
	@echo "  make tf-fmt         Format Terraform HCL configurations"
	@echo "  make tf-validate    Validate Terraform syntax"
	@echo "  make tf-plan        Generate Terraform infrastructure plan"
	@echo "  make local-up       Start LocalStack & simulator with Docker Compose"
	@echo "  make local-down     Stop local development containers"
	@echo "  make clean          Clean temporary files and test caches"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r device-simulator/requirements.txt
	$(PYTHON) -m pip install ruff coverage pre-commit

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format:
	$(PYTHON) -m ruff format .

test:
	$(PYTHON) -m unittest discover -s tests

coverage:
	coverage run -m unittest discover -s tests
	coverage report

simulate:
	$(PYTHON) device-simulator/drone_publisher.py --dry-run --fleet-size 2 --max-ticks 10

benchmark:
	$(PYTHON) scripts/benchmark_publisher.py --records 5000 --threads 4

health-check:
	$(PYTHON) scripts/health_check.py

tf-init:
	terraform -chdir=infrastructure/terraform init -backend=false

tf-fmt:
	terraform fmt infrastructure/terraform

tf-validate:
	terraform -chdir=infrastructure/terraform validate

tf-plan:
	terraform -chdir=infrastructure/terraform plan

local-up:
	docker compose up -d

local-down:
	docker compose down

clean:
	rm -rf .coverage .coverage.* htmlcov .ruff_cache __pycache__ */__pycache__ tests/__pycache__
