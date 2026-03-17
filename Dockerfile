FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libnss3 \
    libxss1 \
    libasound2 \
    libgbm1 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*


ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV CHROMIUM_FLAGS="--disable-gpu --no-sandbox --disable-dev-shm-usage --headless"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "subte_alerta.py"]