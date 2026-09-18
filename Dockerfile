FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY static/ ./static/
COPY scripts/ ./scripts/
COPY data/processed/ ./data/processed/
COPY data/raw/ ./data/raw/

ENV PYTHONPATH=src

RUN python scripts/run_phase1.py || echo "Pipeline skipped - data may be missing"

EXPOSE 8000

CMD ["uvicorn", "turbinetwin.api:app", "--host", "0.0.0.0", "--port", "8000"]
