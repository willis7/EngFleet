FROM ghcr.io/astral-sh/uv:debian-slim

# Set the working directory in the container
WORKDIR /app

# --- Dependency Installation ---
COPY ../../pyproject.toml /app/pyproject.toml
RUN uv sync --locked

# --- Application Code ---
COPY . /app

# --- Environment ---
ENV PYTHONPATH=/app

# Make port 8080 available to the world outside this container
# Cloud Run uses the PORT env var, but EXPOSE is good practice.
EXPOSE 8080

# --- Run the application ---
CMD ["uv", "run", "mcp_server.py"]