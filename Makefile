# Docker
.PHONY: build, up, down, logs
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

# Code Quality
.PHONY: format, isort, flake8, black, bandit, test
format: isort flake8 black bandit

isort:
	$(info ---------- ISORT ----------)
	poetry run isort .

flake8:
	$(info ---------- FLAKE8 ----------)
	poetry run flake8 . --exclude=.pytest_cache,.github,.venv \
	    --count --select=B,C,E,F,W,T4,B9 --max-complexity=18 \
	    --ignore=B950,E402,E203,E266,E501,W503,F403,F401 \
	    --show-source --statistics

black:
	$(info ---------- BLACK ----------)
	poetry run black .

bandit:
	$(info ---------- BANDIT ----------)
	poetry run bandit -c "pyproject.toml" --recursive .

test:
	poetry run pytest --cov=wg_discord --cov-report=html --cov-report=term
