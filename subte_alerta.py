import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

# ========================
# CONFIGURACIÓN
# ========================
TELEGRAM_TOKEN = '###'
TELEGRAM_CHAT_ID = '####'
INTERVALO_EJECUCION = 5400  # 1.5 horas en segundos
ESTADO_NORMAL = "Normal" 


# ========================
# FUNCIONES
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
        chrome_options.add_argument('--window-size=1200,800')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url_estado)
        
        # Esperar más tiempo para que cargue completamente
        time.sleep(8)
        
        # Guardar HTML para depuración
        html_content = driver.page_source
        with open("subte_debug.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("HTML guardado en subte_debug.html para análisis")
        
        # Obtener el texto completo de la página
        page_text = driver.execute_script("return document.body.innerText;")
        print("Contenido de la página (primeros 1000 caracteres):")
        print(page_text[:1000])
        print("\n--- FIN DEL CONTENIDO ---")
        
        # Método robusto: Extraer estados basándose en el patrón del contenido
        lines = page_text.split('\n')
        lineas_subte = ['A', 'B', 'C', 'D', 'E', 'H']
        estado_index = 0
        
        i = 0
        while i < len(lines) and estado_index < len(lineas_subte):
            line = lines[i].strip()
            
            # Si es un estado estándar
            if line in ['Normal', 'Limitado', 'Demora', 'Interrumpido', 'Suspendido', 'Sin servicio']:
                linea_nombre = f"Línea {lineas_subte[estado_index]}"
                estados[linea_nombre] = line
                print(f"Extraído - {linea_nombre}: {line}")
                estado_index += 1
            
            # Si es una descripción de problema (líneas largas con texto descriptivo)
            elif (len(line) > 10 and 
                  estado_index < len(lineas_subte) and
                  any(keyword in line.lower() for keyword in 
                      ["no se detienen", "operativo", "demora", "interrumpido", 
                       "suspendido", "limitado", "sin servicio", "problema", 
                       "cerrado", "fuera de servicio", "reparación", "mantenimiento",
                       "incidente", "avería", "falla"])):
                
                linea_nombre = f"Línea {lineas_subte[estado_index]}"
                # Truncar el mensaje si es muy largo
                mensaje_estado = line[:100] + "..." if len(line) > 100 else line
                estados[linea_nombre] = f"Problema: {mensaje_estado}"
                print(f"Extraído - {linea_nombre}: Problema: {mensaje_estado}")
                estado_index += 1
            
            # Si encontramos una línea que parece irrelevante pero necesitamos avanzar
            elif (estado_index < len(lineas_subte) and 
                  line and 
                  not line.isdigit() and 
                  "." not in line and 
                  len(line) > 5 and
                  line not in ['Estado del servicio', 'Los trenes']):
                
                # Revisar si la siguiente línea es "Normal"
                if i + 1 < len(lines) and lines[i + 1].strip() == 'Normal':
                    # Esta línea descriptiva corresponde a una línea con problemas
                    linea_nombre = f"Línea {lineas_subte[estado_index]}"
                    mensaje_estado = line[:100] + "..." if len(line) > 100 else line
                    estados[linea_nombre] = f"Alerta: {mensaje_estado}"
                    print(f"Extraído - {linea_nombre}: Alerta: {mensaje_estado}")
                    estado_index += 1
                    i += 1  # Saltar la línea "Normal" siguiente
            
            i += 1
        
        # Si no hemos completado todas las líneas, asumir que las restantes son normales
        while estado_index < len(lineas_subte):
            linea_nombre = f"Línea {lineas_subte[estado_index]}"
            estados[linea_nombre] = "Normal"
            print(f"Asumido - {linea_nombre}: Normal (no se encontró información específica)")
            estado_index += 1
        
        driver.quit()
        return estados
        
    except Exception as e:
        print(f"Error al obtener estados con Selenium: {e}")
        if driver:
            driver.quit()
        return {}

def enviar_alerta_telegram(cambios):
    mensaje = "🚇 *Alerta del Subte de Buenos Aires*\n\n"
    for linea, estado in cambios.items():
        mensaje += f"🔸 {linea}: *{estado}*\n"

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)
    print("📤 Alerta enviada por Telegram")
    print(f"Mensaje enviado: {mensaje}")  # Agregado para depuración

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
        print(f"Estados obtenidos: {estados}")  # Agregado para depuración
        
        if not estados:
            print("⚠️ No se pudo obtener información de estados. Verificar estructura HTML.")
            return
            
        # Verificar si tenemos el mensaje especial de "Información no disponible"
        if len(estados) == 1 and "estado_servicio" in estados and estados["estado_servicio"] == "Información no disponible":
            print("ℹ️ El servicio de información de estados del subte no está disponible en este momento.")
            # Opcionalmente, podemos enviar una alerta sobre esto
            enviar_alerta_telegram({"Sistema de información": "No disponible temporalmente"})
            return
            
        cambios = {}

        for linea, estado in estados.items():
            estado_limpio = estado.strip()
            estado_normal_limpio = ESTADO_NORMAL.strip()
            print(f"Comparando '{estado_limpio}' con '{estado_normal_limpio}' - ¿Son diferentes? {estado_limpio.lower() != estado_normal_limpio.lower()}")
            if estado_limpio.lower() != estado_normal_limpio.lower():
                cambios[linea] = estado_limpio

        if cambios:
            enviar_alerta_telegram(cambios)
        else:
            print("✅ Todo funciona normalmente.")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """
    Función principal que ejecuta el programa en bucle con espera.
    """
    print("🚀 Iniciando Bot de Alertas del Subte")
    print(f"⏰ Configurado para ejecutarse cada {INTERVALO_EJECUCION//60} minutos")
    
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




