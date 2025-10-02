# Base image
FROM python:3.11-slim

# Install system dependencies + Tor
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    cmake \
    git \
    tor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Upgrade pip and install dependencies (including SOCKS support)
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Start Tor + run your script
CMD ["sh", "-c", "tor & sleep 15 && python crawler/test_tor.py"]
