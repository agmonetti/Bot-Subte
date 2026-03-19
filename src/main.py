import time
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Se asegura el path raíz
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config
from src.services import (
    obtener_estado_subte,
    cargar_estados_anteriores,
    guardar_estados,
    analizar_cambios_con_historial,
    enviar_alerta_telegram
)

def horarios_de_analisis():
    """Determina si la hora actual está dentro de la ventana de ejecución."""
    hora_actual = datetime.now(Config.TIMEZONE_LOCAL).hour
    return Config.HORARIO_ANALISIS_INICIO <= hora_actual <= Config.HORARIO_ANALISIS_FIN

def verificar_estados():
    """Orquesta el flujo de extracción, análisis y notificación."""
    try:
        print(f"\nIniciando verificación - {datetime.now(Config.TIMEZONE_LOCAL).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. Extraer datos crudos
        estados_actuales = obtener_estado_subte()  
        if not estados_actuales:
            return
            
        # 2. Cargar datos históricos
        data_anterior = cargar_estados_anteriores()
        historial_previo = data_anterior.get("historial", {})
         
        # 3. Analizar cambios en memoria
        cambios_nuevos, obras_programadas, obras_renotificar, estados_procesar, historial_actualizado = analizar_cambios_con_historial(estados_actuales, historial_previo)
        
        # 4. Notificar si corresponde
        if cambios_nuevos or obras_programadas or obras_renotificar:
            enviar_alerta_telegram(cambios_nuevos, obras_programadas, obras_renotificar)
        else:
            print("Todo funciona normalmente (sin cambios que notificar).")  

        # 5. Persistir el nuevo estado en disco
        fecha_actualizacion = datetime.now(Config.TIMEZONE_LOCAL).isoformat()
        guardar_estados(estados_procesar, historial_actualizado, fecha_actualizacion)

    except Exception as e:
        print(f"Error general en el ciclo de verificación: {e}")

def main():
    """Bucle principal de ejecución y control de tiempos."""
    print("Iniciando servicio Bot-Subte...")
    
    while True:
        ahora = datetime.now(Config.TIMEZONE_LOCAL)
        
        if horarios_de_analisis():
            verificar_estados()
            proxima_ejecucion = ahora + timedelta(seconds=Config.INTERVALO_EJECUCION)
            print(f"Esperando hasta la próxima ejecución ({proxima_ejecucion.strftime('%Y-%m-%d %H:%M:%S')})...")
            time.sleep(Config.INTERVALO_EJECUCION)

        else:
            # Calcular tiempo de sueño hasta la apertura del servicio
            if ahora.hour < Config.HORARIO_ANALISIS_INICIO:
                proxima_ejecucion = ahora.replace(hour=Config.HORARIO_ANALISIS_INICIO, minute=0, second=0, microsecond=0)
            else: 
                proxima_ejecucion = (ahora + timedelta(days=1)).replace(hour=Config.HORARIO_ANALISIS_INICIO, minute=0, second=0, microsecond=0)
            
            segundos_hasta_inicio = (proxima_ejecucion - ahora).total_seconds()
            print(f"Fuera del horario de análisis. Durmiendo hasta {proxima_ejecucion.strftime('%Y-%m-%d %H:%M:%S')} ({segundos_hasta_inicio/3600:.2f} horas)")
            
            if segundos_hasta_inicio > 0:
                time.sleep(segundos_hasta_inicio)
            else:
                time.sleep(60)

if __name__ == "__main__":
    main()