ARG PYTHON_VERSION=3.13
# Use Python slim image as base
FROM python:${PYTHON_VERSION}-slim

ARG UV_VERSION=0.7.18
# Install system dependencies for OpenCV and other packages
RUN apt-get update && apt-get install -y \
    ffmpeg curl && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install uv with pinned version
RUN pip install uv==${UV_VERSION}

# Copy only the files needed for installing dependencies
COPY apps/server/pyproject.toml apps/server/uv.lock ./

# Install dependencies
RUN uv sync --no-dev

# Copy the application source code
COPY apps/server/src ./src

# Expose the backend port
EXPOSE 8080

# Run the backend
CMD ["uv", "run", "fastapi", "run", "--app", "app", "src/main.py", "--port", "8080"] 