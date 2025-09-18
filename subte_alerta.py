# Proyecto EMOVA Scraper
# Copyright (C) 2025  Agustin Monetti
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
#/ This program is distributed in the hope that it will be useful,
#/ but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


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
URL_ESTADO_SUBTE = "https://aplicacioneswp.metrovias.com.ar/estadolineasEMOVA/desktopEmova.html"


# Verificar variables de entorno críticas
if not TELEGRAM_TOKEN:
    print("Error: TELEGRAM_TOKEN no está configurado")
    exit(1)
    
if not TELEGRAM_CHAT_ID:
    print("Error: TELEGRAM_CHAT_ID no está configurado")
    exit(1)

# ========================
# FUNCIONES DE PERSISTENCIA
# ========================

# Recupera el historial de incidentes y estados previos para detectar cambios
def cargar_estados_anteriores():
    try:
        if os.path.exists(ARCHIVO_ESTADO):
            with open(ARCHIVO_ESTADO, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error al cargar estados anteriores: {e}")
        return {}

# Persiste el estado completo del sistema para continuidad entre ejecuciones
def guardar_estados(estados_actuales, historial):
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

# Extrae informacion de estado del DOM de la pagina oficial usando Selenium
def obtener_estado_subte():
    #url_estado = "https://aplicacioneswp.metrovias.com.ar/estadolineasEMOVA/desktopEmova.html"
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
        
        print(f"Navegando a: {URL_ESTADO_SUBTE}")
        driver.get(URL_ESTADO_SUBTE)
        
        # Esperar más tiempo para que cargue completamente
        time.sleep(10)
        
        # No guardar HTML en producción para evitar problemas de permisos
        if not is_docker:
            html_content = driver.page_source
            with open("subte_debug.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("HTML guardado en subte_debug.html para análisis")
        
        # Verificar si la página muestra el mensaje de servicio no disponible
        sin_servicio = driver.find_elements(By.ID, "divSinservicio")
        if sin_servicio and not sin_servicio[0].get_attribute("hidden"):
            estados["estado_servicio"] = "Información no disponible"
            driver.quit()
            return estados
        
        # Obtener todas las columnas que contienen información de líneas
        columnas = driver.find_elements(By.CSS_SELECTOR, "#estadoLineasContainer .row:last-child .col")
        
        # Nombres de las líneas en orden
        lineas_subte = ['A', 'B', 'C', 'D', 'E', 'H', 'Premetro']
        
        # Extraer estados de cada columna
        for i, columna in enumerate(columnas[:min(len(columnas), len(lineas_subte))]):
            try:
                # Buscar la etiqueta de imagen para obtener el nombre alternativo (alt)
                img = columna.find_element(By.CSS_SELECTOR, "img")
                alt_text = img.get_attribute("alt")
                
                # Buscar el texto de estado dentro del párrafo
                p_elemento = columna.find_element(By.CSS_SELECTOR, "p")
                estado_texto = p_elemento.text.strip()
                
                # Asignar el estado a la línea correspondiente
                nombre_linea = f"Línea {lineas_subte[i]}"
                estados[nombre_linea] = estado_texto
                print(f"Extraído - {nombre_linea}: {estado_texto}")
                
            except Exception as e:
                print(f"Error al extraer información de la columna {i}: {e}")
                # Si hay error en alguna columna, asignar estado normal por defecto
                if i < len(lineas_subte):
                    estados[f"Línea {lineas_subte[i]}"] = "Normal"
        
        driver.quit()
        return estados
        
    except Exception as e:
        print(f"Error al obtener estados con Selenium: {e}")
        if driver:
            driver.quit()
        return {}
    
# Procesa estados actuales contra historial y clasifica incidentes por tipo y persistencia
def analizar_cambios_con_historial(estados_actuales):
    data_anterior = cargar_estados_anteriores()
    historial = data_anterior.get("historial", {})
    
    cambios_nuevos = {}
    obras_programadas = {}
    obras_renotificar = {}
    componentes_adicionales = {}
    
    for linea, estado_actual in estados_actuales.items():
        if estado_actual.lower() != ESTADO_NORMAL.lower():
            # Procesar el estado por componentes
            componentes = procesar_estado_por_oraciones(estado_actual)
            
            # Procesar CADA OBRA independientemente
            for i, obra in enumerate(componentes['obras']):
                clave_obra = f"{linea}_obra_{i}" if i > 0 else f"{linea}_obra"
                
                if clave_obra not in historial:
                    # Nueva obra detectada
                    historial[clave_obra] = {
                        "estado": obra,
                        "linea_original": linea,
                        "tipo": "obra",
                        "contador": 1,
                        "primera_deteccion": datetime.now().isoformat(),
                        "ultima_notificacion": None,
                        "es_obra_programada": True,
                        "detectada_por_texto": True,
                        "activa": True,
                        "ya_notificada": False
                    }
                    if linea not in obras_programadas:
                        obras_programadas[linea] = []
                    obras_programadas[linea].append(obra)
                    historial[clave_obra]["ya_notificada"] = True
                    print(f"Obra programada detectada en {linea}: {obra}")
                    
                elif historial[clave_obra]["estado"] == obra:
                    # Misma obra continúa
                    historial[clave_obra]["contador"] += 1
                    
                    # Si estaba inactiva, reactivarla sin notificar
                    if not historial[clave_obra].get("activa", True):
                        historial[clave_obra]["activa"] = True
                        historial[clave_obra]["fecha_reactivacion"] = datetime.now().isoformat()
                        print(f"Obra programada reactivada silenciosamente en {linea}: {obra}")
                    
                    # Verificar renotificación solo si está activa y ya fue notificada
                    elif historial[clave_obra]["es_obra_programada"] and historial[clave_obra].get("ya_notificada", False):
                        ultima_notif = historial[clave_obra]["ultima_notificacion"]
                        if ultima_notif:
                            ultima_fecha = datetime.fromisoformat(ultima_notif)
                            if datetime.now() - ultima_fecha >= timedelta(days=DIAS_RENOTIFICAR_OBRA):
                                if linea not in obras_renotificar:
                                    obras_renotificar[linea] = []
                                obras_renotificar[linea].append(obra)
                                print(f"Renotificando obra en {linea}: {obra}")
                else:
                    # Obra cambió
                    historial[clave_obra] = {
                        "estado": obra,
                        "linea_original": linea,
                        "tipo": "obra",
                        "contador": 1,
                        "primera_deteccion": datetime.now().isoformat(),
                        "ultima_notificacion": None,
                        "es_obra_programada": True,
                        "detectada_por_texto": True,
                        "activa": True,
                        "ya_notificada": False
                    }
                    if linea not in obras_programadas:
                        obras_programadas[linea] = []
                    obras_programadas[linea].append(obra)
                    historial[clave_obra]["ya_notificada"] = True
                    print(f"Obra cambió en {linea}: {obra}")
            
            # Procesar CADA PROBLEMA independientemente
            for i, problema in enumerate(componentes['problemas']):
                clave_problema = f"{linea}_problema_{i}" if i > 0 else f"{linea}_problema"
                
                if clave_problema not in historial:
                    # Nuevo problema
                    historial[clave_problema] = {
                        "estado": problema,
                        "linea_original": linea,
                        "tipo": "problema",
                        "contador": 1,
                        "primera_deteccion": datetime.now().isoformat(),
                        "ultima_notificacion": None,
                        "es_obra_programada": False,
                        "detectada_por_texto": False,
                        "activa": True,
                        "ya_notificada": False
                    }
                    if linea not in cambios_nuevos:
                        cambios_nuevos[linea] = []
                    cambios_nuevos[linea].append(problema)
                    historial[clave_problema]["ya_notificada"] = True
                    print(f"Nuevo problema detectado en {linea}: {problema}")
                    
                elif historial[clave_problema]["estado"] == problema:
                    # Mismo problema continúa
                    historial[clave_problema]["contador"] += 1
                    
                    # Si estaba inactivo, reactivarlo
                    if not historial[clave_problema].get("activa", True):
                        historial[clave_problema]["activa"] = True
                        historial[clave_problema]["fecha_reactivacion"] = datetime.now().isoformat()
                        print(f"Problema reactivado en {linea}: {problema}")
                    
                    if (historial[clave_problema]["contador"] >= UMBRAL_OBRA_PROGRAMADA and 
                        not historial[clave_problema]["es_obra_programada"]):
                        # Se convierte en obra por persistencia
                        historial[clave_problema]["es_obra_programada"] = True
                        if linea not in obras_programadas:
                            obras_programadas[linea] = []
                        obras_programadas[linea].append(f"{problema}.\nEste problema llegó a 5 apariciones, por lo que solo se volverá a notificar cuando cambie de estado o en 15 días")
                        print(f"{linea} - problema clasificado como obra por persistencia: {problema}")
                    elif not historial[clave_problema]["es_obra_programada"]:
                        # Continúa como problema
                        if linea not in cambios_nuevos:
                            cambios_nuevos[linea] = []
                        cambios_nuevos[linea].append(problema)
                        print(f"Problema continúa en {linea}: {problema}")
                else:
                    # Problema cambió
                    historial[clave_problema] = {
                        "estado": problema,
                        "linea_original": linea,
                        "tipo": "problema",
                        "contador": 1,
                        "primera_deteccion": datetime.now().isoformat(),
                        "ultima_notificacion": None,
                        "es_obra_programada": False,
                        "detectada_por_texto": False,
                        "activa": True,
                        "ya_notificada": False
                    }
                    if linea not in cambios_nuevos:
                        cambios_nuevos[linea] = []
                    cambios_nuevos[linea].append(problema)
                    historial[clave_problema]["ya_notificada"] = True
                    print(f"Problema cambió en {linea}: {problema}")
            
            
            # Verificar componentes que desaparecieron
            claves_linea_existentes = [k for k in historial.keys() if historial[k].get("linea_original") == linea]
            
            for clave in claves_linea_existentes:
                tipo_componente = historial[clave]["tipo"]
                estado_componente = historial[clave]["estado"]
                es_obra_programada = historial[clave].get("es_obra_programada", False)
                
                # Verificar si este componente ya no está presente
                componente_aun_presente = False
                
                if tipo_componente == "obra":
                    componente_aun_presente = estado_componente in componentes['obras']
                elif tipo_componente == "problema":
                    componente_aun_presente = estado_componente in componentes['problemas']
                
                if not componente_aun_presente:
                    # Este componente desapareció
                    if tipo_componente == "problema" and not es_obra_programada:
                        # Notificar problemas resueltos
                        if linea not in cambios_nuevos:
                            cambios_nuevos[linea] = []
                        cambios_nuevos[linea].append(f"Problema resuelto: {estado_componente}")
                        del historial[clave]
                        print(f"Problema resuelto en {linea}: {estado_componente}")
                    elif tipo_componente == "obra" and not es_obra_programada:
                        # Notificar obras no programadas finalizadas
                        if linea not in cambios_nuevos:
                            cambios_nuevos[linea] = []
                        cambios_nuevos[linea].append(f"Obra finalizada: {estado_componente}")
                        del historial[clave]
                        print(f"Obra finalizada en {linea}: {estado_componente}")
                    else:
                        # Obra programada desapareció - marcar como inactiva, no eliminar
                        historial[clave]["activa"] = False
                        historial[clave]["fecha_desaparicion"] = datetime.now().isoformat()
                        print(f"Obra programada marcada como inactiva en {linea}: {estado_componente}")
                
        else:
            # Línea volvió a normal - limpiar TODAS las entradas de esta línea
            claves_a_eliminar = [k for k in historial.keys() if historial[k].get("linea_original") == linea]
            
            if claves_a_eliminar:
                if linea not in cambios_nuevos:
                    cambios_nuevos[linea] = []
                cambios_nuevos[linea].append("Volvió a funcionar normalmente")
                
                for clave in claves_a_eliminar:
                    del historial[clave]
                print(f"{linea} volvió a normal - limpiado historial")
    
    # Actualizar timestamps
    ahora = datetime.now().isoformat()
    for linea_dict in [cambios_nuevos, obras_programadas, obras_renotificar]:
        for linea in linea_dict.keys():
            claves_linea = [k for k in historial.keys() if historial[k].get("linea_original") == linea]
            for clave in claves_linea:
                historial[clave]["ultima_notificacion"] = ahora
    
    # Guardar estados
    guardar_estados(estados_actuales, historial)
    
    return cambios_nuevos, obras_programadas, obras_renotificar, componentes_adicionales

# Separa texto de estado en componentes discretos y los clasifica por tipo de incidente
def procesar_estado_por_oraciones(estado_completo):
    # Separar por punto seguido de espacio o punto final
    oraciones = re.split(r'\.\s+|\.$', estado_completo.strip())
    oraciones = [o.strip() for o in oraciones if o.strip()]
    
    # Palabras clave para clasificación
    palabras_obra = [
        "obras de renovación integral", "renovación integral", 
        "obras de renovacion integral", "renovacion integral",
        "cerrada por obras", "cerrado por obras",
        "obra programada", "mantenimiento programado",
        "obras", "obra"
    ]
    
    componentes = {
        'obras': [],
        'problemas': [],
    }
    
    for oracion in oraciones:
        oracion_lower = oracion.lower()
        
        if any(palabra in oracion_lower for palabra in palabras_obra):
            componentes['obras'].append(oracion)
        elif oracion_lower != "normal":
            # TODO va a problemas: horarios, operativos, demoras, etc.
            componentes['problemas'].append(oracion)
        else:
            componentes['otros'].append(oracion)
    
    return componentes

# Consolida todos los tipos de alertas en un mensaje unificado y maneja timestamps de notificacion
def enviar_alerta_telegram(cambios_nuevos, obras_programadas, obras_renotificar, componentes_adicionales=None):
    
    if not (cambios_nuevos or obras_programadas or obras_renotificar or componentes_adicionales):
        return
    
    mensaje = "🚇 Estado del Subte de Buenos Aires\n\n"
    
    # Obras programadas
    if obras_programadas:   
        mensaje += "Obras Programadas Detectadas:\n\n"
        tiene_obra_por_persistencia = False
    
        for linea, obras in obras_programadas.items():
            for obra in obras:
                mensaje += f"{linea}: {obra}\n"
                # Verificar si alguna obra es por persistencia
                if "llegó a 5 apariciones" in obra:
                    tiene_obra_por_persistencia = True
    
        # Solo mostrar el mensaje de recordatorio si NO hay obras por persistencia
        if not tiene_obra_por_persistencia:
            mensaje += f"\nAl ser obras programadas, el próximo recordatorio será en {DIAS_RENOTIFICAR_OBRA} días.\n\n"
        else:
            mensaje += "\n"
    # Novedades
    if cambios_nuevos:
        mensaje += "Novedades:\n\n"
        for linea, cambios in cambios_nuevos.items():
            for cambio in cambios:
                if "Volvió a funcionar" in cambio:
                    mensaje += f"✅ {linea}: ✅ {cambio}\n"
                elif "Problema resuelto:" in cambio or "Obra finalizada:" in cambio:
                    mensaje += f"✅ {linea}: ✅ {cambio}\n"
                else:
                    mensaje += f"{linea}: {cambio}\n"
        mensaje += "\n"
    
    # Recordatorios
    if obras_renotificar:
        mensaje += "Recordatorio - Obras Programadas Activas:\n\n"
        for linea, obras in obras_renotificar.items():
            for obra in obras:
                mensaje += f"{linea}: {obra}\n"
        mensaje += f"\nPróximo recordatorio en {DIAS_RENOTIFICAR_OBRA} días.\n"
    
    enviar_mensaje_telegram(mensaje)

# Ejecuta el envio HTTP a la API de Telegram con el mensaje formateado
def enviar_mensaje_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    response = requests.post(url, data=data)
    print("📤 Mensaje enviado por Telegram")
    # print(f"Mensaje: {mensaje}")
    return response

# Realiza la verificación completa del estado del subte y maneja alertas
def verificar_estados():
    try:
        print(f"Iniciando verificación - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        estados = obtener_estado_subte()  
        if not estados:
            print("No se pudo obtener información de estados. Verificar estructura HTML.")
            return
           
        # Verificar si tenemos el mensaje especial de "Información no disponible"
        if len(estados) == 1 and "estado_servicio" in estados and estados["estado_servicio"] == "Información no disponible":
            print("El servicio de información de estados del subte no está disponible en este momento.")
            enviar_mensaje_telegram("⚠️ El sistema de información del subte no está disponible temporalmente.")
            return
         
        # CAMBIO: Agregar componentes_adicionales

        cambios_nuevos, obras_programadas, obras_renotificar, componentes_adicionales = analizar_cambios_con_historial(estados)
        if cambios_nuevos or obras_programadas or obras_renotificar or componentes_adicionales:
            enviar_alerta_telegram(cambios_nuevos, obras_programadas, obras_renotificar, componentes_adicionales)

        else:
            print("Todo funciona normalmente (sin cambios que notificar).")

            

    except Exception as e:
        print(f"Error: {e}")

# ========================
# EJECUCIÓN PRINCIPAL
# ========================

# Ejecuta el programa en bucle infinito con intervalos de tiempo configurados
def main():
    
    while True:
        verificar_estados()
        
        # Mostrar cuándo será la próxima ejecución
        proxima_ejecucion = time.strftime('%Y-%m-%d %H:%M:%S', 
                                          time.localtime(time.time() + INTERVALO_EJECUCION))
        print(f"Esperando hasta la próxima ejecución ({proxima_ejecucion})...")
        
        # Esperar el intervalo configurado
        time.sleep(INTERVALO_EJECUCION)

if __name__ == "__main__":

    main()

