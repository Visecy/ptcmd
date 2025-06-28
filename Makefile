.PHONY: run install install_all refresh uninstall develop build_dist test coverage clean

MODULE := ptcmd
MODULE_PATH := src/${MODULE}
PIP_MODULE := ptcmd

all: clean test lint build_dist
refresh: clean develop test lint

run:
	python -m ${MODULE}

build_dist:
	python -m build

install:
	pip install .

install_all:
	pip install .[all]

develop:
	pip install -e .[dev]

lint:
	ruff check ${MODULE_PATH} tests/ --fix

test:
	pytest

coverage:
	coverage run --source ${MODULE_PATH} --parallel-mode -m pytest
	coverage combine
	coverage html -i

uninstall:
	pip uninstall ${PIP_MODULE} -y || true

clean:
	rm -rf build
	rm -rf dist
	rm -rf ${PIP_MODULE}.egg-info
