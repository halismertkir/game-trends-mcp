FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Expose the port for HTTP MCP server
EXPOSE 8080

# Set default environment variables
ENV HOST=0.0.0.0
ENV PORT=8080

# Default command for HTTP mode
CMD ["python", "server.py"]