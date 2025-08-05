# Imagen base con Python
FROM python:3.10-slim

# Evita preguntas interactivas durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instala dependencias necesarias del sistema, Chrome y ChromeDriver
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Instala Google Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get update && apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# Instala ChromeDriver (usa la misma versión que Chrome)
RUN CHROME_VERSION=$(google-chrome --version | grep -oP "\d+\.\d+\.\d+\.\d+" | cut -d '.' -f 1-3) && \
    CHROMEDRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_VERSION}") && \
    wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing
