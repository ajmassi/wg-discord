.PHONY: format, isort, flake8, black, bandit, test
format: isort flake8 black bandit

isort:
	$(info ---------- ISORT ----------)
	poetry run isort .

flake8:
	$(info ---------- FLAKE8 ----------)
	poetry run flake8 . 

black:
	$(info ---------- BLACK ----------)
	poetry run black .

bandit:
	$(info ---------- BANDIT ----------)
	poetry run bandit -c "pyproject.toml" --recursive .
