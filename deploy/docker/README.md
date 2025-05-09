This guide explains how to deploy the Tofino Reservation System using either Docker Compose or plain Docker commands.

## Overview

The application consists of:
- A Flask web application for managing Tofino switch reservations
- A file watcher that automatically updates switch access when reservations change
- SSH connections to target switches to grant/revoke user access

## SSH Requirements

The container needs SSH access to the target switches. You should:

1. Generate SSH keys inside the container or mount your existing keys
2. Configure the target switches to accept these keys
3. Ensure the switches can be reached on the network

## Deployment Options

### Option 1: Docker Compose (Recommended)

Create a `docker-compose.yml` file:

```yaml
version: '3'

services:
  webapp:
    build:
      context: ..
      dockerfile: deploy/docker/Dockerfile
    ports:
      - "8080:80"
    volumes:
      - ../web:/app/web
      - ../.data:/app/web/.data
      - ~/.ssh:/root/.ssh:ro
    env_file:
      - .env
    restart: unless-stopped
```

Create a `.env` file (see [details about environment variables](#environment-variables)):

```
DEBUG=1
ADMIN_USER_ON_SWITCH=admin
SSH_RESERVATIONS_CONFIG_ON_SWITCH=/etc/ssh/reservations.conf
ENFORCE_SSH_ACCESS_RESERVATION_SCRIPT_ON_SWITCH=/usr/local/bin/enforce-ssh-access.sh
```

Deploy with:

```bash
docker compose up -d
```

### Option 2: Plain Docker with Environment File

First, create a `.env` file with your configuration:

```
DEBUG=1
ADMIN_USER_ON_SWITCH=admin
SSH_RESERVATIONS_CONFIG_ON_SWITCH=/etc/ssh/reservations.conf
ENFORCE_SSH_ACCESS_RESERVATION_SCRIPT_ON_SWITCH=/usr/local/bin/enforce-ssh-access.sh
```

Then build and run the container:

```bash
# Build the image
docker build -t tofino-rsvp-webapp -f deploy/docker/Dockerfile .

# Run the container
docker run -d \
  --name tofino-rsvp \
  -p 8080:80 \
  -v "$(pwd)/web:/app/web" \
  -v "$(pwd)/.data:/app/web/.data" \
  -v ~/.ssh:/root/.ssh:ro \
  --env-file .env \
  tofino-rsvp-webapp
```

## Development Mode

For development with hot-reloading:

```yaml
# In docker-compose.yml
services:
  webapp:
    # ... other settings as above
    volumes:
      - ..:/app
    environment:
      - DEBUG=1
      # ... other environment variables
```

## Monitoring

Access the application at http://localhost:8080

View logs with:
```bash
docker logs tofino-rsvp
# or with compose
docker compose logs webapp
```

## Environment Variables

The following environment variables should be configured:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable Flask debugging mode | not set |
| `ADMIN_USER_ON_SWITCH` | Username for SSH access to switches | `admin` |
| `SSH_RESERVATIONS_CONFIG_ON_SWITCH` | Path to reservation config on switches | `/etc/ssh/reservations.conf` |
| `ENFORCE_SSH_ACCESS_RESERVATION_SCRIPT_ON_SWITCH` | Script on switches to enforce access permissions | *no default* |
