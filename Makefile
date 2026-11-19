.PHONY: install dev test lint demo clean
install:
	pip install -e .
dev:
	pip install -e ".[dev]"
test:
	pytest
lint:
	ruff check src tests
demo:
	tracex --no-banner demo -o examples/demo-output
clean:
	rm -rf build dist *.egg-info .pytest_cache tracex-demo tracex-report
