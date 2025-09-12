FROM python:3.10-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    gnupg \
    curl \
    chromium-driver \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Variables de entorno para Chrome headless
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar archivos del proyecto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear directorio para archivos persistentes
RUN mkdir -p /app/data

COPY . .

CMD ["python", "subte_alerta.py"]




