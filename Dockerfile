FROM python:3.11-slim

# Set working directory
WORKDIR /

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set Python p

# Default command (will be overridden by Smithery)
CMD ["python", "-m", "server"]