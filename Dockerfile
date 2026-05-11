# Slim runtime image for the protea-contracts library.
#
# This package is the contract surface (ABCs, payload schemas, feature
# registry, compute_schema_sha helper). It must stay importable in
# downstream consumers without the platform stack, so the image carries
# only pydantic / numpy / pyarrow.

FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir poetry==2.1.0

COPY pyproject.toml README.md ./
COPY poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

COPY src/ ./src/
RUN poetry install --only main --no-interaction --no-ansi

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY src/ ./src/

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Library image: default entry is the Python REPL with protea_contracts
# importable. Override CMD to run module entrypoints from downstream.
CMD ["python", "-c", "import protea_contracts; print('protea-contracts', protea_contracts.__name__, 'ready')"]
