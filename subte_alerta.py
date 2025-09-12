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
    Obtiene el estado de las líneas del subte de Buenos Aires usando Selenium
    aprovechando la estructura DOM específica de la página.
    """
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
    
    
def analizar_cambios_con_historial(estados_actuales):
    """
    Analiza los cambios considerando el historial de estados.
    Procesa cada oración como entidad independiente.
    Retorna: (cambios_nuevos, obras_programadas, obras_renotificar, componentes_adicionales)
    """
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
                        "detectada_por_texto": True
                    }
                    if linea not in obras_programadas:
                        obras_programadas[linea] = []
                    obras_programadas[linea].append(obra)
                    print(f"Obra programada detectada en {linea}: {obra}")
                    
                elif historial[clave_obra]["estado"] == obra:
                    # Misma obra continúa
                    historial[clave_obra]["contador"] += 1
                    
                    # Verificar renotificación
                    if historial[clave_obra]["es_obra_programada"]:
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
                        "detectada_por_texto": True
                    }
                    if linea not in obras_programadas:
                        obras_programadas[linea] = []
                    obras_programadas[linea].append(obra)
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
                        "detectada_por_texto": False
                    }
                    if linea not in cambios_nuevos:
                        cambios_nuevos[linea] = []
                    cambios_nuevos[linea].append(problema)
                    print(f"Nuevo problema detectado en {linea}: {problema}")
                    
                elif historial[clave_problema]["estado"] == problema:
                    # Mismo problema continúa
                    historial[clave_problema]["contador"] += 1
                    
                    if (historial[clave_problema]["contador"] >= UMBRAL_OBRA_PROGRAMADA and 
                        not historial[clave_problema]["es_obra_programada"]):
                        # Se convierte en obra por persistencia
                        historial[clave_problema]["es_obra_programada"] = True
                        if linea not in obras_programadas:
                            obras_programadas[linea] = []
                        obras_programadas[linea].append(problema)
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
                        "detectada_por_texto": False
                    }
                    if linea not in cambios_nuevos:
                        cambios_nuevos[linea] = []
                    cambios_nuevos[linea].append(problema)
                    print(f"Problema cambió en {linea}: {problema}")
            
            # Procesar CADA HORARIO como información adicional
            if componentes['horarios']:
                if linea not in componentes_adicionales:
                    componentes_adicionales[linea] = []
                for horario in componentes['horarios']:
                    componentes_adicionales[linea].append(f"{horario}")
                    print(f"Información adicional para {linea}: {horario}")
            
            # NUEVO: Verificar componentes que desaparecieron
            claves_linea_existentes = [k for k in historial.keys() if historial[k].get("linea_original") == linea]
            
            for clave in claves_linea_existentes:
                tipo_componente = historial[clave]["tipo"]
                estado_componente = historial[clave]["estado"]
                
                # Verificar si este componente ya no está presente
                componente_aun_presente = False
                
                if tipo_componente == "obra":
                    componente_aun_presente = estado_componente in componentes['obras']
                elif tipo_componente == "problema":
                    componente_aun_presente = estado_componente in componentes['problemas']
                
                if not componente_aun_presente:
                    # Este componente desapareció
                    if linea not in cambios_nuevos:
                        cambios_nuevos[linea] = []
                    
                    if tipo_componente == "obra":
                        cambios_nuevos[linea].append(f"Obra finalizada: {estado_componente}")
                    elif tipo_componente == "problema":
                        cambios_nuevos[linea].append(f"Problema resuelto: {estado_componente}")
                    
                    # Eliminar del historial
                    del historial[clave]
                    print(f"✅ {tipo_componente.title()} resuelto en {linea}: {estado_componente}")
                
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
def procesar_estado_por_oraciones(estado_completo):
    """
    Separa un estado completo en múltiples componentes independientes
    y los clasifica por tipo (obra, horario, problema, etc.)
    """
    # Separar por punto seguido de espacio o punto final
    oraciones = re.split(r'\.\s+|\.$', estado_completo.strip())
    oraciones = [o.strip() for o in oraciones if o.strip()]
    
    # Palabras clave para clasificación
    palabras_obra = [
        "obras de renovación integral", "renovación integral", 
        "obras de renovacion integral", "renovacion integral",
        "cerrada por obras", "cerrado por obras",
        "obra programada", "mantenimiento programado"
    ]
    
    palabras_horario = [
        "horario extendido", "horario reducido", "horario especial",
        "viernes y sabado", "fin de semana", "feriado"
    ]
    
    componentes = {
        'obras': [],
        'horarios': [],
        'problemas': [],
        'otros': []
    }
    
    for oracion in oraciones:
        oracion_lower = oracion.lower()
        
        if any(palabra in oracion_lower for palabra in palabras_obra):
            componentes['obras'].append(oracion)
        elif any(palabra in oracion_lower for palabra in palabras_horario):
            componentes['horarios'].append(oracion)
        elif oracion_lower != "normal":
            # Si no es obra ni horario, pero tampoco "normal", es un problema
            componentes['problemas'].append(oracion)
        else:
            componentes['otros'].append(oracion)
    
    return componentes

def enviar_alerta_telegram(cambios_nuevos, obras_programadas, obras_renotificar, componentes_adicionales=None):
    """Envía todas las alertas en un único mensaje"""
    
    if not (cambios_nuevos or obras_programadas or obras_renotificar or componentes_adicionales):
        return
    
    mensaje = "🚇 Estado del Subte de Buenos Aires\n\n"
    
    # Obras programadas
    if obras_programadas:
        mensaje += "Obras Programadas Detectadas:\n\n"
        for linea, obras in obras_programadas.items():
            for obra in obras:
                mensaje += f"{linea}: {obra}\n"
        mensaje += f"\nAl ser obras programadas, el próximo recordatorio será en {DIAS_RENOTIFICAR_OBRA} días.\n\n"
    
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
    
    # Información adicional
    if componentes_adicionales:
        mensaje += "Información Adicional:\n\n"
        for linea, componentes in componentes_adicionales.items():
            for componente in componentes:
                mensaje += f"{linea}: {componente}\n"
        mensaje += "\n"
    
    # Recordatorios
    if obras_renotificar:
        mensaje += "Recordatorio - Obras Programadas Activas:\n\n"
        for linea, obras in obras_renotificar.items():
            for obra in obras:
                mensaje += f"{linea}: {obra}\n"
        mensaje += f"\nPróximo recordatorio en {DIAS_RENOTIFICAR_OBRA} días.\n"
    
    enviar_mensaje_telegram(mensaje)


def enviar_mensaje_telegram(mensaje):
    """Función auxiliar para enviar mensajes a Telegram"""
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

# ========================
# EJECUCIÓN PRINCIPAL
# ========================

def verificar_estados():
    """
    Función que ejecuta la verificación de estados y envío de alertas.
    """
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
def main():
    """
    Función principal que ejecuta el programa en bucle con espera.
    """
    
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

