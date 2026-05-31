FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OLLAMA_BASE_URL=http://ollama:11434

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    curl \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt /app/requirements.txt

# Install Python deps at build time
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    python3 -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.3.1+cpu && \
    python3 -m pip install -r requirements.txt && \
    touch /.requirements_installed

# Copy application source
COPY . /app

RUN mkdir -p /app/tmp /app/data && chmod -R 777 /app/tmp /app/data

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "./start.sh"]
