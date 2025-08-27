import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

# ========================
# CONFIGURACIÓN
# ========================
TELEGRAM_TOKEN=os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID=os.getenv('TELEGRAM_CHAT_ID')
INTERVALO_EJECUCION = 5400  # 1.5 horas en segundos
ESTADO_NORMAL = "Normal"
ARCHIVO_ESTADO = "estados_persistentes.json"
UMBRAL_OBRA_PROGRAMADA = 5  # Después de 5 detecciones consecutivas, se considera obra programada
DIAS_RENOTIFICAR_OBRA = 15   # Renotificar obras programadas cada 15 días

# Verificar variables de entorno críticas
if not TELEGRAM_TOKEN:
    print("❌ Error: TELEGRAM_TOKEN no está configurado")
    exit(1)
    
if not TELEGRAM_CHAT_ID:
    print("❌ Error: TELEGRAM_CHAT_ID no está configurado")
    exit(1)

print(f"✅ Variables de entorno configuradas correctamente")
print(f"📱 Chat ID: {TELEGRAM_CHAT_ID}")
print(f"🤖 Token configurado: {'Sí' if TELEGRAM_TOKEN else 'No'}")

# ========================
# FUNCIONES DE PERSISTENCIA
# ========================
def cargar_estados_anteriores():
    """Carga los estados anteriores desde archivo JSON"""
    try:
        if os.path.exists(ARCHIVO_ESTADO):
            with open(ARCHIVO_ESTADO, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error al cargar estados anteriores: {e}")
        return {}

def guardar_estados(estados_actuales, historial):
    """Guarda los estados actuales y el historial en archivo JSON"""
    try:
        data = {
            "ultima_actualizacion": datetime.now().isoformat(),
            "estados_actuales": estados_actuales,
            "historial": historial
        }
        with open(ARCHIVO_ESTADO, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error al guardar estados: {e}")

# ========================
# FUNCIONES PRINCIPALES
# ========================
def obtener_estado_subte():
    """
    Obtiene el estado de las líneas del subte de Buenos Aires usando Selenium.
    """
    url_estado = "https://aplicacioneswp.metrovias.com.ar/estadolineasEMOVA/desktopEmova.html"
    estados = {}
    driver = None
    
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--window-size=1200,800')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Detectar si estamos en un contenedor Docker
        is_docker = os.path.exists('/.dockerenv') or os.getenv('CHROME_BIN')
        
        if is_docker:
            # Configuración para Docker/Zeabur
            chrome_options.binary_location = '/usr/bin/chromium'
            service = webdriver.ChromeService(executable_path='/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            # Configuración para desarrollo local
            driver = webdriver.Chrome(options=chrome_options)
        
        print(f"🌐 Navegando a: {url_estado}")
        driver.get(url_estado)
        
        # Esperar más tiempo para que cargue completamente
        time.sleep(10)
        
        # No guardar HTML en producción para evitar problemas de permisos
        if not is_docker:
            html_content = driver.page_source
            with open("subte_debug.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("HTML guardado en subte_debug.html para análisis")
        
        # Obtener el texto completo de la página
        page_text = driver.execute_script("return document.body.innerText;")
        print("Contenido de la página (primeros 1000 caracteres):")
        print(page_text[:1000])
        print("\n--- FIN DEL CONTENIDO ---")
        
        # Nuevo método: Analizar línea por línea con mejor lógica
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        lineas_subte = ['A', 'B', 'C', 'D', 'E', 'H']
        
        # Encontrar todas las líneas que contienen "Normal" o descripciones de problemas
        estados_encontrados = []
        
        for i, line in enumerate(lines):
            # Si encontramos "Normal", lo agregamos
            if line == "Normal":
                estados_encontrados.append("Normal")
                print(f"Encontrado estado Normal en línea {i}: '{line}'")
            
            # Si encontramos una descripción de problema (texto largo descriptivo)
            elif (len(line) > 15 and 
                  any(keyword in line.lower() for keyword in 
                      ["cerrada", "cerrado", "plaza italia", "obras", "renovación", 
                       "no se detienen", "operativo", "demora", "interrumpido", 
                       "suspendido", "limitado", "sin servicio", "problema", 
                       "fuera de servicio", "reparación", "mantenimiento",
                       "incidente", "avería", "falla", "estación"])):
                
                estados_encontrados.append(line)
                print(f"Encontrado problema en línea {i}: '{line}'")
        
        print(f"Estados encontrados: {estados_encontrados}")
        
        # Asignar estados a las líneas
        for i, linea in enumerate(lineas_subte):
            if i < len(estados_encontrados):
                estado = estados_encontrados[i]
                # Si el estado es muy largo, truncarlo para el mensaje
                if len(estado) > 100:
                    estado = estado[:97] + "..."
                estados[f"Línea {linea}"] = estado
                print(f"Asignado - Línea {linea}: {estado}")
            else:
                # Si no hay suficientes estados, asumir normal
                estados[f"Línea {linea}"] = "Normal"
                print(f"Asumido - Línea {linea}: Normal")
        
        driver.quit()
        return estados
        
    except Exception as e:
        print(f"Error al obtener estados con Selenium: {e}")
        if driver:
            driver.quit()
        return {}

def analizar_cambios_con_historial(estados_actuales):
    """
    Analiza los cambios considerando el historial de estados.
    Retorna: (cambios_nuevos, obras_programadas, obras_renotificar)
    """
    data_anterior = cargar_estados_anteriores()
    historial = data_anterior.get("historial", {})
    
    cambios_nuevos = {}
    obras_programadas = {}
    obras_renotificar = {}
    
    # Palabras clave que indican obras programadas/renovación integral
    palabras_obra_programada = [
        "obras de renovación integral",
        "renovación integral", 
        "obras de renovacion integral",
        "renovacion integral",
        "obra programada",
        "mantenimiento programado",
        "renovación de estación",
        "renovacion de estacion",
        "modernización",
        "modernizacion"
    ]
    
    def es_obra_programada_por_texto(estado):
        """Detecta si el estado indica una obra programada por sus palabras clave"""
        estado_lower = estado.lower()
        return any(palabra in estado_lower for palabra in palabras_obra_programada)
    
    for linea, estado_actual in estados_actuales.items():
        if estado_actual.lower() != ESTADO_NORMAL.lower():
            # Hay un problema en esta línea
            
            # Verificar si es obra programada por texto
            es_obra_por_texto = es_obra_programada_por_texto(estado_actual)
            
            if linea not in historial:
                # Primera vez que vemos este problema
                historial[linea] = {
                    "estado": estado_actual,
                    "contador": 1,
                    "primera_deteccion": datetime.now().isoformat(),
                    "ultima_notificacion": None,
                    "es_obra_programada": es_obra_por_texto,  # Marcar inmediatamente si es obra por texto
                    "detectada_por_texto": es_obra_por_texto
                }
                
                if es_obra_por_texto:
                    # Es obra programada detectada por texto, notificar como tal
                    obras_programadas[linea] = estado_actual
                    print(f"🏗️ Obra programada detectada por texto en {linea}: {estado_actual}")
                else:
                    # Problema nuevo, notificar normalmente
                    cambios_nuevos[linea] = estado_actual
                    print(f"🆕 Nuevo problema detectado en {linea}: {estado_actual}")
                
            elif historial[linea]["estado"] == estado_actual:
                # Mismo problema que antes
                historial[linea]["contador"] += 1
                
                # Si no era obra programada antes, verificar si ahora lo es por texto
                if not historial[linea]["es_obra_programada"] and es_obra_por_texto:
                    historial[linea]["es_obra_programada"] = True
                    historial[linea]["detectada_por_texto"] = True
                    obras_programadas[linea] = estado_actual
                    print(f"🏗️ {linea} reclasificada como obra programada por texto: {estado_actual}")
                
                elif (historial[linea]["contador"] >= UMBRAL_OBRA_PROGRAMADA and 
                      not historial[linea]["es_obra_programada"]):
                    # Se convierte en obra programada por persistencia
                    historial[linea]["es_obra_programada"] = True
                    historial[linea]["detectada_por_texto"] = False
                    obras_programadas[linea] = estado_actual
                    print(f"🏗️ {linea} clasificada como obra programada por persistencia tras {historial[linea]['contador']} detecciones")
                    
                elif historial[linea]["es_obra_programada"]:
                    # Es obra programada, verificar si hay que renotificar
                    ultima_notif = historial[linea]["ultima_notificacion"]
                    if ultima_notif:
                        ultima_fecha = datetime.fromisoformat(ultima_notif)
                        if datetime.now() - ultima_fecha >= timedelta(days=DIAS_RENOTIFICAR_OBRA):
                            obras_renotificar[linea] = estado_actual
                            tipo_deteccion = "texto" if historial[linea].get("detectada_por_texto", False) else "persistencia"
                            print(f"🔔 Renotificando obra programada (detectada por {tipo_deteccion}) en {linea}")
                    else:
                        # Primera notificación como obra programada
                        obras_renotificar[linea] = estado_actual
                        
                elif historial[linea]["contador"] < UMBRAL_OBRA_PROGRAMADA:
                    # Aún no es obra programada por persistencia, seguir alertando
                    cambios_nuevos[linea] = estado_actual
                    print(f"🔄 Problema continúa en {linea} (detección {historial[linea]['contador']})")
                    
            else:
                # Cambió el problema
                es_obra_por_texto_nuevo = es_obra_programada_por_texto(estado_actual)
                historial[linea] = {
                    "estado": estado_actual,
                    "contador": 1,
                    "primera_deteccion": datetime.now().isoformat(),
                    "ultima_notificacion": None,
                    "es_obra_programada": es_obra_por_texto_nuevo,
                    "detectada_por_texto": es_obra_por_texto_nuevo
                }
                
                if es_obra_por_texto_nuevo:
                    obras_programadas[linea] = estado_actual
                    print(f"🏗️ Problema cambió a obra programada (por texto) en {linea}: {estado_actual}")
                else:
                    cambios_nuevos[linea] = estado_actual
                    print(f"🔄 Problema cambió en {linea}: {estado_actual}")
                
        else:
            # Línea volvió a normal
            if linea in historial:
                if historial[linea]["es_obra_programada"]:
                    tipo_deteccion = "texto" if historial[linea].get("detectada_por_texto", False) else "persistencia"
                    print(f"✅ Obra programada (detectada por {tipo_deteccion}) finalizada en {linea}")
                    cambios_nuevos[linea] = "✅ Volvió a funcionar normalmente"
                else:
                    print(f"✅ Problema resuelto en {linea}")
                    cambios_nuevos[linea] = "✅ Volvió a funcionar normalmente"
                del historial[linea]
    
    # Actualizar timestamp de notificación para elementos notificados
    ahora = datetime.now().isoformat()
    for linea in list(cambios_nuevos.keys()) + list(obras_renotificar.keys()):
        if linea in historial:
            historial[linea]["ultima_notificacion"] = ahora
    
    # Guardar estados actualizados
    guardar_estados(estados_actuales, historial)
    
    return cambios_nuevos, obras_programadas, obras_renotificar

def enviar_alerta_telegram(cambios_nuevos, obras_programadas, obras_renotificar):
    """Envía alertas diferenciadas según el tipo de cambio"""
    
    if cambios_nuevos:
        mensaje = "🚇 *Alerta del Subte de Buenos Aires*\n\n"
        for linea, estado in cambios_nuevos.items():
            if "Volvió a funcionar" in estado:
                mensaje += f"✅ {linea}: {estado}\n"
            else:
                mensaje += f"🔸 {linea}: *{estado}*\n"
        enviar_mensaje_telegram(mensaje)
    
    if obras_programadas:
        mensaje = "🏗️ *Obra Programada Detectada*\n\n"
        mensaje += "Las siguientes líneas tienen obras programadas:\n\n"
        for linea, estado in obras_programadas.items():
            mensaje += f"🔸 {linea}: *{estado}*\n"
        mensaje += f"\n📅 No se volverá a notificar hasta dentro de {DIAS_RENOTIFICAR_OBRA} días."
        enviar_mensaje_telegram(mensaje)
    
    if obras_renotificar:
        mensaje = "🔔 *Recordatorio - Obras Programadas*\n\n"
        mensaje += "Las siguientes obras programadas siguen activas:\n\n"
        for linea, estado in obras_renotificar.items():
            mensaje += f"🔸 {linea}: *{estado}*\n"
        mensaje += f"\n📅 Próximo recordatorio en {DIAS_RENOTIFICAR_OBRA} días."
        enviar_mensaje_telegram(mensaje)


def enviar_mensaje_telegram(mensaje):
    """Función auxiliar para enviar mensajes a Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=data)
    print("📤 Mensaje enviado por Telegram")
    print(f"Mensaje: {mensaje}")
    return response

# ========================
# EJECUCIÓN PRINCIPAL
# ========================
def verificar_estados():
    """
    Función que ejecuta la verificación de estados y envío de alertas.
    """
    try:
        print(f"⏱️ Iniciando verificación - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        estados = obtener_estado_subte()
        print(f"Estados obtenidos: {estados}")
        
        if not estados:
            print("⚠️ No se pudo obtener información de estados. Verificar estructura HTML.")
            return
            
        # Verificar si tenemos el mensaje especial de "Información no disponible"
        if len(estados) == 1 and "estado_servicio" in estados and estados["estado_servicio"] == "Información no disponible":
            print("ℹ️ El servicio de información de estados del subte no está disponible en este momento.")
            # Opcionalmente, podemos enviar una alerta sobre esto
            enviar_mensaje_telegram("⚠️ El sistema de información del subte no está disponible temporalmente.")
            return
            
        # Usar el nuevo sistema de análisis con historial
        cambios_nuevos, obras_programadas, obras_renotificar = analizar_cambios_con_historial(estados)
        
        if cambios_nuevos or obras_programadas or obras_renotificar:
            enviar_alerta_telegram(cambios_nuevos, obras_programadas, obras_renotificar)
        else:
            print("✅ Todo funciona normalmente (sin cambios que notificar).")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """
    Función principal que ejecuta el programa en bucle con espera.
    """
    print("🚀 Iniciando Bot de Alertas del Subte")
    print(f"⏰ Configurado para ejecutarse cada {INTERVALO_EJECUCION//60} minutos")
    print(f"🏗️ Umbral para obras programadas: {UMBRAL_OBRA_PROGRAMADA} detecciones")
    print(f"🔔 Recordatorios de obras cada {DIAS_RENOTIFICAR_OBRA} días")
    
    while True:
        verificar_estados()
        
        # Mostrar cuándo será la próxima ejecución
        proxima_ejecucion = time.strftime('%Y-%m-%d %H:%M:%S', 
                                          time.localtime(time.time() + INTERVALO_EJECUCION))
        print(f"💤 Esperando hasta la próxima ejecución ({proxima_ejecucion})...")
        
        # Esperar el intervalo configurado
        time.sleep(INTERVALO_EJECUCION)

if __name__ == "__main__":
    main()