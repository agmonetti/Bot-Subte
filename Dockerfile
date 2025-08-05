# Imagen base con Python
FROM python:3.11-slim

# Instala Chrome y ChromeDriver
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    curl \
    unzip \
    fonts-liberation \
    && apt-get clean

# Variables de entorno para Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV PATH=$PATH:/usr/bin/chromium

# Crea directorio y copia código
WORKDIR /app
COPY . .

# Instala dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Corre el bot
CMD ["python", "bot.py"]

