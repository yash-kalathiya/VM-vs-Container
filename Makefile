.PHONY: lint test build run docker-build docker-run docker-push

# Auto-detect requirements and dockerfile if not using sample_app

REQS := $(shell if [ -f sample_app/requirements.txt ]; then echo sample_app/requirements.txt; else ls -1 **/requirements.txt 2>/dev/null | head -n1; fi)
DOCKERFILE := $(shell if [ -f sample_app/Dockerfile ]; then echo sample_app/Dockerfile; else ls -1 **/Dockerfile 2>/dev/null | head -n1; fi)

lint:
	@python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
	@python3 -m pip install ruff >/dev/null 2>&1 || true
	@ruff check . || true

test:
	@python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
	@if [ -n "$(REQS)" ]; then python3 -m pip install -r "$(REQS)" >/dev/null 2>&1 || true; fi
	@if ls -d sample_app/tests 2>/dev/null 1>/dev/null || ls -d tests 2>/dev/null 1>/dev/null; then \
		pytest -q --maxfail=1 --disable-warnings --junitxml=pytest-report.xml || exit 1; \
	else \
		echo "No tests found; skipping."; \
	fi

build:
	@echo "No additional build step."

run:
	@echo "Trying to run a FastAPI app if available..."
	@uvicorn sample_app.app:app --host 0.0.0.0 --port 8000 || echo "Define your own run command for your app."

docker-build:
	@if [ -n "$(DOCKERFILE)" ]; then \
		docker build -t vm-vs-container:local -f "$(DOCKERFILE)" .; \
	else \
		echo "No Dockerfile found. If you have an app, add a Dockerfile or enable sample_app."; exit 1; \
	fi

docker-run:
	@docker run --rm -p 8000:8000 vm-vs-container:local || echo "Container failed to run (expose a port or adjust command)."

docker-push:
	@echo "Handled by GitHub Actions CD workflow."
