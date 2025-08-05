FROM python:3.11-slim

# Evitar archivos .pyc y forzar logs visibles
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar herramientas necesarias del sistema
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg ca-certificates \
    libnss3 libgconf-2-4 libfontconfig1 libxss1 libappindicator1 libgtk-3-0 \
    libglib2.0-0 libatk-bridge2.0-0 libasound2 libdbus-glib-1-2 \
    fonts-liberation xvfb --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Instalar Google Chrome
RUN wget -q -O chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./chrome.deb && rm chrome.deb

# Instalar ChromeDriver versión compatible (ejemplo con versión 120)
RUN CHROMEDRIVER_VERSION=120.0.6099.109 && \
    wget -q -O chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip chromedriver.zip && \
    mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf chromedriver.zip chromedriver-linux64

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos
COPY . /app

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Ejecutar script principal
CMD ["python", "subte_alerta.py"]



