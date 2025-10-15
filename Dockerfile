# Base image
FROM python:3.11-slim

# Create non-root user
RUN useradd -m toruser

# Install Tor and dependencies (optimized)
RUN apt-get update && apt-get install -y \
    tor \
    libffi-dev \
    libssl-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Ensure /app and /app/data are writable by toruser
RUN mkdir -p /app/data && chown -R toruser:toruser /app/data

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Copy torrc to system path
RUN mkdir -p /etc/tor && cp torrc /etc/tor/torrc && chown -R toruser /etc/tor

# Switch to non-root user
USER toruser

# Expose Tor ports
EXPOSE 9050 9051

# Start Tor and run crawler
CMD ["sh", "-c", "tor & echo 'Waiting for Tor to bootstrap...' && sleep 15 && python crawler/crawler.py"]
