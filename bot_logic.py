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

        # Speichere den Zustand: {'url_des_plans': {'detail': '...', 'date': '...', 'title': '...'}, ...}
        self.last_plans_student = {}

    def _fetch_title(self, url):
        """Ruft den Titel (Datum und Tag) eines Vertretungsplans ab, indem die HTML-Seite geparsed wird."""
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
        """Speichert den HTML-Plan im plans/ Ordner und benennt ihn nach Datum.
        Das Datum wird direkt aus dem HTML-Inhalt extrahiert (unterstützt D.M.YYYY und DD.MM.YYYY).
        """
        try:
            # Planinhalt abrufen
            res = requests.get(url, timeout=10)
            res.encoding = res.apparent_encoding
            html_content = res.text

            # 1. Datum aus dem HTML-Inhalt extrahieren
            soup = BeautifulSoup(html_content, "html.parser")
            mon_title_div = soup.find("div", class_="mon_title")

            date_str_to_parse = None
            if mon_title_div:
                # Textinhalt des div (z.B. "5.12.2025 Freitag, Woche B" oder "05.12.2025 Freitag, Woche B")
                full_title_text = mon_title_div.text.strip()

                match = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4})", full_title_text)

                if match:
                    date_str_to_parse = match.group(
                        1
                    )  # z.B. "5.12.2025" oder "05.12.2025"

            if date_str_to_parse:
                # Datumsobjekt erstellen. %d und %m verarbeiten automatisch 1- oder 2-stellige Eingaben.
                # (z.B. strptime('5.12.2025', '%d.%m.%Y') funktioniert)
                dt_obj = datetime.strptime(date_str_to_parse, "%d.%m.%Y")
                # Format für Dateinamen: YYYY-MM-DD
                date_str = dt_obj.strftime("%Y-%m-%d")
            else:
                # Fallback, falls kein Datum gefunden wurde
                logger.warning(
                    f"Konnte Datum nicht aus HTML für URL {url} extrahieren. Nutze aktuelles Datum."
                )
                date_str = datetime.now().strftime("%Y-%m-%d")

            filename = f"{date_str}.html"
            full_path = os.path.join(Config.PLANS_DIR, filename)

            # 2. HTML-Inhalt speichern
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(
                f"Plan gespeichert (Schüler/Heute-Morgen) mit Datum aus HTML: {full_path}"
            )
            return True
        except Exception as e:
            logger.error(f"Konnte HTML nicht speichern für {url}: {e}", exc_info=True)
            return False

    def run_cycle_student(self):
        """Regulärer Abruf der Schülerpläne (Heute/Morgen)."""
        logger.debug("Starte Schüler-Abrufzyklus.")
        # NEU: Erwarte eine Liste von Plan-Objekten (Dictionaries)
        plan_objects = self.dsb_student.fetch_menu_links()

        if not plan_objects:
            logger.warning("Keine Plan-Objekte vom Schüler-Account abgerufen.")
            return

        current_plans = {}
        new_keys = set()

        # Iteriere über die Plan-Objekte (die Dictionaries mit 'detail', 'title', 'date')
        for plan_data in plan_objects:
            # Der Link, der als eindeutiger Schlüssel dient, ist unter 'detail'
            url = plan_data["detail"]
            title = plan_data["title"]  # Titel aus Metadaten
            date = plan_data["date"]  # Zeitstempel aus Metadaten

            # Speichere das gesamte Plan-Objekt unter der URL als Schlüssel
            current_plans[url] = plan_data

            # Prüfe, ob die URL neu ist ODER ob sich die Metadaten (Titel/Datum) geändert haben.
            last_data = self.last_plans_student.get(url)

            is_new = url not in self.last_plans_student
            is_updated = last_data and (
                # Prüfen auf Änderung von Titel oder Zeitstempel (date)
                last_data.get("title") != title
                or last_data.get("date") != date
            )

            if is_new or is_updated:
                # _save_html verwendet den übergebenen Titel, um das Datum für den Dateinamen zu extrahieren.
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
