MODULE := ptcmd
MODULE_PATH := src/${MODULE}
PIP_MODULE := ptcmd

all: clean test lint build_dist
refresh: clean develop test lint

.PHONY: run
run:
	python -m ${MODULE}

.PHONY: build_dist
build_dist:
	python -m build

.PHONY: install
install:
	pip install .

.PHONY: install_all
install_all:
	pip install .[all]

.PHONY: develop
develop:
	pip install -e .[dev]

.PHONY: lint
lint:
	ruff check ${MODULE_PATH} tests/ --fix

.PHONY: docs
docs:
	mkdocs build --clean

.PHONY: test
test:
	pytest

.PHONY: coverage_result
coverage_result:
	coverage run --source ${MODULE_PATH} --parallel-mode -m pytest

.PHONY: coverage
coverage: coverage_result
	coverage combine
	coverage html -i

.PHONY: uninstall
uninstall:
	pip uninstall ${PIP_MODULE} -y || true

.PHONY: clean
clean:
	rm -rf build
	rm -rf dist
	rm -rf ${PIP_MODULE}.egg-info
