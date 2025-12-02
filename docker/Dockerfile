# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Prevent Python from writing .pyc files and enable real-time logging
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# First, copy just the dependency file to leverage Docker cache
COPY ./pyproject.toml /app/

# Install project dependencies (including the MCP SDK for your client)
RUN pip install --no-cache-dir .

# Copy the rest of your application code
COPY ./src/ /app/src/

# Create a non-root user to run the application (security best practice)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Default command (can be overridden when running the container)
CMD ["python", "-m", "src.cli.main"]