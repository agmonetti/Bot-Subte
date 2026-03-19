import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

# Se define el directorio raíz del proyecto (un nivel arriba de src/config.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# Se carga el archivo .env desde la raíz
load_dotenv(BASE_DIR / '.env')

class Config:
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    INTERVALO_EJECUCION = int(os.getenv('INTERVALO_EJECUCION', 5400))
    UMBRAL_OBRA_PROGRAMADA = int(os.getenv('UMBRAL_OBRA_PROGRAMADA', 5))
    DIAS_RENOTIFICAR_OBRA = int(os.getenv('DIAS_RENOTIFICAR_OBRA', 15))
    DIAS_LIMPIAR_HISTORIAL = int(os.getenv('DIAS_LIMPIAR_HISTORIAL', 5))

    HORARIO_ANALISIS_INICIO = int(os.getenv('HORARIO_ANALISIS_INICIO', 6))
    HORARIO_ANALISIS_FIN = int(os.getenv('HORARIO_ANALISIS_FIN', 23))

    URL_ESTADO_SUBTE = "https://aplicacioneswp.metrovias.com.ar/estadolineasEMOVA/desktopEmova.html"
    ESTADO_NORMAL = "Normal"
    ESTADO_REDUNDANTE = "Servicio finalizado"
    TIMEZONE_LOCAL = ZoneInfo('America/Argentina/Buenos_Aires')

    DATA_DIR = BASE_DIR / 'src' / 'data'
    ARCHIVO_ESTADO = DATA_DIR / 'estados_persistentes.json'

    @classmethod
    def validate(cls):
        """Verifica requerimientos críticos y prepara el entorno."""
        if not cls.TELEGRAM_TOKEN or not cls.TELEGRAM_CHAT_ID:
            print("Error crítico: TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no definidos en el .env")
            sys.exit(1)
        
        # Crea la carpeta src/data/ si no existe al iniciar la aplicación
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)

Config.validate()