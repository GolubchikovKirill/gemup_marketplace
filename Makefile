.PHONY: dev dev-d dev-watch prod build clean logs shell db-shell migrate test lint format help

dev:
	docker compose -f docker-compose.dev.yml up --build

dev-d:
	docker compose -f docker-compose.dev.yml up --build -d

dev-watch:
	docker compose -f docker-compose.dev.yml watch

prod:
	docker compose up --build -d

build:
	docker compose -f docker-compose.dev.yml build

clean:
	docker compose -f docker-compose.dev.yml down -v
	docker compose down -v
	docker system prune -f

logs:
	docker compose -f docker-compose.dev.yml logs -f web

shell:
	docker compose -f docker-compose.dev.yml exec web bash

db-shell:
	docker compose -f docker-compose.dev.yml exec db psql -U gemup_user -d gemup_marketplace

migrate:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/alembic upgrade head

create-migration:
	@if [ -z "$(msg)" ]; then \
		echo "Укажите сообщение: make create-migration msg='описание'"; \
		exit 1; \
	fi
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/alembic revision --autogenerate -m "$(msg)"

lint:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/ruff check .

format:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/ruff format .

test:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/pytest

help:
	@echo "Доступные команды:"
	@echo "  dev          - Запуск для разработки"
	@echo "  dev-d        - Запуск для разработки в фоне"
	@echo "  dev-watch    - Запуск с hot reload"
	@echo "  prod         - Запуск для продакшена"
	@echo "  build        - Сборка образов"
	@echo "  clean        - Очистка контейнеров"
	@echo "  logs         - Просмотр логов"
	@echo "  shell        - Подключение к контейнеру"
	@echo "  db-shell     - Подключение к базе данных"
	@echo "  migrate      - Применение миграций"
	@echo "  lint         - Проверка кода"
	@echo "  test         - Запуск тестов"
