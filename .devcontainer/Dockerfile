# Multi-Python Development Container for Pure3270
# Supports Python 3.9, 3.10, 3.11, 3.12, and 3.13 via pyenv

FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Install dependencies for pyenv and Python compilation
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    wget \
    curl \
    llvm \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libffi-dev \
    liblzma-dev \
    python3-openssl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Switch to vscode user for pyenv installation
USER vscode

# Install pyenv
RUN curl https://pyenv.run | bash

# Add pyenv to PATH and initialize
ENV PATH="/home/vscode/.pyenv/bin:$PATH"
RUN echo 'export PATH="/home/vscode/.pyenv/bin:$PATH"' >> ~/.bashrc && \
    echo 'eval "$(pyenv init -)"' >> ~/.bashrc && \
    echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc

# Set shell to bash for pyenv
SHELL ["/bin/bash", "-c"]

# Install all Python versions used in CI
ENV PYTHON_VERSIONS="3.9.21 3.10.14 3.11.10 3.12.11 3.13.1"
RUN source ~/.bashrc && \
    for version in $PYTHON_VERSIONS; do \
        echo "Installing Python $version..." && \
        pyenv install $version; \
    done

# Set Python 3.12 as global default (matches CI default)
RUN source ~/.bashrc && pyenv global 3.12.11

# Create a convenience script for testing with all versions
RUN mkdir -p /home/vscode/bin

# Ensure proper ownership
USER root
RUN chown -R vscode:vscode /home/vscode/.pyenv
USER vscode