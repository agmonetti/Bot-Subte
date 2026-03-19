import requests
import sys
from pathlib import Path

# Se asegura la resolución del path raíz para importar config correctamente
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config

def enviar_mensaje_telegram(mensaje):
    """Ejecuta la petición HTTP contra la API de Telegram."""
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": Config.TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        print("Notificación enviada exitosamente a Telegram.")
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error de red al notificar por Telegram: {e}")
    except Exception as e:
        print(f"Error inesperado en notificador de Telegram: {e}")
    return None

def enviar_alerta_telegram(cambios_nuevos, obras_programadas, obras_renotificar):
    """Formatea la estructura de los diccionarios en un mensaje de texto plano/HTML."""
    if not (cambios_nuevos or obras_programadas or obras_renotificar):
        return

    mensaje = "Estado del Subte de Buenos Aires\n\n"
    
    if obras_programadas:
        mensaje += "Obras Programadas Detectadas:\n\n"
        tiene_obra_por_persistencia = False
        
        for linea, obras in obras_programadas.items():
            for obra in obras:
                mensaje += f"<b><u>{linea}:</u></b> {obra}\n"
                if "llegó a 5 apariciones" in obra:
                    tiene_obra_por_persistencia = True
        
        if not tiene_obra_por_persistencia:
            mensaje += f"\nAl ser obras programadas, el próximo recordatorio será en {Config.DIAS_RENOTIFICAR_OBRA} días.\n\n"
        else:
            mensaje += "\n"

    if cambios_nuevos:
        mensaje += "Novedades:\n\n"
        for linea, cambios in cambios_nuevos.items():
            for cambio in cambios:
                # Se eliminan emojis, manteniendo solo el formato bold para la linea
                mensaje += f"<b>{linea}:</b> {cambio}\n"
        mensaje += "\n"
    
    if obras_renotificar:
        mensaje += "Recordatorio - Obras Programadas Activas:\n\n"
        for linea, obras in obras_renotificar.items():
            for obra in obras:
                mensaje += f"{linea}: {obra}\n"
        mensaje += f"\nPróximo recordatorio en {Config.DIAS_RENOTIFICAR_OBRA} días.\n"
    
    enviar_mensaje_telegram(mensaje)