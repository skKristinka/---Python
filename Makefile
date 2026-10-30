.PHONY: install run test integration lint pylint dev load
install:
	pip install -r requirements.txt
run:
	python -m src.main
test:
	pytest tests/ -v
integration:
	pytest tests/test_integration.py -v
lint:
	flake8 src/ tests/ scripts/
pylint:
	pylint --rcfile=.pylintrc src/ scripts/
	pylint --rcfile=.pylintrc --disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,redefined-outer-name,unused-argument,import-outside-toplevel,duplicate-code,protected-access tests/
dev:
	python -X dev -m pytest tests/ -v
load:
	python -m scripts.load_test http://localhost:8080/ -n 100
