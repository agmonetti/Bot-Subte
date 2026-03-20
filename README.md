# Bot de Alertas del Subte de Buenos Aires

Este proyecto es un bot automatizado que monitorea el estado de las líneas del subte de Buenos Aires y envía alertas inteligentes a Telegram cuando detecta cambios en el servicio.

## ¿Cómo funciona?

- Utiliza Selenium para navegar y extraer el estado de cada línea desde la web oficial de EMOVA.
- **Sistema inteligente de clasificación**: Distingue automáticamente entre incidentes urgentes y obras programadas.
- **Procesamiento granular**: Analiza cada oración independientemente para detectar múltiples componentes por línea.
- **Persistencia de estados**: Mantiene un historial de problemas para evitar notificaciones repetitivas.
- **Alertas diferenciadas**: Envía diferentes tipos de mensajes según la naturaleza del problema.
- El chequeo se realiza de manera periódica (por defecto, cada 1.5 horas).

## Arquitectura del Proyecto

El código está estructurado de manera modular para separar las responsabilidades de extracción, análisis, almacenamiento y notificación:

```text
├── src/
│   ├── config.py                  # Variables de entorno y constantes globales
│   ├── main.py                    # Orquestador y bucle principal
│   ├── data/
│   │   └── estados_persistentes.json # Historial dinámico de alertas
│   └── services/
│       ├── __init__.py            # Interfaz pública de los servicios
│       ├── scrapper.py            # Extracción web con Selenium
│       ├── analyzer.py            # Lógica de negocio y reglas de texto
│       ├── storage.py             # Entrada/Salida del archivo JSON
│       └── telegram_notifier.py   # Integración con API de Telegram
├── .env                           # Credenciales locales (no versionado)
├── docker-compose.yml             # Despliegue de infraestructura
├── Dockerfile                     # Receta de la imagen con Chromium
└── requirements.txt               # Manifiesto de dependencias Python
```

## Características principales

### Detección 
- **Obras programadas**: Detecta automáticamente obras de renovación integral y mantenimientos programados.
- **Incidentes**: Identifica problemas operativos que requieren atención inmediata.
- **Recuperación de servicio**: Notifica cuando las líneas vuelven a funcionar normalmente.
- **Múltiples componentes**: Puede detectar obras, problemas e información adicional en la misma línea.

### Sistema de historial
- Guarda el estado de cada línea en `src/data/estados_persistentes.json`.
- Cuenta las detecciones consecutivas para clasificar problemas persistentes.
- Evita spam de notificaciones para el mismo problema.

### Alertas diferenciadas
- **Alertas urgentes**: Para nuevos incidentes o problemas operativos.
- **Notificaciones de obras**: Para obras programadas (una sola vez).
- **Recordatorios**: Para obras de larga duración (cada 15 días).
- **Información adicional**: Para horarios especiales y detalles complementarios.

## Variables de entorno

* `TELEGRAM_TOKEN`: Token de tu bot de Telegram. (Requerido)
* `TELEGRAM_CHAT_ID`: ID del chat donde envía alertas. (Requerido)
* `INTERVALO_EJECUCION`: Intervalo entre verificaciones en segundos. (Por defecto: 5400)
* `HORARIO_ANALISIS_INICIO`: Hora de inicio del monitoreo, hora local. (Por defecto: 6)
* `HORARIO_ANALISIS_FIN`: Hora de fin del monitoreo, hora local. (Por defecto: 23)
* `UMBRAL_OBRA_PROGRAMADA`: Detecciones consecutivas para clasificar como obra. (Por defecto: 5)
* `DIAS_RENOTIFICAR_OBRA`: Días entre recordatorios de obras. (Por defecto: 15)
* `DIAS_LIMPIAR_HISTORIAL`: Días inactivos para borrar un registro del historial. (Por defecto: 5)

**Nota sobre zonas horarias:** El bot utiliza la zona horaria de Buenos Aires (America/Argentina/Buenos_Aires, UTC-3) para el monitoreo, independientemente de la zona horaria del servidor donde se ejecute. Esto asegura que los horarios configurados se respeten correctamente incluso cuando se despliega en servidores con zonas horarias diferentes (como Zeabur que usa UTC).

## Créditos

- Desarrollado por Agustin Monetti.
- Basado en información pública de EMOVA.
- GitHub: [@agmonetti](https://github.com/agmonetti)
- Email: agus.monetti01@gmail.com

---

## License
This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
