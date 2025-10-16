import os
from dotenv import load_dotenv
import pytz

load_dotenv()
telegram_token = os.getenv('TELEGRAM_TOKEN')
telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

intervalo_ejecucion = int(os.getenv('intervalo_ejecucion', 5400))  # 1.5 horas
umbral_obra_programada = int(os.getenv('umbral_obra_programada', 5))
dias_renotificar_obra = int(os.getenv('dias_renotificar_obra', 15))
dias_limpiar_historial = int(os.getenv('dias_limpiar_historial', 5))
url_estado_subte = "https://aplicacioneswp.metrovias.com.ar/estadolineasEMOVA/desktopEmova.html"
archivo_estado = "estados_persistentes.json"
estado_normal = "Normal"
estado_redundante = "Servicio finalizado"
horario_analisis_inicio =  int(os.getenv('horario_analisis_inicio', 6))
horario_analisis_fin =  int(os.getenv('horario_analisis_fin', 23))
# Timezone para Buenos Aires
timezone_local = pytz.timezone('America/Argentina/Buenos_Aires')