# BookMyShow Movie Monitor (Coolie)

Monitor BookMyShow for ticket availability of a specific movie and receive instant notifications via Email, Webhook (Discord/Slack), or Telegram. Built with Python and Playwright.

---

## Features

- **Continuous Monitoring**: Scans BookMyShow for a target movie at regular intervals.
- **Multi-Channel Notifications**: Email (SMTP), Webhook (Discord/Slack), Telegram Bot.
- **Configurable**: Easily set movie name, interval, and notification settings via `config.json` or environment variables.
- **Single-Run Mode**: Script for CI/CD or cron jobs (`movie_monitor_single.py`).
- **Logging**: Logs events and errors to a file.

---

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies:
  - `requests`
  - `beautifulsoup4`
  - `lxml`
  - `playwright`

---

## Installation

1. **Clone the repository**
    ```bash
    git clone <your-repo-url>
    cd fdfs_coolie
    ```

2. **Install Python dependencies**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    playwright install
    ```

---

## Configuration

Edit `config.json` to set your preferences, or use environment variables for secrets (recommended for production/CI).

**Example `config.json`:**
```json
{
  "url": "https://in.bookmyshow.com/explore/movies-bengaluru?languages=tamil",
  "movie_name": "Coolie",
  "check_interval": 300,
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your@email.com",
    "sender_password": "yourpassword",
    "recipient_emails": ["to@email.com"]
  },
  "webhook": {
    "enabled": false,
    "url": ""
  },
  "telegram": {
    "enabled": false,
    "bot_token": "",
    "chat_id": ""
  },
  "logging": {
    "level": "INFO",
    "file": "movie_monitor.log"
  }
}
```

**Environment Variables Supported:**
- `SENDER_EMAIL`, `SENDER_PASSWORD`, `RECIPIENT_EMAILS`
- `WEBHOOK_URL`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `MOVIE_NAME`, `CHECK_INTERVAL`

---

## Notification Setup

### Telegram Bot Setup

1. **Create a Telegram Bot**
   - Open Telegram and search for `@BotFather`.
   - Start a chat and send `/newbot`.
   - Follow the prompts to name your bot and set a username.
   - After creation, you will receive a **bot token** (e.g., `123456789:ABCdefGhIJKLmnoPQRstuVwxyz1234567890`).

2. **Get Your Chat ID (for a user)**
   - Start a chat with your new bot (send any message).
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Look for `chat":{"id":<your_chat_id>,...}` in the JSON response. Use this as your `chat_id`.

3. **Get Chat ID for a Group**
   - Add your bot to the Telegram group.
   - Send a message in the group.
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Look for `chat":{"id":-<group_chat_id>,...}` (group chat IDs are negative numbers).
   - Use this negative number (including the `-`) as your `chat_id`.

### Gmail App Password (for Email Notifications)

If you use Gmail for sending emails, you must use an **App Password** (not your regular Gmail password):

1. Go to your [Google Account Security page](https://myaccount.google.com/security).
2. Enable **2-Step Verification** if not already enabled.
3. After enabling, go to the **App Passwords** section.
4. Select "Mail" as the app and "Other" for device (e.g., "MovieMonitor").
5. Generate the password and copy it. Use this as your `sender_password` in `config.json` or as the `SENDER_PASSWORD` environment variable.

---

## Usage

### 1. Continuous Monitoring (default)
```bash
python movie_monitor.py
```

### 2. Single-Run Mode (for CI/CD or cron jobs)
```bash
python movie_monitor_single.py
```
- Returns exit code 0 if movie found, 1 otherwise.

---

## Step-by-Step: Deploy on Free GCP E2 Micro VM

### 1. Create a Free E2 Micro VM
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Navigate to Compute Engine → VM Instances
- Click **Create Instance**
- Choose **e2-micro** (in a free-eligible region)
- Choose Ubuntu 22.04 LTS as OS
- Allow HTTP/HTTPS traffic if you want remote access
- Create and SSH into your VM

### 2. Install Python and Git
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

### 3. Install Playwright dependencies
```bash
sudo apt install -y wget libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libgbm1 libasound2 libxcomposite1 libxdamage1 libxrandr2 libgtk-3-0 libxshmfence1
```

### 4. Clone and Set Up the Project
```bash
git clone <your-repo-url>
cd fdfs_coolie
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install
```

### 5. Configure Notifications
- Edit `config.json` with your email/telegram/webhook details, or set environment variables for secrets.

### 6. Run the Monitor
```bash
python movie_monitor.py
```
- For single-run/cron: `python movie_monitor_single.py`

### 7. (Optional) Set up as a background service (systemd)
- Create a systemd service file to run the monitor on startup or as a background process.

### 8. (Optional) Set up a cron job (run every 5 minutes)
- To run the single-run script every 5 minutes, edit your crontab:

```bash
crontab -e
```

- Add the following line (replace `/path/to/fdfs_coolie` with your actual path):

```cron
*/5 * * * * cd /path/to/fdfs_coolie && /bin/bash -c 'source venv/bin/activate && python movie_monitor_single.py >> cron.log 2>&1'
```

- This will activate the virtual environment and run the monitor every 5 minutes, logging output to `cron.log`.

---

## Troubleshooting
- Ensure all dependencies are installed (`playwright install` is required!).
- Check `movie_monitor.log` for errors.
- For headless environments, Playwright runs in headless mode by default.

---

## License
MIT

---

## Credits
- Inspired by the need for instant movie ticket alerts!
- Developed by Manoj Raghavendran
