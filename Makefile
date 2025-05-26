.PHONY: dev dev-d dev-watch prod build build-dev clean clean-all logs logs-all shell db-shell redis-shell migrate test lint format typecheck help
.PHONY: create-migration migration-history migration-current reset-db backup-db restore-db
.PHONY: test-unit test-integration test-cov test-fast test-auth test-crud test-api install-deps update-deps

# =============================================================================
# Основные команды разработки
# =============================================================================

dev:
	docker compose -f docker-compose.dev.yml up --build

dev-d:
	docker compose -f docker-compose.dev.yml up --build -d

dev-watch:
	docker compose -f docker-compose.dev.yml watch

prod:
	docker compose up --build -d

# Запуск без пересборки
up:
	docker compose -f docker-compose.dev.yml up

down:
	docker compose -f docker-compose.dev.yml down

restart:
	docker compose -f docker-compose.dev.yml restart

# =============================================================================
# Сборка
# =============================================================================

build:
	docker compose -f docker-compose.dev.yml build

build-dev:
	docker compose -f docker-compose.dev.yml build --no-cache

build-prod:
	docker compose build

# =============================================================================
# Очистка
# =============================================================================

clean:
	docker compose -f docker-compose.dev.yml down -v
	docker compose down -v
	docker system prune -f

clean-all:
	docker compose -f docker-compose.dev.yml down -v --rmi all
	docker compose down -v --rmi all
	docker system prune -af
	docker volume prune -f

clean-volumes:
	docker compose -f docker-compose.dev.yml down -v
	docker volume prune -f

# =============================================================================
# Логи и мониторинг
# =============================================================================

logs:
	docker compose -f docker-compose.dev.yml logs -f web

logs-all:
	docker compose -f docker-compose.dev.yml logs -f

logs-db:
	docker compose -f docker-compose.dev.yml logs -f db

logs-redis:
	docker compose -f docker-compose.dev.yml logs -f redis

status:
	docker compose -f docker-compose.dev.yml ps

# =============================================================================
# Подключения к контейнерам
# =============================================================================

shell:
	docker compose -f docker-compose.dev.yml exec web bash

db-shell:
	docker compose -f docker-compose.dev.yml exec db psql -U gemup_user -d gemup_marketplace

redis-shell:
	docker compose -f docker-compose.dev.yml exec redis redis-cli

# =============================================================================
# Миграции базы данных
# =============================================================================

migrate:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/alembic upgrade head

create-migration:
	@if [ -z "$(msg)" ]; then \
		echo "❌ Укажите сообщение: make create-migration msg='описание'"; \
		exit 1; \
	fi
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/alembic revision --autogenerate -m "$(msg)"

migration-history:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/alembic history

migration-current:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/alembic current

downgrade:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/alembic downgrade -1

# Сброс базы данных (ОСТОРОЖНО!)
reset-db:
	@echo "⚠️  ВНИМАНИЕ: Это удалит ВСЕ данные в базе!"
	@read -p "Вы уверены? (y/N): " confirm && [ "$$confirm" = "y" ]
	docker compose -f docker-compose.dev.yml down -v
	docker volume rm $$(docker volume ls -q | grep postgres) 2>/dev/null || true
	docker compose -f docker-compose.dev.yml up -d db
	sleep 10
	docker compose -f docker-compose.dev.yml up -d web

# =============================================================================
# Резервное копирование
# =============================================================================

backup-db:
	@mkdir -p ./backups
	docker compose -f docker-compose.dev.yml exec db pg_dump -U gemup_user gemup_marketplace > ./backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Бэкап создан в ./backups/"

restore-db:
	@if [ -z "$(file)" ]; then \
		echo "❌ Укажите файл бэкапа: make restore-db file=./backups/backup_20240101_120000.sql"; \
		exit 1; \
	fi
	@if [ ! -f "$(file)" ]; then \
		echo "❌ Файл $(file) не найден"; \
		exit 1; \
	fi
	docker compose -f docker-compose.dev.yml exec -T db psql -U gemup_user -d gemup_marketplace < $(file)
	@echo "✅ База данных восстановлена из $(file)"

# =============================================================================
# Качество кода
# =============================================================================

lint:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/ruff check .

lint-fix:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/ruff check . --fix

format:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/ruff format .

typecheck:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/mypy app/

security:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/bandit -r app/

check-all: lint typecheck security
	@echo "✅ Все проверки качества кода завершены"

# =============================================================================
# Тестирование
# =============================================================================

test:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/pytest

test-unit:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/pytest tests/unit/ -v

test-integration:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/pytest tests/integration/ -v

test-cov:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/pytest --cov=app --cov-report=html --cov-report=term

test-fast:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/pytest -m "not slow" -x

test-auth:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/pytest -m auth -v

test-crud:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/pytest -m crud -v

test-api:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/pytest -m api -v

test-watch:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/pytest-watch

test-debug:
	docker compose -f docker-compose.dev.yml exec web /app/.venv/bin/pytest -v -s --pdb

# =============================================================================
# Зависимости
# =============================================================================

install-deps:
	docker compose -f docker-compose.dev.yml exec web uv sync

update-deps:
	docker compose -f docker-compose.dev.yml exec web uv lock --upgrade

export-requirements:
	docker compose -f docker-compose.dev.yml exec web uv export --format requirements-txt --output-file requirements.txt

# =============================================================================
# Утилиты
# =============================================================================

docs:
	@echo "🌐 Открываем Swagger UI..."
	@command -v open >/dev/null 2>&1 && open http://localhost:8000/docs || echo "Откройте http://localhost:8000/docs в браузере"

redoc:
	@echo "🌐 Открываем ReDoc..."
	@command -v open >/dev/null 2>&1 && open http://localhost:8000/redoc || echo "Откройте http://localhost:8000/redoc в браузере"

health:
	@echo "🔍 Проверка состояния сервисов..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ API недоступно"