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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv


load_dotenv()

from config import (
    telegram_token, telegram_chat_id, estado_normal, url_estado_subte,
    intervalo_ejecucion, umbral_obra_programada, dias_renotificar_obra, 
    archivo_estado, estado_redundante, dias_limpiar_historial,
    horario_analisis_inicio, horario_analisis_fin, timezone_local
)


# ========================
# FUNCIONES DE PERSISTENCIA
# ========================

def verificar_tokens_telegram():
    """Verifica que los tokens de Telegram estén configurados"""
    if not telegram_token:
        print("Error: TELEGRAM_TOKEN no está configurado")
        exit(1)

    if not telegram_chat_id:
        print("Error: TELEGRAM_CHAT_ID no está configurado")
        exit(1)

verificar_tokens_telegram()

def cargar_estados_anteriores():
    """Carga el estado anterior y el historial desde un archivo JSON"""
    try:
        if os.path.exists(archivo_estado):
            with open(archivo_estado, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error al cargar estados anteriores: {e}")
        return {}

def guardar_estados(estados_actuales, historial):
    """Guarda el estado actual y el historial en un archivo JSON"""
    try:
        data = {
            "ultima_actualizacion": datetime.now(timezone_local).isoformat(),
            "estados_actuales": estados_actuales,
            "historial": historial
        }
        with open(archivo_estado, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error al guardar estados: {e}")

# ========================
# FUNCION PRINCIPALES
# ========================

def obtener_estado_subte():
    """Obtiene el estado actual del subte usando Selenium"""
    estados = {}
    driver = None
    
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        is_docker = os.path.exists('/.dockerenv') or os.getenv('CHROME_BIN')
        
        if is_docker:
            chrome_options.binary_location = '/usr/bin/chromium'
            service = webdriver.ChromeService(executable_path='/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)

        print(f"Navegando a: {url_estado_subte}")
        driver.get(url_estado_subte)

        wait = WebDriverWait(driver, 15)
        wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "#estadoLineasContainer .row:last-child .col")) >= 7)

        """ La pagina puede mostrarse como fuera de servicio """
        sin_servicio = driver.find_elements(By.ID, "divSinservicio")
        if sin_servicio and not sin_servicio[0].get_attribute("hidden"):
            enviar_mensaje_telegram("El sistema de información del subte no está disponible.")
            driver.quit()
            return {}
        
        
        columnas = driver.find_elements(By.CSS_SELECTOR, "#estadoLineasContainer .row:last-child .col")
        lineas_subte = ['A', 'B', 'C', 'D', 'E', 'H', 'Premetro']
        
        
        for i, columna in enumerate(columnas):
            try:
                img = columna.find_element(By.CSS_SELECTOR, "img")
                alt_text = img.get_attribute("alt")
                p_elemento = columna.find_element(By.CSS_SELECTOR, "p")
                estado_texto = p_elemento.text.strip()

                if alt_text and alt_text.strip():
                    nombre_linea = alt_text.strip()
                    # print(f"Usando alt_text: {nombre_linea}")

                else:
                    if i < len(lineas_subte):
                        nombre_linea = f"Línea {lineas_subte[i]}"
                        # print(f"Como la columna {i} no tenía alt_text: uso la opcion de backup: {nombre_linea}")
                    else:
                        # print(f"Columna {i} no tenia disponible el alt_text y fuera del rango de lineas_subte")
                        continue
                
                estados[nombre_linea] = estado_texto
                print(f"Extraído - {nombre_linea}: {estado_texto}")
                
            except Exception as e:
                print(f"Error al extraer información de la columna {i}: {e}")
                continue

        if len(estados) == 0:
            enviar_mensaje_telegram("No se pudo acceder al estado del subte. Reintentando mas tarde")
            driver.quit()
            return {}
        else:
            # print(f"Se pudieron obtener {len(estados)} líneas del scrapping")
            pass
        
        driver.quit()
        return estados
        
        
    except Exception as e:
        print(f"Error al obtener estados con Selenium: {e}")
        if driver:
            driver.quit()
        return {}

# =================================
# FUNCIONES DE ANALISIS DE CAMBIOS
# =================================

def procesar_obra_individual(linea, obra, indice, historial):
    """Procesa una obra individual y determina su estado"""
    clave_obra = f"{linea}_obra_{indice}" if indice > 0 else f"{linea}_obra"
    
    if clave_obra not in historial:
        """aparece una nueva obra"""
        historial[clave_obra] = {
            "estado": obra,
            "linea_original": linea,
            "tipo": "obra",
            "contador": 1,
            "primera_deteccion": datetime.now(timezone_local).isoformat(),
            "ultima_notificacion": None,
            "es_obra_programada": True,
            "detectada_por_texto": True,
            "activa": True,
            "ya_notificada": True
        }
        return "nueva_obra", obra
        
    elif historial[clave_obra]["estado"] == obra:
        """la obra sigue estando"""
        historial[clave_obra]["contador"] += 1
        
        if not historial[clave_obra].get("activa", True):
            historial[clave_obra]["activa"] = True
            historial[clave_obra]["fecha_reactivacion"] = datetime.now(timezone_local).isoformat()
            return "reactivada_silenciosa", obra
            
        elif (historial[clave_obra]["es_obra_programada"] and 
              historial[clave_obra].get("ya_notificada", False)):
            ultima_notif = historial[clave_obra]["ultima_notificacion"]
            if ultima_notif:
                ultima_fecha = datetime.fromisoformat(ultima_notif)
                if datetime.now(timezone_local) - ultima_fecha >= timedelta(days=dias_renotificar_obra):
                    return "renotificar", obra
        return "continua", obra
    else:
        """significa que la obra cambio"""
        historial[clave_obra] = {
            "estado": obra,
            "linea_original": linea,
            "tipo": "obra",
            "contador": 1,
            "primera_deteccion": datetime.now(timezone_local).isoformat(),
            "ultima_notificacion": None,
            "es_obra_programada": True,
            "detectada_por_texto": True,
            "activa": True,
            "ya_notificada": True
        }
        return "obra_cambiada", obra

def procesar_problema_individual(linea, problema, indice, historial):
    """Procesa un problema individual y determina su estado"""
    clave_problema = f"{linea}_problema_{indice}" if indice > 0 else f"{linea}_problema"
    
    if clave_problema not in historial:
        historial[clave_problema] = {
            "estado": problema,
            "linea_original": linea,
            "tipo": "problema",
            "contador": 1,
            "primera_deteccion": datetime.now(timezone_local).isoformat(),
            "ultima_notificacion": None,
            "es_obra_programada": False,
            "detectada_por_texto": False,
            "activa": True,
            "ya_notificada": True
        }
        return "nuevo_problema", problema
        
    elif historial[clave_problema]["estado"] == problema:
        historial[clave_problema]["contador"] += 1
        
        if not historial[clave_problema].get("activa", True):
            historial[clave_problema]["activa"] = True
            historial[clave_problema]["fecha_reactivacion"] = datetime.now(timezone_local).isoformat()
            return "problema_reactivado", problema
            
        if (historial[clave_problema]["contador"] >= umbral_obra_programada and 
            not historial[clave_problema]["es_obra_programada"]):
            """Se define como una obra por persistencia ya que no quiero recibir constantes notificaciones """
            historial[clave_problema]["es_obra_programada"] = True
            mensaje_obra = f"{problema}.\n \nEste problema llegó a 5 apariciones, por lo que solo se volverá a notificar cuando cambie de estado o en 15 días \n"
            return "convertido_a_obra", mensaje_obra
        elif not historial[clave_problema]["es_obra_programada"]:
            return "problema_continua", problema
        
        return "problema_persistente", problema
    else:
        historial[clave_problema] = {
            "estado": problema,
            "linea_original": linea,
            "tipo": "problema",
            "contador": 1,
            "primera_deteccion": datetime.now(timezone_local).isoformat(),
            "ultima_notificacion": None,
            "es_obra_programada": False,
            "detectada_por_texto": False,
            "activa": True,
            "ya_notificada": True
        }
        return "problema_cambiado", problema

def detectar_componentes_desaparecidos(linea, componentes, historial):
    """Detecta componentes que ya no están presentes
    Utilizo una copia para poder modificar durante iteración"""
    cambios_resueltos = []
    claves_linea_existentes = [k for k in historial.keys() if historial[k].get("linea_original") == linea]
    
    for clave in claves_linea_existentes[:]: 
        tipo_componente = historial[clave]["tipo"]
        estado_componente = historial[clave]["estado"]
        es_obra_programada = historial[clave].get("es_obra_programada", False)
        
        componente_aun_presente = False
        
        if tipo_componente == "obra":
            componente_aun_presente = estado_componente in componentes['obras']
        elif tipo_componente == "problema":
            componente_aun_presente = estado_componente in componentes['problemas']
        
        if not componente_aun_presente:
            if tipo_componente == "problema" and not es_obra_programada:
                cambios_resueltos.append(f"Problema resuelto: {estado_componente}")
                del historial[clave]
            elif tipo_componente == "obra" and not es_obra_programada:
                cambios_resueltos.append(f"Obra finalizada: {estado_componente}")
                del historial[clave]
            else:
                historial[clave]["activa"] = False
                historial[clave]["fecha_desaparicion"] = datetime.now(timezone_local).isoformat()
    
    return cambios_resueltos

def procesar_linea_con_problemas(linea, estado_actual, historial):
    """Procesa una línea que tiene problemas o obras"""
    componentes = procesar_estado_por_oraciones(estado_actual)
    
    resultados = {
        'cambios_nuevos': [],
        'obras_programadas': [],
        'obras_renotificar': []
    }
    
    for i, obra in enumerate(componentes['obras']):
        tipo_resultado, contenido = procesar_obra_individual(linea, obra, i, historial)
        
        if tipo_resultado in ["nueva_obra", "obra_cambiada"]:
            resultados['obras_programadas'].append(contenido)
            print(f"Obra programada detectada en {linea}: {contenido}")
        elif tipo_resultado == "renotificar":
            resultados['obras_renotificar'].append(contenido)
            print(f"Renotificando obra en {linea}: {contenido}")
        elif tipo_resultado == "reactivada_silenciosa":
            print(f"Obra programada reactivada silenciosamente en {linea}: {contenido}")
    

    for i, problema in enumerate(componentes['problemas']):
        tipo_resultado, contenido = procesar_problema_individual(linea, problema, i, historial)
        
        if tipo_resultado in ["nuevo_problema", "problema_cambiado"]:
            resultados['cambios_nuevos'].append(contenido)
            print(f"Nuevo problema detectado en {linea}: {contenido}")
        elif tipo_resultado == "convertido_a_obra":
            resultados['obras_programadas'].append(contenido)
            print(f"{linea} - problema clasificado como obra por persistencia: {problema}")
        elif tipo_resultado in ["problema_continua", "problema_reactivado"]:
            resultados['cambios_nuevos'].append(contenido)
            if tipo_resultado == "problema_reactivado":
                print(f"Problema reactivado en {linea}: {contenido}")
            else:
                print(f"Problema continúa en {linea}: {contenido}")
    
    """hay cambios resueltos?"""
    cambios_resueltos = detectar_componentes_desaparecidos(linea, componentes, historial)
    resultados['cambios_nuevos'].extend(cambios_resueltos)
    
    return resultados

def procesar_linea_normal(linea, historial):
    """Procesa una línea que volvió a normal"""
    claves_a_eliminar = [k for k in historial.keys() if historial[k].get("linea_original") == linea]
    
    if claves_a_eliminar:
        for clave in claves_a_eliminar:
            del historial[clave]
        print(f"{linea} volvió a normal - limpiado historial")
        return ["Volvió a funcionar normalmente"]
    
    return []

def actualizar_timestamps_notificacion(cambios_nuevos, obras_programadas, obras_renotificar, historial):
    """Actualiza los timestamps de notificación"""
    ahora = datetime.now(timezone_local).isoformat()
    
    for linea_dict in [cambios_nuevos, obras_programadas, obras_renotificar]:
        for linea in linea_dict.keys():
            claves_linea = [k for k in historial.keys() if historial[k].get("linea_original") == linea]
            for clave in claves_linea:
                historial[clave]["ultima_notificacion"] = ahora

def limpiar_historial_antiguo(historial):
    """Elimina entradas inactivas después de X días, 
    incluyendo obras clasificadas por persistencia"""
    claves_a_eliminar = []
    ahora = datetime.now(timezone_local)
    
    for clave, datos in historial.items():
        if not datos.get("activa", True):
            fecha_desaparicion = datos.get("fecha_desaparicion")
            if fecha_desaparicion:
                fecha_desap = datetime.fromisoformat(fecha_desaparicion)
                dias_transcurridos = (ahora - fecha_desap).days
                
                es_obra_por_persistencia = (
                    datos.get("es_obra_programada", False) and 
                    not datos.get("detectada_por_texto", True)
                )
                
                if dias_transcurridos >= dias_limpiar_historial:
                    if es_obra_por_persistencia or not datos.get("es_obra_programada", False):
                        claves_a_eliminar.append(clave)
                        #print(f"Limpiando {tipo_entrada}: {clave} ({dias_transcurridos} días inactiva)")
    
    for clave in claves_a_eliminar:
        del historial[clave]
    
    return len(claves_a_eliminar) > 0

def analizar_cambios_con_historial(estados_actuales):
    """Función principal que coordina el análisis del sitio web y la detección de cambios"""
    data_anterior = cargar_estados_anteriores()
    historial = data_anterior.get("historial", {})

    limpiar_historial_antiguo(historial)

    estados_para_procesar = {}
    for linea, estado in estados_actuales.items():
        if estado.lower() != estado_redundante.lower():
            estados_para_procesar[linea] = estado

    
    cambios_nuevos = {}
    obras_programadas = {}
    obras_renotificar = {}

    for linea, estado_actual in estados_para_procesar.items():

        if estado_actual.lower() != estado_normal.lower():
            resultados = procesar_linea_con_problemas(linea, estado_actual, historial)
            
            if resultados['cambios_nuevos']:
                cambios_nuevos[linea] = resultados['cambios_nuevos']
            if resultados['obras_programadas']:
                obras_programadas[linea] = resultados['obras_programadas']
            if resultados['obras_renotificar']:
                obras_renotificar[linea] = resultados['obras_renotificar']

        else:
            cambios_normales = procesar_linea_normal(linea, historial)
            if cambios_normales:
                cambios_nuevos[linea] = cambios_normales
    

    actualizar_timestamps_notificacion(cambios_nuevos, obras_programadas, obras_renotificar, historial)
    guardar_estados(estados_para_procesar, historial)
    
    return cambios_nuevos, obras_programadas, obras_renotificar
def procesar_estado_por_oraciones(estado_completo):
    """Procesa el estado completo dividiéndolo en oraciones y clasificándolas
       Fue necesario crear un diccionario de abreviaciones para evitar divisiones incorrectas
    """
    abreviaciones = {
        'Int.Saguier': 'INTSAGUIER_TEMP',
        'Int. Saguier': 'INTSAGUIER_TEMP',
        'Gral. Savio': 'GRALSAVIO_TEMP',
        'Gral.Savio': 'GRALSAVIO_TEMP',
        'Av. de Mayo': 'AVDEMAYO_TEMP',
        'Av.de Mayo': 'AVDEMAYO_TEMP',
        'Av. La Plata': 'AVLAPLATA_TEMP',
        'Av.La Plata': 'AVLAPLATA_TEMP',
        'Gral. Paz': 'GRALPAZ_TEMP',
        'Gral.Paz': 'GRALPAZ_TEMP',
        'Gral. Urquiza': 'GRALURQUIZA_TEMP',
        'Gral.Urquiza': 'GRALURQUIZA_TEMP',
        'Gral. Belgrano': 'GRALBELGRANO_TEMP',
        'Gral.Belgrano': 'GRALBELGRANO_TEMP',
        'J.M. Rosas': 'JMROSAS_TEMP',
        'J. M. Rosas': 'JMROSAS_TEMP',
        'J.M.Rosas': 'JMROSAS_TEMP',
    }
    
    """Tomamos el texto completo, reemplazamos las abreviaciones"""
    texto = estado_completo.strip()
    reverso = {}  

    """En este bucle reemplazamos las abreviaciones por temporales"""
    for original, temporal in abreviaciones.items():
        texto = texto.replace(original, temporal)
        reverso[temporal] = original
       
    oraciones = re.split(r'\.\s+|\.$', texto)
    
    oraciones_finales = []
    for oracion in oraciones:
        oracion = oracion.strip()
        if not oracion:
            continue
        
        """Revertimos las abreviaciones temporales a su forma original"""
        for temporal, original in reverso.items():
            oracion = oracion.replace(temporal, original)
        
        oraciones_finales.append(oracion)
    
    '''Clasificamos las oraciones en obras, problemas y otros'''
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
        'otros': []
    }
    
    for oracion in oraciones_finales:
        oracion_lower = oracion.lower()
        
        if any(palabra in oracion_lower for palabra in palabras_obra):
            componentes['obras'].append(oracion)
        elif oracion_lower != "normal":
            componentes['problemas'].append(oracion)
        else:
            componentes['otros'].append(oracion)
    
    return componentes

def enviar_alerta_telegram(cambios_nuevos, obras_programadas, obras_renotificar):
    """Envía una alerta por Telegram con los cambios detectados"""    
    if not (cambios_nuevos or obras_programadas or obras_renotificar):
        return
    
    mensaje = "🚇 Estado del Subte de Buenos Aires\n\n"
    if obras_programadas:   
        mensaje += "Obras Programadas Detectadas:\n\n"
        tiene_obra_por_persistencia = False
    
        for linea, obras in obras_programadas.items():
            for obra in obras:
                mensaje += f"<b><u>{linea}:</u></b> {obra}\n"
                """verifico si alguna obra fue clasificada por persistencia"""
                if "llegó a 5 apariciones" in obra:
                    tiene_obra_por_persistencia = True
    
        if not tiene_obra_por_persistencia:
            mensaje += f"\nAl ser obras programadas, el próximo recordatorio será en {dias_renotificar_obra} días.\n\n"
        else:
            mensaje += "\n"

    if cambios_nuevos:
        mensaje += "Novedades:\n\n"
        for linea, cambios in cambios_nuevos.items():
            for cambio in cambios:
                if "Volvió a funcionar" in cambio:
                    mensaje += f"✅ <b>{linea}:</b>✅ {cambio}\n"
                elif "Problema resuelto:" in cambio or "Obra finalizada:" in cambio:
                    mensaje += f"✅ <b>{linea}: </b>✅ {cambio}\n"
                else:
                    mensaje += f"<b>{linea}: </b>{cambio}\n"
        mensaje += "\n"
    
   
    if obras_renotificar:
        mensaje += "Recordatorio - Obras Programadas Activas:\n\n"
        for linea, obras in obras_renotificar.items():
            for obra in obras:
                mensaje += f"{linea}: {obra}\n"
        mensaje += f"\nPróximo recordatorio en {dias_renotificar_obra} días.\n"
    
    enviar_mensaje_telegram(mensaje)

def enviar_mensaje_telegram(mensaje):
    """Envía un mensaje usando la API de Telegram"""
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    data = {
        "chat_id": telegram_chat_id,
        "text": mensaje,
        # "parse_mode": "Markdown",
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        if response.status_code == 200:
            print("Mensaje enviado por Telegram exitosamente")
        else:
            print(f"Error al enviar mensaje por Telegram: Status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error general al enviar mensaje por Telegram: {e}")
    except Exception as e:
        print(f"Error desconocido al enviar mensaje por Telegram: {e}")
    
    # print(f"Mensaje: {mensaje}")
    return response

def horarios_de_analisis():
    """Determino el horario de análisis
    horario de 6 am - 23 pm (definido desde config.py)
    Usa timezone de Buenos Aires para evitar problemas con servidores UTC
    """
    hora_actual = datetime.now(timezone_local).hour
    return (horario_analisis_inicio <= hora_actual <= horario_analisis_fin)

def verificar_estados():
    """Función principal que verifica los estados y envía alertas si es necesario"""
    try:
        print(f"Iniciando verificación - {datetime.now(timezone_local).strftime('%Y-%m-%d %H:%M:%S')}")
        estados = obtener_estado_subte()  

        if not estados:
            """Este es el caso en el que el estado es un diccionario vacio"""
            return
         
        cambios_nuevos, obras_programadas, obras_renotificar = analizar_cambios_con_historial(estados)
        if cambios_nuevos or obras_programadas or obras_renotificar:
            enviar_alerta_telegram(cambios_nuevos, obras_programadas, obras_renotificar)
        else:
            print("Todo funciona normalmente (sin cambios que notificar).")  

    except Exception as e:
        print(f"Error: {e}")

# ========================
# EJECUCIÓN PRINCIPAL
# ========================

def main():
    """Función principal que ejecuta el ciclo de verificación periódica"""   
    while True:
        ahora = datetime.now(timezone_local)
        if horarios_de_analisis():
            print(f"Nos encontramos dentro del horario de analisis - Hora actual {ahora.strftime('%H:%M:%S')}")
            verificar_estados()
            proxima_ejecucion = ahora + timedelta(seconds=intervalo_ejecucion)
            print(f"Esperando hasta la próxima ejecución ({proxima_ejecucion.strftime('%Y-%m-%d %H:%M:%S')})...")
            time.sleep(intervalo_ejecucion)

        else:
            """Calcular el tiempo exacto hasta el próximo horario de inicio"""
            if ahora.hour < horario_analisis_inicio:
                """Mismo día, calcular hasta horario_analisis_inicio"""
                proxima_ejecucion = ahora.replace(hour=horario_analisis_inicio, minute=0, second=0, microsecond=0)
            else: 
                """Día siguiente, calcular hasta horario_analisis_inicio del día siguiente"""
                proxima_ejecucion = (ahora + timedelta(days=1)).replace(hour=horario_analisis_inicio, minute=0, second=0, microsecond=0)
            
            segundos_hasta_inicio = (proxima_ejecucion - ahora).total_seconds()
            print(f"Fuera del horario de análisis. Durmiendo hasta {proxima_ejecucion.strftime('%Y-%m-%d %H:%M:%S')} ({segundos_hasta_inicio/3600:.2f} horas)")
            if segundos_hasta_inicio > 0:
                time.sleep(segundos_hasta_inicio)
            else:
                print(f"Advertencia: tiempo de espera calculado es {segundos_hasta_inicio}s, continuando inmediatamente")
        

if __name__ == "__main__":
    main()