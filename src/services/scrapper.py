import requests
from bs4 import BeautifulSoup
import sys
from pathlib import Path

# Se asegura la resolución del path raíz para importar config correctamente
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config

def obtener_estado_subte():
    """Obtiene el estado actual del subte utilizando peticiones estáticas."""
    estados = {}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        print(f"Obteniendo datos de: {Config.URL_ESTADO_SUBTE}")
        response = requests.get(Config.URL_ESTADO_SUBTE, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # Verificar si el sistema reporta fuera de servicio global
        sin_servicio = soup.find(id="divSinservicio")
        if sin_servicio and not sin_servicio.has_attr('hidden'):
            print("El sistema de información del subte no está disponible.")
            return {}

        columnas = soup.select("#estadoLineasContainer .row:last-child .col")
        lineas_subte = ['A', 'B', 'C', 'D', 'E', 'H', 'Premetro']

        for i, columna in enumerate(columnas):
            try:
                img = columna.find("img")
                alt_text = img.get("alt") if img else None
                p_elemento = columna.find("p")
                
                if not p_elemento:
                    continue
                    
                estado_texto = p_elemento.get_text(strip=True)

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
            print("No se pudo extraer información válida. Reintentando en el próximo ciclo.")
            return {}
        
        return estados

    except requests.RequestException as e:
        print(f"Error de red al conectar con el servidor: {e}")
        return {}
    except Exception as e:
        print(f"Error inesperado en el procesamiento HTML: {e}")
        return {}