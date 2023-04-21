# syntax=docker/dockerfile:1
FROM python:3.11.2-alpine

# Install Dependencies
WORKDIR /app
RUN apk add curl wireguard-tools --no-cache
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 -
ENV PATH="/etc/poetry/bin:$PATH"

COPY src/ src/
COPY pyproject.toml .
COPY README.md .
RUN pip install . --no-cache-dir

ENTRYPOINT ["python", "-m", "wg_discord"]

# Manual Testing
# ENTRYPOINT ["tail", "-f", "/dev/null"]