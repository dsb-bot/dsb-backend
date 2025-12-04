import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DSB_USER = os.getenv("DSB_USER")
    DSB_PASS = os.getenv("DSB_PASS")
    GIT_USER = os.getenv("GIT_USER")
    GIT_TOKEN = os.getenv("GIT_TOKEN")
    GIT_REPO = os.getenv("GIT_REPO")
    
    WEBHOOK_WARN = os.getenv("DISCORD_WEBHOOK_WARN")
    WEBHOOK_PLANS = os.getenv("DISCORD_WEBHOOK_PLANS")
    
    # NEU: Discord Rolle für Pings
    DISCORD_PING_ROLE_ID = os.getenv("DISCORD_PING_ROLE_ID", "")
    
    TEMP_THRESHOLD = float(os.getenv("TEMP_THRESHOLD", 75))
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    REPO_DIR = os.path.join(BASE_DIR, "dsb-database")
    PLANS_DIR = os.path.join(REPO_DIR, "plans")
    
    LOG_DIR = os.path.join(BASE_DIR, "logs")

    # NEU: Log Datei Pfad
    LOG_FILE = os.path.join(BASE_DIR, "dsb_bot.log")

    @staticmethod
    def validate():
        required = ["DSB_USER", "DSB_PASS", "GIT_USER", "GIT_TOKEN", "GIT_REPO"]
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise EnvironmentError(f"Fehlende Variablen in .env: {', '.join(missing)}")