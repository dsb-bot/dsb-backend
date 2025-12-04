import requests
from utils import get_cpu_temperature, logger # Importiere den Logger

class DiscordNotifier:
    # Füge ping_role_id zum Konstruktor hinzu
    def __init__(self, warn_url, plans_url, ping_role_id): 
        self.warn_url = warn_url
        self.plans_url = plans_url
        self.ping_role_id = ping_role_id

    def send_warning(self, message):
        logger.warning(f"Discord-Warnung wird gesendet: {message}") 
        
        if not self.warn_url:
            return

        # Rollen-Ping hinzufügen, wenn eine ID konfiguriert ist
        content = message
        if self.ping_role_id:
            # Discord erwartet die Rolle im Format <@&ID>
            content = f"<@&{self.ping_role_id}> {message}"
            
        try:
            response = requests.post(self.warn_url, json={"username": "DSB-Monitor", "content": content})
            if response.status_code not in (204, 200):
                logger.error(f"Discord Warnung failed with status {response.status_code}: {response.text}")
            else:
                logger.info("Discord-Warnung erfolgreich gesendet.")
        except Exception as e:
            logger.error(f"Discord Warnung konnte nicht gesendet werden: {e}")

    def send_plan_update(self, plans, new_keys):
        if not self.plans_url:
            return

        fields = []
        for key in plans:
            title = plans[key]['title']
            if key in new_keys:
                title += " 🌟 (neu)"
            
            fields.append({
                "name": title,
                "value": f"[Vertretungsplan öffnen]({plans[key]['url']})",
                "inline": False
            })

        temp = get_cpu_temperature()
        temp_str = f"{temp:.1f}°C" if temp else "?"

        data = {
            "username": "DSB-Bot",
            "avatar_url": "https://www.dsbmobile.de/img/logo_dsbmobile.png",
            "embeds": [{
                "title": "Aktuelle Vertretungspläne",
                "color": 0x1abc9c,
                "fields": fields,
                "footer": {
                    "text": f"System Temp: {temp_str}",
                    # "icon_url": "..." 
                }
            }]
        }
        try:
            response = requests.post(self.plans_url, json=data)
            if response.status_code == 204:
                logger.info("Discord Plan-Update erfolgreich gesendet.")
            else:
                logger.error(f"Discord Plan-Update fehlgeschlagen: {response.status_code}, {response.text}")
        except Exception as e:
            logger.error(f"Discord Plan-Update konnte nicht gesendet werden: {e}")