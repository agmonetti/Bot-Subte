import os
from dotenv import load_dotenv

load_dotenv()


telegram_token = os.getenv('TELEGRAM_TOKEN')
telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

intervalo_ejecucion = int(os.getenv('intervalo_ejecucion', 5400))  # 1.5 horas
umbral_obra_programada = int(os.getenv('umbral_obra_programada', 5))
dias_renotificar_obra = int(os.getenv('dias_renotificar_obra', 15))
url_estado_subte = "https://aplicacioneswp.metrovias.com.ar/estadolineasEMOVA/desktopEmova.html"
archivo_estado = "estados_persistentes.json"
estado_normal = "Normal"