FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# opencv-python-headless only needs libglib2.0-0 (no X11/GL required)
# gcc is needed to compile psycopg binary extensions
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
       libglib2.0-0 \
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
