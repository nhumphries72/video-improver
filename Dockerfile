FROM python:3.11-slim

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["/bin/bash", "-c", "streamlit run decibel_sorter.py --server.maxUploadSize 1024 --server.port $PORT --server.address 0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false"]