import os
import time
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import Config
from dsb_client import DSBClient
from git_manager import GitManager
from discord_notifier import DiscordNotifier
from utils import logger # Logger importieren

class SubstitutionBot:
    def __init__(self):
        try:
            Config.validate()
        except EnvironmentError as e:
            logger.critical(f"FATAL: Konfigurationsfehler: {e}")
            raise

        self.dsb = DSBClient(Config.DSB_USER, Config.DSB_PASS)
        self.discord = DiscordNotifier(Config.WEBHOOK_WARN, Config.WEBHOOK_PLANS, Config.DISCORD_PING_ROLE_ID)
        
        self.git = GitManager(
            Config.GIT_USER, 
            Config.GIT_TOKEN, 
            Config.GIT_REPO, 
            Config.REPO_DIR
        )
        
        try:
            self.git.initialize_repo()
        except Exception as e:
            self.discord.send_warning(f"⚠️ Kritischer Git-Fehler beim Start: {e}")
            logger.critical(f"Kritischer Git-Fehler beim Start: {e}") 
        
        os.makedirs(Config.PLANS_DIR, exist_ok=True)
        
        self.last_plans = {}

    def _fetch_title(self, url):
        try:
            res = requests.get(url, timeout=10)
            res.encoding = res.apparent_encoding
            soup = BeautifulSoup(res.text, "html.parser")
            div = soup.find("div", class_="mon_title")
            return div.text.strip() if div else "Unbekannter Plan"
        except Exception:
            logger.warning(f"Konnte Titel für URL {url} nicht abrufen.", exc_info=True)
            return "Unbekannter Plan"

    def _save_html(self, url, title):
        try:
            # Dateinamen generieren
            try:
                date_part = title.split()[0]
                dt_obj = datetime.strptime(date_part, "%d.%m.%Y")
                filename = f"{dt_obj.strftime('%Y-%m-%d')}.html"
            except:
                safe_title = re.sub(r'[^0-9A-Za-z]+', "_", title)
                filename = f"{safe_title}.html"

            full_path = os.path.join(Config.PLANS_DIR, filename)
            
            res = requests.get(url)
            res.encoding = res.apparent_encoding
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(res.text)
            logger.info(f"Plan gespeichert: {full_path}")
            return True
        except Exception as e:
            logger.error(f"Konnte HTML nicht speichern für {url}: {e}", exc_info=True)
            return False

    def run_cycle(self):
        urls = self.dsb.fetch_menu_links()
        if not urls:
            return

        current_plans = {}
        for url in urls:
            title = self._fetch_title(url)
            current_plans[title] = {"url": url, "title": title}

        new_keys = set()
        updated = False

        for key, data in current_plans.items():
            if key not in self.last_plans or self.last_plans[key]['url'] != data['url']:
                new_keys.add(key)
                updated = True
                self._save_html(data['url'], data['title'])

        if updated:
            logger.info(f"Updates gefunden: {list(new_keys)}")
            self.discord.send_plan_update(current_plans, new_keys)
            self.git.push_changes()
            self.last_plans = current_plans
        else:
            logger.debug("Keine neuen Updates gefunden.")

    def start(self):
        logger.info("Bot gestartet.")
        self.discord.send_warning("🤖 Bot wurde neu gestartet.")
        
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                err_msg = f"Fehler im Hauptloop: {e}"
                logger.error(err_msg, exc_info=True) 
                self.discord.send_warning(f" [CRASH] {err_msg}")
            
            now = time.localtime()
            time.sleep(60 - now.tm_sec)