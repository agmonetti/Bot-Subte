FROM python:3.11-slim-bookworm

WORKDIR /app

# Copia e instala únicamente las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código fuente (incluyendo la carpeta src/)
COPY . .

# Actualiza el punto de entrada al nuevo orquestador principal
CMD ["python", "src/main.py"]