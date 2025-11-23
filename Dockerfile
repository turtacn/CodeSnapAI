# Stage 1: Builder
FROM python:3.10-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y git build-essential && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-dev

# Stage 2: Runner
FROM python:3.10-slim
WORKDIR /workspace
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . /app
RUN pip install /app  # Install current package
ENTRYPOINT ["codesage"]
