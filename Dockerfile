# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock* ./

# Install dependencies with uv (no dev deps in production)
RUN uv sync --frozen --no-dev --all-extras || uv sync --no-dev --all-extras

# Copy application code
COPY . .

# Expose the port
EXPOSE 8000

# Run the application from realtime_price_agent directory
WORKDIR /app/realtime_price_agent
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

