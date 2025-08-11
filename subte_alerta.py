import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os

# ========================
# CONFIGURACIÓN
# ========================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
INTERVALO_EJECUCION = 5400  # 1.5 horas en segundos
ESTADO_NORMAL = "Normal" 
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
        
        # ...existing code...
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
