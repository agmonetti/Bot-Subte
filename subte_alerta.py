import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

# ========================
# CONFIGURACIÓN
# ========================
TELEGRAM_TOKEN = '8366284760:AAHO74Vc58mScw9iVZ7uyjoWwc9iioKMcB8'
TELEGRAM_CHAT_ID = '6404690721'
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
        
        # Método 1: Intentar selectores específicos conocidos
        selectores_posibles = [
            '.estadoLinea',
            '.line-status',
            '.estado-linea', 
            '.linea',
            '.subway-line',
            '[class*="estado"]',
            '[class*="linea"]',
            '[class*="line"]'
        ]
        
        bloques_encontrados = []
        for selector in selectores_posibles:
            try:
                bloques = driver.find_elements(By.CSS_SELECTOR, selector)
                if bloques:
                    print(f"Encontrados {len(bloques)} elementos con selector: {selector}")
                    bloques_encontrados = bloques
                    break
            except:
                continue
        
        # Método 2: Si no encontramos con selectores específicos, buscar por texto
        if not bloques_encontrados:
            print("Buscando elementos por contenido de texto...")
            
            # Buscar todos los elementos que contengan letras de líneas de subte
            all_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'A') or contains(text(), 'B') or contains(text(), 'C') or contains(text(), 'D') or contains(text(), 'E') or contains(text(), 'H')]")
            
            for element in all_elements:
                try:
                    text = element.text.strip()
                    if text and len(text) < 50:  # Filtrar elementos con poco texto
                        # Buscar si contiene una línea específica
                        for linea in ['A', 'B', 'C', 'D', 'E', 'H']:
                            if linea in text:
                                print(f"Elemento encontrado con línea {linea}: {text}")
                                
                                # Buscar el estado en el mismo elemento o elementos cercanos
                                estado_encontrado = None
                                
                                # Estados posibles
                                estados_posibles = ['Normal', 'Limitado', 'Demora', 'Interrumpido', 'Suspendido', 'Sin servicio']
                                
                                # Buscar en el mismo elemento
                                for estado_pos in estados_posibles:
                                    if estado_pos.lower() in text.lower():
                                        estado_encontrado = estado_pos
                                        break
                                
                                # Si no se encontró en el mismo elemento, buscar en elementos hermanos
                                if not estado_encontrado:
                                    try:
                                        parent = element.find_element(By.XPATH, "..")
                                        parent_text = parent.text.strip()
                                        for estado_pos in estados_posibles:
                                            if estado_pos.lower() in parent_text.lower():
                                                estado_encontrado = estado_pos
                                                break
                                    except:
                                        pass
                                
                                # Si aún no se encontró, usar "Normal" como default
                                if not estado_encontrado:
                                    estado_encontrado = "Normal"
                                
                                estados[f"Línea {linea}"] = estado_encontrado
                                print(f"Agregado - Línea {linea}: {estado_encontrado}")
                                break
                except:
                    continue
        
        # Método 3: Extraer información de los bloques encontrados con selectores
        else:
            for bloque in bloques_encontrados:
                try:
                    texto_bloque = bloque.text.strip()
                    print(f"Procesando bloque: {texto_bloque}")
                    
                    # Si el bloque contiene "Estado del servicio", extraer usando el método 4
                    if "Estado del servicio" in texto_bloque:
                        lines = texto_bloque.split('\n')
                        lineas_subte = ['A', 'B', 'C', 'D', 'E', 'H']
                        estado_index = 0
                        
                        for line in lines:
                            line = line.strip()
                            if line in ['Normal', 'Limitado', 'Demora', 'Interrumpido', 'Suspendido', 'Sin servicio']:
                                if estado_index < len(lineas_subte):
                                    linea_nombre = f"Línea {lineas_subte[estado_index]}"
                                    estados[linea_nombre] = line
                                    print(f"Extraído - {linea_nombre}: {line}")
                                    estado_index += 1
                        break
                    
                    # Buscar nombre de línea (método original)
                    nombre_encontrado = None
                    for linea in ['A', 'B', 'C', 'D', 'E', 'H']:
                        if linea in texto_bloque:
                            nombre_encontrado = f"Línea {linea}"
                            break
                    
                    # Buscar estado
                    estado_encontrado = None
                    estados_posibles = ['Normal', 'Limitado', 'Demora', 'Interrumpido', 'Suspendido', 'Sin servicio']
                    for estado_pos in estados_posibles:
                        if estado_pos.lower() in texto_bloque.lower():
                            estado_encontrado = estado_pos
                            break
                    
                    if nombre_encontrado and estado_encontrado:
                        estados[nombre_encontrado] = estado_encontrado
                        print(f"Encontrado - {nombre_encontrado}: {estado_encontrado}")
                    
                except Exception as e:
                    print(f"Error procesando bloque: {e}")
                    continue
        
        # Si no se encontró nada, mostrar contenido de la página para análisis
        if not estados:
            page_text = driver.execute_script("return document.body.innerText;")
            print("Contenido de la página (primeros 1000 caracteres):")
            print(page_text[:1000])
            print("\n--- FIN DEL CONTENIDO ---")
            
            # Método 4: Extraer estados basándose en el patrón del contenido
            lines = page_text.split('\n')
            lineas_subte = ['A', 'B', 'C', 'D', 'E', 'H']
            estado_index = 0
            
            for i, line in enumerate(lines):
                line = line.strip()
                if line in ['Normal', 'Limitado', 'Demora', 'Interrumpido', 'Suspendido', 'Sin servicio']:
                    if estado_index < len(lineas_subte):
                        linea_nombre = f"Línea {lineas_subte[estado_index]}"
                        estados[linea_nombre] = line
                        print(f"Extraído - {linea_nombre}: {line}")
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


