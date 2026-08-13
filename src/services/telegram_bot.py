import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config
from src.services.scrapper import obtener_estado_subte
from src.services.storage import cargar_estados_anteriores
from src.services.telegram_notifier import enviar_mensaje_telegram

def formatear_estado_actual(estados):
    """Formatea el estado crudo de cada línea sin truncar oraciones."""
    mensaje = "Estado del Subte de Buenos Aires\n\n"
    lineas = ['A', 'B', 'C', 'D', 'E', 'H', 'Premetro']

    for linea in lineas:
        estado = estados.get(linea)
        if estado:
            mensaje += f"<b>{linea}:</b> {estado}\n"
        else:
            mensaje += f"<b>{linea}:</b> sin datos disponibles\n"

    return mensaje

def obtener_respuesta_estado():
    """Devuelve el estado actual, con fallback al último estado persistido."""
    estados = obtener_estado_subte()
    if estados:
        return formatear_estado_actual(estados)

    data_anterior = cargar_estados_anteriores()
    estados_persistidos = data_anterior.get("estados_actuales", {})
    if estados_persistidos:
        return formatear_estado_actual(estados_persistidos)

    return "No se pudo obtener el estado del subte en este momento."

def obtener_updates(offset):
    """Long-polling de la API de Telegram."""
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": Config.POLLING_TIMEOUT}
    response = requests.get(url, params=params, timeout=Config.POLLING_TIMEOUT + 10)
    response.raise_for_status()
    return response.json()

def escuchar_comandos():
    """Escucha comandos del bot sin interrumpir el loop principal."""
    offset = None

    while True:
        try:
            data = obtener_updates(offset)
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                mensaje = update.get("message", {})
                texto = mensaje.get("text", "")
                chat_id = mensaje.get("chat", {}).get("id")

                if not chat_id:
                    continue

                if texto.strip().startswith(Config.COMANDO_ESTADO):
                    respuesta = obtener_respuesta_estado()
                    enviar_mensaje_telegram(respuesta, chat_id=chat_id)
        except requests.exceptions.RequestException as e:
            print(f"Error de red al consultar comandos de Telegram: {e}")
        except Exception as e:
            print(f"Error inesperado al escuchar comandos: {e}")

        time.sleep(Config.POLLING_INTERVALO)
