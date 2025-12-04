import os
import time
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
# Import der Konvertierungsfunktion aus utils
from utils import logger, ConvertTeacherToStudent

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

        # Speichere den Zustand: {'unique_key': {'detail': '...', 'date': '...', 'title': '...'}, ...}
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

    def _save_content_by_date(self, html_content: str, title: str, identifier: str) -> bool:
        """Speichert den HTML-Inhalt im plans/ Ordner, extrahiert Datum und benennt die Datei.
        Konvertierte Pläne erhalten ein Suffix zur Eindeutigkeit.
        """
        try:
            # 1. Datum aus dem HTML-Inhalt extrahieren (Kernlogik)
            soup = BeautifulSoup(html_content, "html.parser")
            mon_title_div = soup.find("div", class_="mon_title")

            date_str_to_parse = None
            if mon_title_div:
                full_title_text = mon_title_div.text.strip()
                # Regex erlaubt 1 oder 2 Ziffern für Tag und Monat
                match = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4})", full_title_text)

                if match:
                    date_str_to_parse = match.group(1)

            # 2. Dateinamen bestimmen
            if date_str_to_parse:
                dt_obj = datetime.strptime(date_str_to_parse, "%d.%m.%Y")
                date_str = dt_obj.strftime("%Y-%m-%d")
            else:
                logger.warning(
                    f"Konnte Datum nicht aus HTML für '{identifier}' extrahieren. Nutze aktuelles Datum."
                )
                date_str = datetime.now().strftime("%Y-%m-%d")

            # 3. Dateinamen-Logik: YYYY-MM-DD.html
            # HINWEIS: Wenn 'converted_' im Identifier enthalten ist und ConvertTeacherToStudent
            # mehrere Pläne für dasselbe Datum liefert, werden diese sich aufgrund des
            # identischen Dateinamens gegenseitig überschreiben.
            filename = f"{date_str}.html"

            full_path = os.path.join(Config.PLANS_DIR, filename)

            # 4. HTML-Inhalt speichern
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            logger.info(f"Plan gespeichert ({title}): {full_path}")
            return True
        except Exception as e:
            logger.error(f"Konnte HTML nicht speichern für '{identifier}': {e}", exc_info=True)
            return False

    def _save_html_from_url(self, url: str, title: str) -> bool:
        """Wrapper, der HTML von einer URL abruft und _save_content_by_date aufruft."""
        try:
            # Planinhalt abrufen
            res = requests.get(url, timeout=10)
            res.encoding = res.apparent_encoding
            html_content = res.text
            
            # Kernlogik auslagern
            return self._save_content_by_date(html_content, title, url)
            
        except Exception as e:
            logger.error(f"Konnte HTML nicht von URL ({url}) abrufen: {e}", exc_info=True)
            return False

    def run_cycle_student(self):
        """Regulärer Abruf der Schülerpläne (Heute/Morgen) und Verarbeitung des Lehrerplans."""
        logger.debug("Starte Schüler-Abrufzyklus.")
        plan_objects = self.dsb_student.fetch_menu_links()

        if not plan_objects:
            logger.warning("Keine Plan-Objekte vom Schüler-Account abgerufen.")
            return

        current_plans = {}
        new_keys = set()
        
        # Zähler für konvertierte Pläne, um eindeutige Schlüssel zu erzeugen
        converted_counter = 0

        for plan_data in plan_objects:
            url = plan_data["detail"]
            title = plan_data["title"]

            if title == "Lehrerzimmer heute":
                # Fall 1: "Lehrerzimmer heute" soll ignoriert werden
                logger.debug(f"Plan '{title}' ignoriert.")
                continue

            elif title == "Lehrerzimmer morgen":
                # Fall 2: "Lehrerzimmer morgen" muss konvertiert werden
                logger.info(f"Verarbeite Lehrerplan zur Konvertierung: {url}")
                
                try:
                    # 1. HTML-Inhalt des Lehrerplans abrufen
                    res = requests.get(url, timeout=10)
                    res.encoding = res.apparent_encoding
                    teacher_html = res.text
                    
                    # 2. Inhalt konvertieren (erwartet: Liste von HTML-Strings für Schülerpläne)
                    converted_html_plans = ConvertTeacherToStudent(teacher_html)
                    
                    if not converted_html_plans:
                        logger.warning("Konvertierung des Lehrerplans lieferte keine Ergebnisse.")
                        continue
                    
                    # 3. Verarbeite jeden konvertierten HTML-Plan
                    for html_content in converted_html_plans:
                        converted_counter += 1
                        
                        # Temporäre Titel/Datumsextraktion nur für Zustand/Logs
                        soup = BeautifulSoup(html_content, "html.parser")
                        mon_title_div = soup.find("div", class_="mon_title")
                        
                        # Generiere einen eindeutigen Schlüssel
                        date_tag = datetime.now().strftime("%Y%m%d")
                        unique_key = f"converted_{date_tag}_{converted_counter}"
                        
                        new_title = mon_title_div.text.strip() if mon_title_div else f"Konvertierter Plan {converted_counter}"

                        # Prüfen, ob dieser konvertierte Plan neu ist (der Key ist temporär und basiert auf der Reihenfolge)
                        is_new = unique_key not in self.last_plans_student
                        
                        if is_new:
                            # 4. Speichern des HTML-Inhalts unter Verwendung der neuen Methode
                            if self._save_content_by_date(html_content, new_title, unique_key):
                                # 5. Zum Zustand hinzufügen und auf Update prüfen
                                new_plan_data = {
                                    "detail": unique_key, # Interner Schlüssel für das Tracking
                                    "title": new_title,
                                    "date": datetime.now().isoformat(), 
                                    "original_url": url, # NEU: Füge die Lehrer-URL hinzu, die für Discord verwendet werden soll
                                }
                                current_plans[unique_key] = new_plan_data
                                new_keys.add(unique_key)
                                logger.info(f"Konvertierungsziel als Neu/Update markiert: {new_title} (Key: {unique_key}, Original-URL für Discord: {url})")
                            else:
                                logger.error(f"Speichern des konvertierten Plans {new_title} fehlgeschlagen.")
                        # Wenn er nicht neu ist, wird er ignoriert, da wir keine bessere Verfolgung haben.

                except Exception as e:
                    logger.error(f"Fehler bei Konvertierung des Lehrerplans {url}: {e}", exc_info=True)
                
                # Wir überspringen die weitere Standardverarbeitung für diesen Lehrerplan.
                continue 

            # Fall 3: Standard-Pläne ("DSB App Schüler", "DSB App SuS morgen" und alle anderen)
            
            # Speichere das gesamte Plan-Objekt unter der URL als Schlüssel
            current_plans[url] = plan_data
            
            date = plan_data["date"] # Zeitstempel aus Metadaten

            # Prüfe, ob die URL neu ist ODER ob sich die Metadaten (Titel/Datum) geändert haben.
            last_data = self.last_plans_student.get(url)

            is_new = url not in self.last_plans_student
            is_updated = last_data and (
                # Prüfen auf Änderung von Titel oder Zeitstempel (date)
                last_data.get("title") != title
                or last_data.get("date") != date
            )

            if is_new or is_updated:
                # Verwende die Wrapper-Methode, die den Inhalt von der URL abruft
                self._save_html_from_url(url, title)
                new_keys.add(url)

        # Der Rest des Zyklus (Discord/Git) bleibt gleich, da er mit new_keys und current_plans arbeitet.

        updated = bool(new_keys)

        if updated:
            logger.info(f"Schüler-Updates gefunden: {list(new_keys)}")
            self.discord.send_plan_update(current_plans, new_keys)
            self.git.push_changes(message="Schülerplan Update (Heute/Morgen/Konvertiert)")

        # Aktualisiere den Zustand mit allen Plänen (Original und Konvertiert)
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