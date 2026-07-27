FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY knowledge ./knowledge
COPY fixtures ./fixtures
COPY prompts ./prompts

ENV PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000

EXPOSE 8000

# Compatible with Render: uvicorn app:app --host 0.0.0.0 --port $PORT
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
