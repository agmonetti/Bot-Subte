import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Resolución del path raíz para importar config
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config

def procesar_estado_por_oraciones(estado_completo):
    abreviaciones = {
        'Int.Saguier': 'INTSAGUIER_TEMP', 'Int. Saguier': 'INTSAGUIER_TEMP',
        'Gral. Savio': 'GRALSAVIO_TEMP', 'Gral.Savio': 'GRALSAVIO_TEMP',
        'Av. de Mayo': 'AVDEMAYO_TEMP', 'Av.de Mayo': 'AVDEMAYO_TEMP',
        'Av. La Plata': 'AVLAPLATA_TEMP', 'Av.La Plata': 'AVLAPLATA_TEMP',
        'Gral. Paz': 'GRALPAZ_TEMP', 'Gral.Paz': 'GRALPAZ_TEMP',
        'Gral. Urquiza': 'GRALURQUIZA_TEMP', 'Gral.Urquiza': 'GRALURQUIZA_TEMP',
        'Gral. Belgrano': 'GRALBELGRANO_TEMP', 'Gral.Belgrano': 'GRALBELGRANO_TEMP',
        'J.M. Rosas': 'JMROSAS_TEMP', 'J. M. Rosas': 'JMROSAS_TEMP',
        'J.M.Rosas': 'JMROSAS_TEMP', 'Leandro N. Alem': 'LEANDRONALEM_TEMP',
        'Leandro N.Alem': 'LEANDRONALEM_TEMP',
    }
    
    texto = estado_completo.strip()
    reverso = {}  

    for original, temporal in abreviaciones.items():
        if original in texto:
            texto = texto.replace(original, temporal)
            reverso[temporal] = original
       
    oraciones = re.split(r'\.\s+|\.$|\n+', texto)
    oraciones_finales = []
    
    for oracion in oraciones:
        oracion = oracion.strip()
        if not oracion:
            continue
        for temporal, original in reverso.items():
            oracion = oracion.replace(temporal, original)
        oraciones_finales.append(oracion)
    
    palabras_obra = [
        "obras de renovación integral", "renovación integral", 
        "obras de renovacion integral", "renovacion integral",
        "cerrada por obras", "cerrado por obras",
        "obra programada", "mantenimiento programado",
        "obras", "obra"
    ]
    
    componentes = {'obras': [], 'problemas': [], 'otros': []}
    
    for oracion in oraciones_finales:
        oracion_lower = oracion.lower()
        if any(palabra in oracion_lower for palabra in palabras_obra):
            componentes['obras'].append(oracion)
        elif oracion_lower != Config.ESTADO_NORMAL.lower():
            componentes['problemas'].append(oracion)
        else:
            componentes['otros'].append(oracion)
    
    return componentes

def normalizar_obra(texto_obra):
    normalizado = texto_obra.lower().strip()
    palabras_a_remover = [
        'las estaciones ', 'la estación ', 'la estacion ',
        'estaciones ', 'estación ', 'estacion '
    ]
    for palabra in palabras_a_remover:
        normalizado = normalizado.replace(palabra, '')
    return ' '.join(normalizado.split())

def buscar_obra_similar(linea, obra, historial):
    obra_normalizada = normalizar_obra(obra)
    for clave, datos in historial.items():
        if (datos.get("linea_original") == linea and 
            datos.get("tipo") == "obra" and
            datos.get("activa", True)):
            if normalizar_obra(datos.get("estado", "")) == obra_normalizada:
                return clave
    return None

def procesar_obra_individual(linea, obra, indice, historial):
    clave_similar = buscar_obra_similar(linea, obra, historial)
    clave_obra = clave_similar if clave_similar else (f"{linea}_obra_{indice}" if indice > 0 else f"{linea}_obra")
    
    if clave_obra not in historial:
        historial[clave_obra] = {
            "estado": obra, "linea_original": linea, "tipo": "obra",
            "contador": 1, "primera_deteccion": datetime.now(Config.TIMEZONE_LOCAL).isoformat(),
            "ultima_notificacion": None, "es_obra_programada": True,
            "detectada_por_texto": True, "activa": True, "ya_notificada": True
        }
        return "nueva_obra", obra
    else:
        if normalizar_obra(obra) == normalizar_obra(historial[clave_obra]["estado"]):
            historial[clave_obra]["contador"] += 1
            historial[clave_obra]["estado"] = obra
            
            if not historial[clave_obra].get("activa", True):
                historial[clave_obra]["activa"] = True
                historial[clave_obra]["fecha_reactivacion"] = datetime.now(Config.TIMEZONE_LOCAL).isoformat()
                return "reactivada_silenciosa", obra
                
            elif historial[clave_obra]["es_obra_programada"] and historial[clave_obra].get("ya_notificada", False):
                ultima_notif = historial[clave_obra]["ultima_notificacion"]
                if ultima_notif:
                    ultima_fecha = datetime.fromisoformat(ultima_notif)
                    if datetime.now(Config.TIMEZONE_LOCAL) - ultima_fecha >= timedelta(days=Config.DIAS_RENOTIFICAR_OBRA):
                        return "renotificar", obra
            return "continua", obra
        else:
            historial[clave_obra] = {
                "estado": obra, "linea_original": linea, "tipo": "obra",
                "contador": 1, "primera_deteccion": datetime.now(Config.TIMEZONE_LOCAL).isoformat(),
                "ultima_notificacion": None, "es_obra_programada": True,
                "detectada_por_texto": True, "activa": True, "ya_notificada": True
            }
            return "obra_cambiada", obra

def procesar_problema_individual(linea, problema, indice, historial):
    clave_problema = f"{linea}_problema_{indice}" if indice > 0 else f"{linea}_problema"
    
    if clave_problema not in historial:
        historial[clave_problema] = {
            "estado": problema, "linea_original": linea, "tipo": "problema",
            "contador": 1, "primera_deteccion": datetime.now(Config.TIMEZONE_LOCAL).isoformat(),
            "ultima_notificacion": None, "es_obra_programada": False,
            "detectada_por_texto": False, "activa": True, "ya_notificada": True
        }
        return "nuevo_problema", problema
    elif historial[clave_problema]["estado"] == problema:
        historial[clave_problema]["contador"] += 1
        
        if not historial[clave_problema].get("activa", True):
            historial[clave_problema]["activa"] = True
            historial[clave_problema]["fecha_reactivacion"] = datetime.now(Config.TIMEZONE_LOCAL).isoformat()
            return "problema_reactivado", problema
            
        if historial[clave_problema]["contador"] >= Config.UMBRAL_OBRA_PROGRAMADA and not historial[clave_problema]["es_obra_programada"]:
            historial[clave_problema]["es_obra_programada"] = True
            mensaje_obra = f"{problema}.\n \nEste problema llegó a {Config.UMBRAL_OBRA_PROGRAMADA} apariciones, por lo que solo se volverá a notificar cuando cambie de estado o en {Config.DIAS_RENOTIFICAR_OBRA} días \n"
            return "convertido_a_obra", mensaje_obra
        elif not historial[clave_problema]["es_obra_programada"]:
            return "problema_continua", problema
        return "problema_persistente", problema
    else:
        historial[clave_problema] = {
            "estado": problema, "linea_original": linea, "tipo": "problema",
            "contador": 1, "primera_deteccion": datetime.now(Config.TIMEZONE_LOCAL).isoformat(),
            "ultima_notificacion": None, "es_obra_programada": False,
            "detectada_por_texto": False, "activa": True, "ya_notificada": True
        }
        return "problema_cambiado", problema

def detectar_componentes_desaparecidos(linea, componentes, historial):
    cambios_resueltos = []
    claves_linea = [k for k in historial.keys() if historial[k].get("linea_original") == linea]
    
    for clave in claves_linea[:]: 
        tipo = historial[clave]["tipo"]
        estado = historial[clave]["estado"]
        es_obra = historial[clave].get("es_obra_programada", False)
        
        presente = (estado in componentes['obras']) if tipo == "obra" else (estado in componentes['problemas'])
        
        if not presente:
            if tipo == "problema" and not es_obra:
                cambios_resueltos.append(f"Problema resuelto: {estado}")
                del historial[clave]
            elif tipo == "obra" and not es_obra:
                cambios_resueltos.append(f"Obra finalizada: {estado}")
                del historial[clave]
            else:
                historial[clave]["activa"] = False
                historial[clave]["fecha_desaparicion"] = datetime.now(Config.TIMEZONE_LOCAL).isoformat()
    return cambios_resueltos

def procesar_linea_con_problemas(linea, estado_actual, historial):
    componentes = procesar_estado_por_oraciones(estado_actual)
    resultados = {'cambios_nuevos': [], 'obras_programadas': [], 'obras_renotificar': []}
    
    for i, obra in enumerate(componentes['obras']):
        tipo_res, cont = procesar_obra_individual(linea, obra, i, historial)
        if tipo_res in ["nueva_obra", "obra_cambiada"]:
            resultados['obras_programadas'].append(cont)
        elif tipo_res == "renotificar":
            resultados['obras_renotificar'].append(cont)

    for i, prob in enumerate(componentes['problemas']):
        tipo_res, cont = procesar_problema_individual(linea, prob, i, historial)
        if tipo_res in ["nuevo_problema", "problema_cambiado"]:
            resultados['cambios_nuevos'].append(cont)
        elif tipo_res == "convertido_a_obra":
            resultados['obras_programadas'].append(cont)
        elif tipo_res in ["problema_continua", "problema_reactivado"]:
            resultados['cambios_nuevos'].append(cont)
    
    resultados['cambios_nuevos'].extend(detectar_componentes_desaparecidos(linea, componentes, historial))
    return resultados

def limpiar_historial_antiguo(historial):
    claves_a_eliminar = []
    ahora = datetime.now(Config.TIMEZONE_LOCAL)
    
    for clave, datos in historial.items():
        if not datos.get("activa", True):
            fecha_desap_str = datos.get("fecha_desaparicion")
            if fecha_desap_str:
                dias = (ahora - datetime.fromisoformat(fecha_desap_str)).days
                es_obra_persist = datos.get("es_obra_programada", False) and not datos.get("detectada_por_texto", True)
                if dias >= Config.DIAS_LIMPIAR_HISTORIAL:
                    if es_obra_persist or not datos.get("es_obra_programada", False):
                        claves_a_eliminar.append(clave)
    
    for clave in claves_a_eliminar:
        del historial[clave]

def analizar_cambios_con_historial(estados_actuales, historial_previo):
    limpiar_historial_antiguo(historial_previo)

    estados_procesar = {l: e for l, e in estados_actuales.items() if e.lower() != Config.ESTADO_REDUNDANTE.lower()}
    
    cambios_nuevos = {}
    obras_programadas = {}
    obras_renotificar = {}

    for linea, estado in estados_procesar.items():
        if estado.lower() != Config.ESTADO_NORMAL.lower():
            res = procesar_linea_con_problemas(linea, estado, historial_previo)
            if res['cambios_nuevos']: cambios_nuevos[linea] = res['cambios_nuevos']
            if res['obras_programadas']: obras_programadas[linea] = res['obras_programadas']
            if res['obras_renotificar']: obras_renotificar[linea] = res['obras_renotificar']
        else:
            claves_elim = [k for k in historial_previo.keys() if historial_previo[k].get("linea_original") == linea]
            if claves_elim:
                for c in claves_elim: del historial_previo[c]
                cambios_nuevos[linea] = ["Volvió a funcionar normalmente"]

    ahora = datetime.now(Config.TIMEZONE_LOCAL).isoformat()
    for coleccion in [cambios_nuevos, obras_programadas, obras_renotificar]:
        for linea in coleccion.keys():
            for clave in [k for k in historial_previo.keys() if historial_previo[k].get("linea_original") == linea]:
                historial_previo[clave]["ultima_notificacion"] = ahora

    return cambios_nuevos, obras_programadas, obras_renotificar, estados_procesar, historial_previo