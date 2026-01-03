FROM python:3.9-slim

# Install system dependencies
# imapsync: The core tool (installing from Debian repositories for stability)
# procps: For process management
RUN apt-get update && apt-get install -y \
    imapsync \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole project
COPY . .

# Create logs directory
RUN mkdir -p backend/logs && chmod 777 backend/logs

# Expose the API port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
