FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for OpenCV and psycopg
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
       libgl1 \
       libglib2.0-0 \
       libxcb1 \
       libx11-6 \
       gcc \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.py ./

EXPOSE 8000

CMD ["python", "run.py"]
