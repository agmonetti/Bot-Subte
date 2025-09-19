# Buenos Aires Subway Alerts Bot

This project is an automated bot that monitors the status of Buenos Aires subway lines and sends intelligent alerts to Telegram whenever it detects changes in service.

## How it works

* Uses **Selenium** to navigate and extract the status of each line from the official EMOVA website.
* **Intelligent classification system**: Automatically distinguishes between urgent incidents and scheduled maintenance.
* **Granular processing**: Analyzes each sentence individually to detect multiple components per line.
* **State persistence**: Keeps a history of issues to avoid repeated notifications.
* **Differentiated alerts**: Sends different types of messages depending on the nature of the problem.
* Checks run periodically (default every 1.5 hours).

## Main Features

### Detection

* **Scheduled maintenance**: Automatically detects major renovations and planned maintenance.
* **Incidents**: Identifies operational problems requiring immediate attention.
* **Service recovery**: Notifies when lines return to normal operation.
* **Multiple components**: Can detect maintenance, incidents, and additional info for the same line.

### History system

* Stores the status of each line in `estados_persistentes.json`.
* Counts consecutive detections to classify persistent problems.
* Prevents spam notifications for the same issue.

### Differentiated alerts

* **Urgent alerts**: For new incidents or operational problems.
* **Maintenance notifications**: For scheduled works (one-time alert).
* **Reminders**: For long-term works (every 15 days).
* **Additional information**: For special schedules and supplementary details.

## Requirements

* Python 3.10+
* Docker (optional, recommended for easier deployment)
* A Telegram bot and the chat ID to send alerts
* Local or cloud hosting

## Installation and Usage

### Option 1: Docker (Recommended)

1. Clone this repository.
2. Create a `.env` file with your credentials:

   ```env
   TELEGRAM_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```
3. Build the Docker image:

   ```sh
   docker build -t subway-bot .
   ```
4. Run the container:

   ```sh
   docker run --rm subway-bot
   ```

### Option 2: Manual

1. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```
2. Create a `.env` file with your credentials (see example above).
3. Run the bot:

   ```sh
   python subte_alerta.py
   ```

## Advanced Configuration

* `INTERVALO_EJECUCION`: Check interval in seconds (default: 5400 = 1.5 hours)
* `UMBRAL_OBRA_PROGRAMADA`: Consecutive detections required to classify as scheduled maintenance (default: 5)
* `DIAS_RENOTIFICAR_OBRA`: Days between reminders for scheduled works (default: 15)

## Environment Variables

| Variable           | Description             |
| ------------------ | ----------------------- |
| `TELEGRAM_TOKEN`   | Your Telegram bot token |
| `TELEGRAM_CHAT_ID` | Chat ID to send alerts  |

## Credits

* Developed by **Agustín Monetti**
* Based on publicly available information from EMOVA
* GitHub: [@agmonetti](https://github.com/agmonetti)
* Email: [agmonetti@uade.edu.ar](mailto:agmonetti@uade.edu.ar)

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**
