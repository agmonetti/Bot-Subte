import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config

def cargar_estados_anteriores():
    """Lee el historial desde el archivo físico."""
    try:
        if Config.ARCHIVO_ESTADO.exists():
            with open(Config.ARCHIVO_ESTADO, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error de I/O al cargar estados: {e}")
        return {}

def guardar_estados(estados_actuales, historial, fecha_actualizacion):
    """Escribe los diccionarios procesados al sistema de archivos."""
    try:
        data = {
            "ultima_actualizacion": fecha_actualizacion,
            "estados_actuales": estados_actuales,
            "historial": historial
        }
        with open(Config.ARCHIVO_ESTADO, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error de I/O al guardar estados: {e}")