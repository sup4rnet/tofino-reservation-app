# Base image
FROM python:3.9-slim AS base

# Declare the build arguments so they can be used
ARG REPO_URL
ARG COMMIT_ID

# Install dependencies including SSH client
RUN apt-get update && apt-get install -y \
    entr \
    openssh-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Clone repository
RUN mkdir /app/webapp && cd /app/webapp \
    && git clone ${REPO_URL} . \
    && git checkout ${COMMIT_ID}

COPY on-rsvp-change.sh /app/on-rsvp-change.sh
COPY rest-db-watch.sh /app/rest-db-watch.sh
COPY start.sh /app/start.sh

# Install Python dependencies
WORKDIR /app/webapp

RUN python -m venv .venv \
    && . .venv/bin/activate \
    && pip install --no-cache-dir gunicorn \
    && pip install --no-cache-dir -r requirements.txt 

# Create startup script
WORKDIR /app
# RUN echo '#!/bin/bash\n\
# # Fix SSH directory permissions\n\
# if [ -d /root/.ssh ]; then\n\
#     chmod 700 /root/.ssh\n\
#     if [ -f /root/.ssh/id_rsa ]; then\n\
#         chmod 600 /root/.ssh/id_rsa\n\
#     fi\n\
#     if [ -f /root/.ssh/id_ed25519 ]; then\n\
#         chmod 600 /root/.ssh/id_ed25519\n\
#     fi\n\
#     if [ -f /root/.ssh/config ]; then\n\
#         chmod 600 /root/.ssh/config\n\
#     fi\n\
# fi\n\
# \n\
# # Start the webapp in the background\n\
# cd /app/webapp && ./.venv/bin/gunicorn -w 1 -b :80 server:app &\n\
# \n\
# # Start the file watcher\n\
# /app/rest-db-watch.sh' > /app/start.sh \
#     && chmod +x /app/start.sh

# Expose port for the web application
EXPOSE 80

# Start both services
CMD ["/app/start.sh"]
# sleep
# CMD ["sleep", "infinity"]