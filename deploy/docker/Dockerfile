# Base image
FROM python:3.9-slim AS base

# Install dependencies including SSH client
RUN apt-get update && apt-get install -y \
    entr \
    openssh-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r ./requirements.txt 

# Expose port for the web application
EXPOSE 80

# Start both services 
CMD ["./deploy/docker/start.sh"]
# sleep
# CMD ["sleep", "infinity"]