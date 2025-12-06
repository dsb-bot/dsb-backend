import os
import time
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from utils import logger
from teacher_to_student_converter import ConvertTeacherToStudent

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

        # --- Client-Initialisierung (Schüler ist Pflicht, Lehrer ist optional) ---

        # 1. Schüler-Account (Standard)
        self.dsb_student = DSBClient(Config.DSB_USER, Config.DSB_PASS)
        # Zustandsspeicher für Schüler-Pläne (Standard & Konvertiert)
        self.last_plans_student = {}

        # 2. Lehrer-Account (Optional)
        self.dsb_teacher = None
        self.last_plans_teacher = {}
        if Config.DSB_TEACHER_USER and Config.DSB_TEACHER_PASS:
            self.dsb_teacher = DSBClient(
                Config.DSB_TEACHER_USER, Config.DSB_TEACHER_PASS
            )
            logger.info("Lehrer-Account wurde erfolgreich initialisiert.")

        # Liste aller zu verarbeitenden Clients
        self.clients = [
            {
                "client": self.dsb_student,
                "state": self.last_plans_student,
                "name": "Schüler",
            }
        ]
        if self.dsb_teacher:
            self.clients.append(
                {
                    "client": self.dsb_teacher,
                    "state": self.last_plans_teacher,
                    "name": "Lehrer",
                }
            )

        # --- Sonstige Initialisierung ---

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

    def _extract_plan_date(self, html_content: str) -> datetime | None:
        """Extrahiert das Datum (als datetime-Objekt) aus dem HTML-Inhalt des Plans.

        Sucht im 'mon_title' Div nach dem Muster DD.MM.YYYY.
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            mon_title_div = soup.find("div", class_="mon_title")
            date_str_to_parse = None

            if mon_title_div:
                full_title_text = mon_title_div.text.strip()
                # Regex sucht nach DD.MM.YYYY oder D.M.YYYY
                match = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4})", full_title_text)

                if match:
                    date_str_to_parse = match.group(1)

            if date_str_to_parse:
                # Versucht, das Datum zu parsen
                # Die Zeitkomponenten werden auf 0 gesetzt, um nur das Datum zu vergleichen
                dt_obj = datetime.strptime(date_str_to_parse, "%d.%m.%Y")
                return dt_obj.replace(hour=0, minute=0, second=0, microsecond=0)

            return None
        except Exception as e:
            logger.warning(f"Fehler beim Extrahieren des Datums aus dem Plan: {e}")
            return None

    def _get_n_working_days_from_now(self, n: int) -> datetime:
        """Berechnet das Datum, das n Arbeitstage (Mo-Fr) in der Zukunft liegt.

        Args:
            n: Die Anzahl der Arbeitstage, die addiert werden sollen.

        Returns:
            Ein datetime-Objekt, das den Start des berechneten Tages darstellt.
        """
        target_date = datetime.now().date()
        days_added = 0

        # Gehe Tag für Tag vor, bis n Arbeitstage hinzugefügt wurden
        while days_added < n:
            target_date += timedelta(days=1)
            # Montag (0) bis Freitag (4) sind Arbeitstage
            if target_date.weekday() < 5:
                days_added += 1

        # Konvertiere das Date-Objekt in ein Datetime-Objekt (mit Zeit 00:00:00)
        return datetime.combine(target_date, datetime.min.time())

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

    def _save_content_by_date(
        self, html_content: str, title: str, identifier: str
    ) -> bool:
        """Speichert den HTML-Inhalt im plans/ Ordner, extrahiert Datum und benennt die Datei."""
        try:
            # 1. Datum aus dem HTML-Inhalt extrahieren (Kernlogik)
            dt_obj = self._extract_plan_date(html_content)

            # 2. Dateinamen bestimmen
            if dt_obj:
                # Verwende das extrahierte Datum für den Dateinamen
                date_str = dt_obj.strftime("%Y-%m-%d")
            else:
                logger.warning(
                    f"Konnte Datum nicht aus HTML für '{identifier}' extrahieren. Nutze aktuelles Datum."
                )
                # Fallback auf das aktuelle Datum
                date_str = datetime.now().strftime("%Y-%m-%d")

            # 3. Dateinamen-Logik: YYYY-MM-DD.html
            filename = f"{date_str}.html"

            full_path = os.path.join(Config.PLANS_DIR, filename)

            # 4. HTML-Inhalt speichern
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info(f"Plan gespeichert ({title}): {full_path}")
            return True
        except Exception as e:
            logger.error(
                f"Konnte HTML nicht speichern für '{identifier}': {e}", exc_info=True
            )
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
            logger.error(
                f"Konnte HTML nicht von URL ({url}) abrufen: {e}", exc_info=True
            )
            return False

    def _process_client_cycle(
        self, client: DSBClient, last_plans: dict, client_name: str
    ) -> tuple[dict, dict, set]:
        """Führt einen Abrufzyklus für einen bestimmten DSBClient durch.

        Gibt den aktualisierten Zustand (current_plans), den aktualisierten Zustand
        der konvertierten Pläne und die neuen/geänderten Keys zurück.
        """
        logger.debug(f"Starte Abrufzyklus für {client_name}-Account.")
        plan_objects = client.fetch_menu_links()

        if not plan_objects:
            logger.warning(f"Keine Plan-Objekte vom {client_name}-Account abgerufen.")
            return {}, set()

        # current_plans enthält alle Standardpläne (Key=URL) und neu konvertierte Pläne (Key=converted_...)
        current_plans = {}
        new_keys = set()
        converted_counter = 0

        # Berechne den Mindest-Werktag (zwei Arbeitstage von heute, also übermorgen oder später)
        min_working_day = self._get_n_working_days_from_now(2)
        logger.debug(
            f"Konvertierung von Lehrerplänen nur für Pläne ab: {min_working_day.strftime('%d.%m.%Y')}"
        )

        for plan_data in plan_objects:
            url = plan_data["detail"]
            title = plan_data["title"]

            # **********************************************
            # Teil 1: Lehrerplan-Konvertierung
            # **********************************************

            # Ignoriere "Lehrerzimmer heute"
            if title == "Lehrerzimmer heute":
                logger.debug(f"Plan '{title}' ignoriert.")
                continue

            # Verarbeite "Lehrerzimmer morgen" zur Konvertierung
            elif title == "Lehrerzimmer morgen":
                logger.info(
                    f"Verarbeite Lehrerplan zur Konvertierung von {client_name}: {url}"
                )

                try:
                    # 1. HTML-Inhalt des Lehrerplans abrufen
                    res = requests.get(url, timeout=10)
                    res.encoding = res.apparent_encoding
                    teacher_html = res.text

                    # 2. Inhalt konvertieren (Liste von HTML-Strings für Schülerpläne)
                    converted_html_plans = ConvertTeacherToStudent(teacher_html)

                    if not converted_html_plans:
                        logger.warning(
                            f"Konvertierung des Lehrerplans von {client_name} lieferte keine Ergebnisse."
                        )
                        continue

                    # 3. Verarbeite und filtere jeden konvertierten HTML-Plan
                    for html_content in converted_html_plans:
                        plan_dt_obj = self._extract_plan_date(html_content)

                        # Prüfe, ob der Plan frühstens vom übernächsten Werktag ist
                        if plan_dt_obj is None or plan_dt_obj < min_working_day:
                            date_display = (
                                plan_dt_obj.strftime("%d.%m.%Y")
                                if plan_dt_obj
                                else "unbekanntes Datum"
                            )
                            logger.debug(
                                f"Konvertierter Plan ({date_display}) ignoriert, da er vor {min_working_day.strftime('%d.%m.%Y')} liegt."
                            )
                            continue

                        # Der Plan ist gültig und wird verarbeitet
                        converted_counter += 1

                        # Temporäre Titel/Datumsextraktion nur für Zustand/Logs
                        soup = BeautifulSoup(html_content, "html.parser")
                        mon_title_div = soup.find("div", class_="mon_title")

                        # Generiere einen eindeutigen Schlüssel (beinhaltet Client-Name und Datum)
                        date_tag = plan_dt_obj.strftime("%Y%m%d")
                        unique_key = (
                            f"converted_{client_name}_{date_tag}_{converted_counter}"
                        )

                        new_title = (
                            mon_title_div.text.strip()
                            if mon_title_div
                            else f"Konvertierter Plan {converted_counter} ({client_name})"
                        )

                        # 4. Speichern des HTML-Inhalts
                        if self._save_content_by_date(
                            html_content, new_title, unique_key
                        ):
                            new_plan_data = {
                                "detail": unique_key,  # Interner Schlüssel für das Tracking
                                "title": new_title,
                                "date": datetime.now().isoformat(),
                                "original_url": url,
                            }

                            # Zum Zustand hinzufügen. Es ist ein Update, wenn der Key neu ist.
                            current_plans[unique_key] = new_plan_data
                            if unique_key not in last_plans:
                                new_keys.add(unique_key)
                                logger.info(
                                    f"Konvertierungsziel als Neu markiert: {new_title} (Key: {unique_key})"
                                )
                            else:
                                logger.debug(
                                    f"Konvertierter Plan {new_title} existierte bereits im Zustand."
                                )
                        else:
                            logger.error(
                                f"Speichern des konvertierten Plans {new_title} fehlgeschlagen."
                            )

                except Exception as e:
                    logger.error(
                        f"Fehler bei Konvertierung des Lehrerplans {url} für {client_name}: {e}",
                        exc_info=True,
                    )

                # Wenn es ein Lehrerplan war, überspringen wir die Standardverarbeitung (Teil 2).
                continue

            # **********************************************
            # Teil 2: Standard-Pläne (DSB App SuS, etc.)
            # **********************************************

            # Verwende die URL als Schlüssel für Standardpläne
            current_plans[url] = plan_data
            date = plan_data.get("date")  # Zeitstempel aus Metadaten

            last_data = last_plans.get(url)

            is_new = url not in last_plans
            is_updated = last_data and (
                # Prüfen auf Änderung von Titel oder Zeitstempel (date)
                last_data.get("title") != title
                or last_data.get("date") != date
            )

            if is_new or is_updated:
                # Verwende die Wrapper-Methode, die den Inhalt von der URL abruft und speichert
                if self._save_html_from_url(url, title):
                    new_keys.add(url)
                    logger.info(
                        f"Standardplan als Neu/Update markiert: {title} (Client: {client_name})"
                    )
                else:
                    # Wenn das Speichern fehlschlägt, entfernen wir es aus current_plans
                    current_plans.pop(url)

        # Gib alle neuen/aktualisierten Pläne und die Keys zurück.
        return current_plans, new_keys

    def run_cycle(self):
        """Führt den Abrufzyklus für alle konfigurierten DSBClients (Schüler & Lehrer) aus."""

        all_current_plans = {}
        all_new_keys = set()

        # Iteriere über alle konfigurierten Clients
        for client_data in self.clients:
            client_instance = client_data["client"]
            client_name = client_data["name"]

            # Hole den Zustand für diesen Client
            # Da `self.clients` eine Liste von Dictionaries mit einem 'state'-Schlüssel ist,
            # können wir den Zustand direkt verwenden und am Ende des Zyklus aktualisieren.
            last_plans = client_data["state"]

            current_plans, new_keys = self._process_client_cycle(
                client_instance, last_plans, client_name
            )

            # Füge die Ergebnisse zum Gesamtzustand hinzu (für Discord-Benachrichtigung und Git-Commit)
            all_current_plans.update(current_plans)
            all_new_keys.update(new_keys)

            # Aktualisiere den spezifischen Client-Zustand für den nächsten Durchlauf
            # Wichtig: 'state' ist eine Referenz auf self.last_plans_student/teacher
            client_data["state"] = current_plans
            if client_name == "Schüler":
                self.last_plans_student = current_plans
            elif client_name == "Lehrer":
                self.last_plans_teacher = current_plans

            logger.debug(
                f"{client_name}-Zyklus abgeschlossen. Neue/aktualisierte Schlüssel: {len(new_keys)}"
            )

        updated = bool(all_new_keys)

        if updated:
            logger.info(f"Gesamt-Updates gefunden: {list(all_new_keys)}")
            # Sende Discord-Nachricht basierend auf allen neuen/aktualisierten Plänen
            self.discord.send_plan_update(all_current_plans, all_new_keys)
            self.git.push_changes(message="Gesamtplan Update (Standard & Konvertiert)")

        if not updated:
            logger.debug("Keine neuen Gesamt-Updates gefunden.")

    def start(self):
        """Startet den Haupt-Bot-Zyklus."""
        logger.info("Bot gestartet.")
        self.discord.send_warning("🤖 Bot wurde neu gestartet.")

        while True:
            # --- 1. Abrufzyklus (Schüler und Lehrer) ---
            self.run_cycle()

            # --- 2. Warte bis zur nächsten vollen Minute ---
            try:
                time_to_wait = 60 - time.localtime().tm_sec
                time.sleep(time_to_wait)
            except Exception as e:
                err_msg = f"Fehler beim Warten: {e}"
                logger.error(err_msg, exc_info=True)
                self.discord.send_warning(f" [CRASH] {err_msg}")
