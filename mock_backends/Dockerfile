FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ ./src/
COPY seed_data/ ./seed_data/

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
