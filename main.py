import threading
import time
from config import Config
# Importiere Logger und das Setup
from utils import get_cpu_temperature, logger, setup_logging 
from discord_notifier import DiscordNotifier
from bot_logic import SubstitutionBot

def monitor_system(notifier):
    while True:
        temp = get_cpu_temperature()
        if temp:
            logger.debug(f"Aktuelle Temperatur: {temp:.1f}°C")
            if temp > Config.TEMP_THRESHOLD:
                msg = f"Hitzewarnung: {temp:.1f}°C"
                logger.warning(msg)
                notifier.send_warning(f"⚠️ {msg}")
        
        time.sleep(60)

if __name__ == "__main__":
    # 1. Logging konfigurieren
    setup_logging() 
    
    try:
        # 2. Konfiguration validieren
        Config.validate()
        
        # 3. Notifier initialisieren (mit Rollen-ID)
        notifier = DiscordNotifier(Config.WEBHOOK_WARN, Config.WEBHOOK_PLANS, Config.DISCORD_PING_ROLE_ID)
    except EnvironmentError as e:
        logger.critical(f"FATAL: Konfigurationsfehler: {e}. Bitte .env überprüfen.")
        exit(1)

    # 4. Monitor Thread starten
    logger.info("Starte System Monitor Thread...")
    threading.Thread(target=monitor_system, args=(notifier,), daemon=True).start()

    # 5. Bot initialisieren und starten
    try:
        bot = SubstitutionBot()
        bot.start()
    except KeyboardInterrupt:
        logger.info("Beende Bot durch Benutzer (KeyboardInterrupt)...")
    except Exception as e:
        logger.critical(f"FATAL: Bot Start fehlgeschlagen: {e}", exc_info=True)