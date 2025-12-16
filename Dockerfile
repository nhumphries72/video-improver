FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["streamlit", "run", "decibel-sorter.py", "--server.maxUploadSize=1024", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]