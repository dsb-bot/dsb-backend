import os
import sys
import time
import threading
import requests
import subprocess

# --- Prüfen, ob alle Parameter übergeben wurden ---
if len(sys.argv) < 7:
    print("Usage: python start_server.py <DSB_USER> <DSB_PASS> <GIT_USER> <GIT_TOKEN> <GIT_REPO> <DISCORD_WEBHOOK_WARN> <DISCORD_WEBHOOK_PLANS>")
    sys.exit(1)

DSB_USER = sys.argv[1]
DSB_PASS = sys.argv[2]
GIT_USER = sys.argv[3]
GIT_TOKEN = sys.argv[4]
GIT_REPO = sys.argv[5]
DISCORD_WEBHOOK_WARN = sys.argv[6]
DISCORD_WEBHOOK_PLANS = sys.argv[7]

# ---------------------------
# --- DISCORD WARNUNG ---
# ---------------------------
def send_discord_message(message: str):
    try:
        data = {
            "username": "DSB-Bot",
            "avatar_url": "https://www.dsbmobile.de/img/logo_dsbmobile.png",
            "content": message
        }
        response = requests.post(DISCORD_WEBHOOK_WARN, json=data)
        if response.status_code == 204:
            print(f" [LOG] Discord-Nachricht gesendet: {message}")
        else:
            print(f" [ERROR] Fehler beim Senden: {response.status_code}")
    except Exception as e:
        print(f" [ERROR] Nachricht konnte nicht gesendet werden: {e}")


def send_temp_warning():
    try:
        res = os.popen("vcgencmd measure_temp").readline()
        temp = float(res.replace("temp=", "").replace("'C\n", ""))
        print(f" [TEMP] Die CPU-Temperatur ist bei: {temp:.1f}°C")

        if temp > 60:
            send_discord_message(f"⚠️ Achtung! Die CPU-Temperatur ist hoch: {temp:.1f}°C")
    except Exception as e:
        print(f" [ERROR] Temperaturwarnung konnte nicht gesendet werden: {e}")


def temp_monitor():
    while True:
        send_temp_warning()
        time.sleep(60)


# ---------------------------
# --- BUILD BOT STARTEN ---
# ---------------------------
def build_bot():
    build_site_path = os.path.join(os.path.dirname(__file__), "server-build", "build_bot.py")

    # Python + Script + alle Parameter inklusive Discord Webhook für Pläne
    args = [
        sys.executable,
        build_site_path,
        DSB_USER,
        DSB_PASS,
        GIT_USER,
        GIT_TOKEN,
        GIT_REPO,
        DISCORD_WEBHOOK_PLANS
    ]

    try:
        subprocess.run(args, check=True)
        msg = " [LOG] build_bot.py erfolgreich ausgeführt."
        print(msg)
        send_discord_message(msg)
    except Exception as e:
        msg = f" [ERROR] build_bot.py konnte nicht ausgeführt werden: {e}"
        print(msg)
        send_discord_message(msg)


# ---------------------------
# --- SERVER STARTEN ---
# ---------------------------
def start_server():
    temp_thread = threading.Thread(target=temp_monitor, daemon=True)
    temp_thread.start()
    build_bot()


if __name__ == "__main__":
    start_server()
