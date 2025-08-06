# Bot de Alertas del Subte de Buenos Aires 🚇

Este proyecto es un bot automatizado que monitorea el estado de las líneas del subte de Buenos Aires y envía alertas a Telegram cuando detecta cambios en el servicio.

## ¿Cómo funciona?

- Utiliza Selenium para navegar y extraer el estado de cada línea desde la web oficial de EMOVA.
- Si detecta que alguna línea no está en estado "Normal", envía una alerta automática a un chat de Telegram configurado.
- El chequeo se realiza de manera periódica (por defecto, cada 1.5 horas).

## Requisitos

- Python 3.10+
- Docker (opcional, recomendado para facilitar la ejecución)
- Un bot de Telegram y el ID de chat donde enviar las alertas

## Instalación y uso

### Opción 1: Docker

1. Clona este repositorio.
2. Construye la imagen:
   ```sh
   docker build -t bot-subte .
   ```
3. Ejecuta el contenedor:
   ```sh
   docker run --rm bot-subte
   ```

### Opción 2: Manual

1. Instala las dependencias:
   ```sh
   pip install -r requirements.txt
   ```
2. Ejecuta el bot:
   ```sh
   python subte_alerta.py
   ```

## Configuración

Edita las siguientes variables en [`subte_alerta.py`](Bot-Subte/subte_alerta.py):

- `TELEGRAM_TOKEN`: Token de tu bot de Telegram
- `TELEGRAM_CHAT_ID`: ID del chat donde se enviarán las alertas
- `INTERVALO_EJECUCION`: Intervalo de chequeo en segundos (por defecto, 5400)

## Créditos

Desarrollado por Agustin Monetti.  
Basado en información pública de EMOVA.

---
