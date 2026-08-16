FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for OpenCV (headless) and psycopg
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
       libglib2.0-0 \
       libsm6 \
       libxrender1 \
       libxext6 \
       libgl1-mesa-glx \
       gcc \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["sh", "-c", "python -m app.db_init && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
