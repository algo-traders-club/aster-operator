FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY aster-operator/ ./aster-operator/
COPY main.py test_mvp.py monitor.py ./

# Install dependencies
RUN uv sync --frozen

# Create logs directory
RUN mkdir -p logs

# Expose port for monitoring (optional)
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["uv", "run", "python", "main.py"]
