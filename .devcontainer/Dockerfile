FROM mcr.microsoft.com/devcontainers/python:3.12-bullseye

# Set up sudoers for vscode user to avoid postStartCommand sudo issues
RUN echo 'vscode ALL=(ALL) NOPASSWD: /usr/bin/apt-get, /bin/tar, /usr/bin/curl, /bin/mv' | tee /etc/sudoers.d/vscode

# Install additional system dependencies that were in postCreateCommand
RUN apt-get update && apt-get install -y \
    libdbus-1-3 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libc6 \
    libdrm2 \
    libgtk-3-0 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Install ACT v0.2.74
RUN curl -LO https://github.com/nektos/act/releases/download/v0.2.74/act_Linux_x86_64.tar.gz \
    && curl -LO https://github.com/nektos/act/releases/download/v0.2.74/checksums.txt \
    && grep act_Linux_x86_64.tar.gz checksums.txt | sha256sum -c - \
    && tar -xzf act_Linux_x86_64.tar.gz -C /usr/local/bin act \
    && rm act_Linux_x86_64.tar.gz checksums.txt
