FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    procps \
    libauthen-ntlm-perl \
    libcgi-pm-perl \
    libcrypt-openssl-rsa-perl \
    libdata-uniqid-perl \
    libencode-imaputf7-perl \
    libfile-copy-recursive-perl \
    libfile-tail-perl \
    libio-socket-ssl-perl \
    libio-socket-inet6-perl \
    libio-tee-perl \
    libhtml-parser-perl \
    libjson-webtoken-perl \
    libmail-imapclient-perl \
    libparse-recdescent-perl \
    libmodule-scandeps-perl \
    libreadonly-perl \
    libregexp-common-perl \
    libsys-meminfo-perl \
    libterm-readkey-perl \
    libtest-mockobject-perl \
    libtest-pod-perl \
    libunicode-string-perl \
    liburi-perl \
    libwww-perl \
    libtest-nowarnings-perl \
    libtest-deep-perl \
    libtest-warn-perl \
    libnet-libidn-perl \
    libnet-ssleay-perl \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install imapsync manually since it's removed from Debian repos
RUN wget -N https://raw.githubusercontent.com/imapsync/imapsync/master/imapsync \
    && cp imapsync /usr/bin/imapsync \
    && chmod +x /usr/bin/imapsync

WORKDIR /app

# Copy requirements
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole project
COPY . .

# Create logs directory
RUN mkdir -p backend/logs && chmod 777 backend/logs

# Change WORKDIR to backend so imports work natively
WORKDIR /app/backend

# Expose the API port
EXPOSE 8000

# Command to run the application
# Now running directly from /app/backend, so we use main:app instead of backend.main:app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
