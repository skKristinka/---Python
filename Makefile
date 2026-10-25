.PHONY: install run test integration lint
install:
	pip install -r requirements.txt
run:
	python -m src.main
test:
	pytest tests/ -v
integration:
	pytest tests/test_integration.py -v
lint:
	flake8 src/ tests/
