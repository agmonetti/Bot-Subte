# Bot de Alertas del Subte de Buenos Aires

Este proyecto es un bot automatizado que monitorea el estado de las líneas del subte de Buenos Aires y envía alertas inteligentes a Telegram cuando detecta cambios en el servicio.

## ¿Cómo funciona?

- Utiliza Selenium para navegar y extraer el estado de cada línea desde la web oficial de EMOVA.
- **Sistema inteligente de clasificación**: Distingue automáticamente entre incidentes urgentes y obras programadas.
- **Procesamiento granular**: Analiza cada oración independientemente para detectar múltiples componentes por línea.
- **Persistencia de estados**: Mantiene un historial de problemas para evitar notificaciones repetitivas.
- **Alertas diferenciadas**: Envía diferentes tipos de mensajes según la naturaleza del problema.
- El chequeo se realiza de manera periódica (por defecto, cada 1.5 horas).

## Características principales

### Sistema de horarios
- **Cálculo inteligente de espera**: Determina automáticamente cuándo reactivarse según la hora actual
- **Operación optimizada**: Funciona respetando los horarios definidos

### Detección 
- **Obras programadas**: Detecta automáticamente obras de renovación integral y mantenimientos programados
- **Incidentes**: Identifica problemas operativos que requieren atención inmediata
- **Recuperación de servicio**: Notifica cuando las líneas vuelven a funcionar normalmente
- **Múltiples componentes**: Puede detectar obras, problemas e información adicional en la misma línea


### Sistema de historial
- Guarda el estado de cada línea en `estados_persistentes.json`
- Cuenta las detecciones consecutivas para clasificar problemas persistentes
- Evita spam de notificaciones para el mismo problema

### Alertas diferenciadas
- **Alertas urgentes**: Para nuevos incidentes o problemas operativos
- **Notificaciones de obras**: Para obras programadas (una sola vez)
- **Recordatorios**: Para obras de larga duración (cada 15 días)
- **Información adicional**: Para horarios especiales y detalles complementarios


## Requisitos

- Python 3.10+
- Docker (opcional, recomendado para facilitar la ejecución)
- Un bot de Telegram y el ID de chat donde enviar las alertas
- Hosteo local / Nube

## Instalación y uso

### Opción 1: Docker (Recomendado)

1. Clona este repositorio.
2. Crea un archivo `.env` con tus credenciales:
   ```env
   TELEGRAM_TOKEN=tu_token_aqui
   TELEGRAM_CHAT_ID=tu_chat_id_aqui
   ```
3. Construye la imagen:
   ```sh
   docker build -t bot-subte .
   ```
4. Ejecuta el contenedor:
   ```sh
   docker run --rm bot-subte
   ```

### Opción 2: Manual

1. Instala las dependencias:
   ```sh
   pip install -r requirements.txt
   ```
2. Crea un archivo `.env` con tus credenciales (ver ejemplo arriba)
3. Ejecuta el bot:
   ```sh
   python subte_alerta.py
   ```

## Variables de entorno
| Variable | Descripción | Por defecto |
|----------|-------------|-------------|
| `TELEGRAM_TOKEN` | Token de tu bot de Telegram | - |
| `TELEGRAM_CHAT_ID` | ID del chat donde envía alertas | - |
| `intervalo_ejecucion` | Intervalo entre verificaciones (segundos) | 5400 |
| `horario_analisis_inicio` | Hora de inicio del monitoreo (hora de Buenos Aires) | 6 |
| `horario_analisis_fin` | Hora de fin del monitoreo (hora de Buenos Aires) | 23 |
| `umbral_obra_programada` | Detecciones para clasificar como obra | 5 |
| `dias_renotificar_obra` | Días entre recordatorios de obras | 15 |
| `dias_limpiar_historial` | Días para limpiar historial antiguo | 5 |

**Nota sobre zonas horarias:** El bot utiliza la zona horaria de Buenos Aires (America/Argentina/Buenos_Aires, UTC-3) para el monitoreo, independientemente de la zona horaria del servidor donde se ejecute. Esto asegura que los horarios configurados se respeten correctamente incluso cuando se despliega en servidores con zonas horarias diferentes (como Zeabur que usa UTC).

## Créditos

- Desarrollado por Agustin Monetti.
- Basado en información pública de EMOVA.
- GitHub: [@agmonetti](https://github.com/agmonetti)
- Email: agmonetti@uade.edu.ar

---

## License
This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). 
