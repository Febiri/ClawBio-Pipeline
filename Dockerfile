# 🧬 ClawBio-Pipeline Production Docker Container
FROM python:3.10-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install essential system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    procps \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline codebase
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Default entrypoint runs pipeline in simulation mode (or override with `serve`)
ENTRYPOINT ["python", "main.py"]
CMD ["run-pipeline", "--mode", "simulation"]
