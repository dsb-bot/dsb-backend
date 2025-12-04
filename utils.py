import os
import logging
import datetime
from logging.handlers import RotatingFileHandler
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
    try:
        res = os.popen("vcgencmd measure_temp").readline()
        temp = float(res.replace("temp=", "").replace("'C\n", ""))
        return temp
    except Exception:
        return None

def ConvertTeacherToStudent(teacher_html: str) -> list[str]:
    """Dummy-Funktion zur Konvertierung eines Lehrerplans (HTML-String) in eine Liste von Schülerplänen (HTML-Strings).
    
    Diese Dummy-Implementierung gibt den übergebenen String einfach als Liste zurück,
    damit die Bot-Logik getestet werden kann. In der finalen Version muss hier 
    die Logik zur Filterung und Aufteilung des Lehrerplans implementiert werden.
    """
    # Gibt den kompletten HTML-String als einziges Element in einer Liste zurück.
    return [teacher_html]