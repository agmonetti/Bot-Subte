import os
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config

def obtener_estado_subte():
    """Obtiene el estado actual del subte usando Selenium en modo headless."""
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

        print(f"Navegando a: {Config.URL_ESTADO_SUBTE}")
        driver.get(Config.URL_ESTADO_SUBTE)

        wait = WebDriverWait(driver, 15)
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#estadoLineasContainer .row:last-child .col")) >= 7)

        sin_servicio = driver.find_elements(By.ID, "divSinservicio")
        if sin_servicio and not sin_servicio[0].get_attribute("hidden"):
            print("El sistema de información del subte no está disponible.")
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
                else:
                    if i < len(lineas_subte):
                        nombre_linea = f"Línea {lineas_subte[i]}"
                    else:
                        continue
                
                estados[nombre_linea] = estado_texto
                print(f"Extraído - {nombre_linea}: {estado_texto}")
                
            except Exception as e:
                print(f"Error al extraer información de la columna {i}: {e}")
                continue

        if not estados:
            print("No se pudo acceder al estado del subte. Reintentando mas tarde.")
        
        driver.quit()
        return estados
        
    except Exception as e:
        print(f"Error al obtener estados con Selenium: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        try:
            print("Ejecutando recolector de basura: limpiando procesos zombies de Chrome...")
            os.system("pkill -f chrome")
            os.system("pkill -f chromedriver")
        except Exception as kill_e:
            print(f"Error al ejecutar pkill: {kill_e}")
            
        return {}