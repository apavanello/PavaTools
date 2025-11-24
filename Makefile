.PHONY: run clean

run:
	uv run pavatools

clean:
	rm -rf .venv
	rm -rf src/pavatools.egg-info
	rm -rf dist
	rm -rf build
