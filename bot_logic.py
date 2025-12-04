import os
import time
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from utils import logger

from config import Config
from dsb_client import DSBClient
from git_manager import GitManager
from discord_notifier import DiscordNotifier


class SubstitutionBot:
    def __init__(self):
        try:
            Config.validate()
        except EnvironmentError as e:
            logger.critical(f"FATAL: Konfigurationsfehler: {e}")
            raise

        # 1. Client für Schüler-Account (Standard)
        self.dsb_student = DSBClient(Config.DSB_USER, Config.DSB_PASS)

        self.discord = DiscordNotifier(
            Config.WEBHOOK_WARN, Config.WEBHOOK_PLANS, Config.DISCORD_PING_ROLE_ID
        )

        self.git = GitManager(
            Config.GIT_USER, Config.GIT_TOKEN, Config.GIT_REPO, Config.REPO_DIR
        )

        try:
            self.git.initialize_repo()
        except Exception as e:
            self.discord.send_warning(f"⚠️ Kritischer Git-Fehler beim Start: {e}")
            logger.critical(f"Kritischer Git-Fehler beim Start: {e}")

        os.makedirs(Config.PLANS_DIR, exist_ok=True)
        
        # Speichere den Zustand
        self.last_plans_student = {}

    def _fetch_title(self, url):
        """Ruft den Titel (Datum und Tag) eines Vertretungsplans ab."""
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
        """Speichert den HTML-Plan im plans/ Ordner und benennt ihn nach Datum."""
        try:
            # Versuche, ein Datum aus dem Titel zu extrahieren (z.B. 04.12.2025)
            match = re.search(r'(\d{2}\.\d{2}\.\d{4})', title)
            
            if match:
                dt_obj = datetime.strptime(match.group(1), '%d.%m.%Y')
                date_str = dt_obj.strftime('%Y-%m-%d')
            else:
                # Fallback, sollte nicht passieren
                date_str = datetime.now().strftime('%Y-%m-%d')
            
            filename = f"{date_str}.html" 
            full_path = os.path.join(Config.PLANS_DIR, filename)
            
            res = requests.get(url)
            res.encoding = res.apparent_encoding
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(res.text)
            logger.info(f"Plan gespeichert (Schüler/Heute-Morgen): {full_path}")
            return True
        except Exception as e:
            logger.error(f"Konnte HTML nicht speichern für {url}: {e}", exc_info=True)
            return False

    def run_cycle_student(self):
        """Regulärer Abruf der Schülerpläne (Heute/Morgen)."""
        logger.debug("Starte Schüler-Abrufzyklus.")
        urls = self.dsb_student.fetch_menu_links()

        if not urls:
            logger.warning("Keine URLs vom Schüler-Account abgerufen.")
            return

        current_plans = {}
        new_keys = set()

        for url in urls:
            title = self._fetch_title(url)
            current_plans[url] = {"url": url, "title": title}

            # Prüfe, ob die URL neu ist oder der Titel sich geändert hat
            if (
                url not in self.last_plans_student
                or self.last_plans_student[url]["title"] != title
            ):
                self._save_html(url, title) 
                new_keys.add(url)

        updated = bool(new_keys)

        if updated:
            logger.info(f"Schüler-Updates gefunden: {list(new_keys)}")
            self.discord.send_plan_update(current_plans, new_keys)
            self.git.push_changes(message="Schülerplan Update (Heute/Morgen)")

        self.last_plans_student = current_plans
        if not updated:
            logger.debug("Keine neuen Schüler-Updates gefunden.")
            
    def start(self):
        """Startet den Haupt-Bot-Zyklus."""
        logger.info("Bot gestartet.")
        self.discord.send_warning("🤖 Bot wurde neu gestartet.")
        
        while True:
            # --- 1. Standard-Zyklus (Schüler) ---
            self.run_cycle_student()
            
            # --- 2. Warte bis zur nächsten vollen Minute ---
            try:
                time_to_wait = 60 - time.localtime().tm_sec
                time.sleep(time_to_wait)
            except Exception as e:
                err_msg = f"Fehler beim Warten: {e}"
                logger.error(err_msg, exc_info=True) 
                self.discord.send_warning(f" [CRASH] {err_msg}")