import os
import logging
import datetime # NEU: Für den Zeitstempel
from logging.handlers import RotatingFileHandler # Wird nicht mehr genutzt, aber ggf. gut zu wissen
from config import Config

logger = logging.getLogger('DSBBot')

def setup_logging():
    """Konfiguriert den Logger für Console und File mit einem neuen, zeitgestempelten Log-File."""
    logger.setLevel(logging.DEBUG)
    
    # 1. Sicherstellen, dass der Log-Ordner existiert
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    
    # 2. Einzigartigen Dateinamen generieren (Format: JJJJMMTT_HHMMSS)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(Config.LOG_DIR, f"{timestamp}.log")

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    # Bestehende Handler entfernen, um doppelte Ausgaben zu verhindern
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Standard File Handler für neue Datei pro Start
    fh = logging.FileHandler(log_filename, encoding='utf-8')
    fh.setLevel(logging.INFO) 
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.info("Logging initialisiert. Neue Log-Datei: %s", log_filename)


def get_cpu_temperature():
    """Liest die CPU-Temperatur des Raspberry Pi aus."""
    # ... (Logik bleibt gleich)
    try:
        res = os.popen("vcgencmd measure_temp").readline()
        temp = float(res.replace("temp=", "").replace("'C\n", ""))
        return temp
    except Exception:
        return None