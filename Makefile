.PHONY: install run test eval lint docker verify prepublish browser
install:
	python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
run:
	.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
test:
	.venv/bin/python -m pytest -q
eval:
	.venv/bin/python -m pytest -q tests/test_eval.py
docker:
	docker compose up --build -d

verify:
	bash scripts/verify.sh
prepublish:
	bash scripts/prepublish.sh
browser:
	.venv/bin/python -m scripts.smoke_browser
