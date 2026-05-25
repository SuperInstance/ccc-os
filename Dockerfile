FROM python:3.12-slim

WORKDIR /app

# Install only what's needed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

# Copy application
COPY . .

# Default: run fleet status in watch mode
CMD ["python", "-m", "ccc_os", "--watch", "900"]
