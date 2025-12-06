import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DSB_USER = os.getenv("DSB_USER")
    DSB_PASS = os.getenv("DSB_PASS")
    
    DSB_TEACHER_USER = os.getenv("DSB_TEACHER_USER")
    DSB_TEACHER_PASS = os.getenv("DSB_TEACHER_PASS")
    
    GIT_USER = os.getenv("GIT_USER")
    GIT_TOKEN = os.getenv("GIT_TOKEN")
    GIT_REPO = os.getenv("GIT_REPO")
    
    WEBHOOK_WARN = os.getenv("DISCORD_WEBHOOK_WARN")
    WEBHOOK_PLANS = os.getenv("DISCORD_WEBHOOK_PLANS")
    
    DISCORD_PING_ROLE_ID = os.getenv("DISCORD_PING_ROLE_ID", "")
    
    TEMP_THRESHOLD = float(os.getenv("TEMP_THRESHOLD", 75))
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    REPO_DIR = os.path.join(BASE_DIR, "dsb-database")
    PLANS_DIR = os.path.join(REPO_DIR, "plans")
    
    LOG_DIR = os.path.join(BASE_DIR, "logs")

    LOG_FILE = os.path.join(BASE_DIR, "dsb_bot.log")

    @staticmethod
    def validate():
        # Standard-Pflichtfelder
        required_base = [
            "DSB_USER", "DSB_PASS", 
            "GIT_USER", "GIT_TOKEN", "GIT_REPO"
        ]
        
        missing = [key for key in required_base if not os.getenv(key)]
        if missing:
            raise EnvironmentError(f"Fehlende Variablen in .env: {', '.join(missing)}")
        
        # Lehrer-Zugangsdaten sind optional, müssen aber entweder beide gesetzt oder beide leer sein.
        has_teacher_user = bool(os.getenv("DSB_TEACHER_USER"))
        has_teacher_pass = bool(os.getenv("DSB_TEACHER_PASS"))
        
        if has_teacher_user != has_teacher_pass:
            raise EnvironmentError("Wenn DSB_TEACHER_USER gesetzt ist, muss auch DSB_TEACHER_PASS gesetzt werden (und umgekehrt).")