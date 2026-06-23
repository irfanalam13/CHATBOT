.PHONY: install dev up down init seed test lint worker

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

up:
	docker compose up --build

down:
	docker compose down

init:
	python scripts/init_db.py

seed:
	python scripts/seed.py

worker:
	celery -A app.workers.celery_app.celery_app worker --loglevel=info -Q ingestion,default

test:
	pytest --cov=app --cov-report=term-missing

lint:
	ruff check app tests
