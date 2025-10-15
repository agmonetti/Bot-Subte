# Buenos Aires Subway Alert Bot

This project is an automated bot that monitors the status of Buenos Aires subway lines and sends intelligent alerts to Telegram when it detects service changes.

## How does it work?

- Uses Selenium to navigate and extract the status of each line from the official EMOVA website.
- **Intelligent classification system**: Automatically distinguishes between urgent incidents and scheduled works.
- **Granular processing**: Analyzes each sentence independently to detect multiple components per line.
- **State persistence**: Maintains a history of problems to avoid repetitive notifications.
- **Differentiated alerts**: Sends different types of messages according to the nature of the problem.
- Checking is performed periodically (by default, every 1.5 hours).

## Main Features

### Schedule system
- **Intelligent wait calculation**: Automatically determines when to reactivate based on current time
- **Optimized operation**: Works respecting defined schedules

### Detection 
- **Scheduled works**: Automatically detects comprehensive renovation works and scheduled maintenance
- **Incidents**: Identifies operational problems that require immediate attention
- **Service recovery**: Notifies when lines return to normal operation
- **Multiple components**: Can detect works, problems and additional information on the same line

### History system
- Saves the status of each line in `estados_persistentes.json`
- Counts consecutive detections to classify persistent problems
- Prevents notification spam for the same problem

### Differentiated alerts
- **Urgent alerts**: For new incidents or operational problems
- **Work notifications**: For scheduled works (one time only)
- **Reminders**: For long-duration works (every 15 days)
- **Additional information**: For special schedules and complementary details

## Requirements

- Python 3.10+
- Docker (optional, recommended for easier execution)
- A Telegram bot and the chat ID where to send alerts
- Local / Cloud hosting

## Installation and usage

### Option 1: Docker (Recommended)

1. Clone this repository.
2. Create a `.env` file with your credentials:
   ```env
   TELEGRAM_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```
3. Build the image:
   ```sh
   docker build -t bot-subte .
   ```
4. Run the container:
   ```sh
   docker run --rm bot-subte
   ```

### Option 2: Manual

1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Create a `.env` file with your credentials (see example above)
3. Run the bot:
   ```sh
   python subte_alerta.py
   ```

## Environment variables
| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_TOKEN` | Your Telegram bot token | - |
| `TELEGRAM_CHAT_ID` | Chat ID where alerts are sent | - |
| `intervalo_ejecucion` | Interval between checks (seconds) | 5400 |
| `horario_analisis_inicio` | Monitoring start hour | 6 |
| `horario_analisis_fin` | Monitoring end hour | 23 |
| `umbral_obra_programada` | Detections to classify as work | 5 |
| `dias_renotificar_obra` | Days between work reminders | 15 |
| `dias_limpiar_historial` | Days to clean old history | 5 |

## Credits

- Developed by Agustin Monetti.
- Based on public information from EMOVA.
- GitHub: [@agmonetti](https://github.com/agmonetti)
- Email: agmonetti@uade.edu.ar

---

## License
This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).