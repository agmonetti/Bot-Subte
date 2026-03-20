# Buenos Aires Subway Alert Bot

This project is an automated bot that monitors the status of Buenos Aires subway lines and sends intelligent alerts to Telegram when it detects service changes.

## How does it work?

- Uses Selenium to navigate and extract the status of each line from the official EMOVA website.
- **Intelligent classification system**: Automatically distinguishes between urgent incidents and scheduled works.
- **Granular processing**: Analyzes each sentence independently to detect multiple components per line.
- **State persistence**: Maintains a history of problems to avoid repetitive notifications.
- **Differentiated alerts**: Sends different types of messages according to the nature of the problem.
- Checking is performed periodically (by default, every 1.5 hours).

## Project Architecture

The code is modularly structured to separate extraction, analysis, storage, and notification responsibilities:

```text
├── src/
│   ├── config.py                  # Environment variables and global constants
│   ├── main.py                    # Orchestrator and main loop
│   ├── data/
│   │   └── estados_persistentes.json # Dynamic alert history
│   └── services/
│       ├── __init__.py            # Services public interface
│       ├── scrapper.py            # Web scraping with Selenium
│       ├── analyzer.py            # Business logic and text parsing
│       ├── storage.py             # JSON file Input/Output
│       └── telegram_notifier.py   # Telegram API integration
├── .env                           # Local credentials (not versioned)
├── docker-compose.yml             # Infrastructure deployment
├── Dockerfile                     # Image recipe with Chromium
└── requirements.txt               # Python dependencies manifest
```

## Main Features

### Detection 
- **Scheduled works**: Automatically detects comprehensive renovation works and scheduled maintenance.
- **Incidents**: Identifies operational problems that require immediate attention.
- **Service recovery**: Notifies when lines return to normal operation.
- **Multiple components**: Can detect works, problems and additional information on the same line.

### History system
- Saves the status of each line in `src/data/estados_persistentes.json`.
- Counts consecutive detections to classify persistent problems.
- Prevents notification spam for the same problem.

### Differentiated alerts
- **Urgent alerts**: For new incidents or operational problems.
- **Work notifications**: For scheduled works (one time only).
- **Reminders**: For long-duration works (every 15 days).
- **Additional information**: For special schedules and complementary details.

## Environment variables

* `TELEGRAM_TOKEN`: Your Telegram bot token. (Required)
* `TELEGRAM_CHAT_ID`: Chat ID where alerts are sent. (Required)
* `INTERVALO_EJECUCION`: Interval between checks in seconds. (Default: 5400)
* `HORARIO_ANALISIS_INICIO`: Monitoring start hour, local time. (Default: 6)
* `HORARIO_ANALISIS_FIN`: Monitoring end hour, local time. (Default: 23)
* `UMBRAL_OBRA_PROGRAMADA`: Consecutive detections to classify as work. (Default: 5)
* `DIAS_RENOTIFICAR_OBRA`: Days between work reminders. (Default: 15)
* `DIAS_LIMPIAR_HISTORIAL`: Inactive days to remove a record from history. (Default: 5)

**Note on timezones:** The bot uses Buenos Aires timezone (America/Argentina/Buenos_Aires, UTC-3) for monitoring, regardless of the server's timezone where it runs. This ensures that the configured hours are respected correctly even when deployed on servers with different timezones (like Zeabur which uses UTC).

## Credits

- Developed by Agustin Monetti.
- Based on public information from EMOVA.
- GitHub: [@agmonetti](https://github.com/agmonetti)
- Email: agus.monetti01@gmail.com

---

## License
This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
