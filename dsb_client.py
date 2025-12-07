import requests
import json
import uuid
import base64
import gzip
import datetime as dt
from utils import logger

class DSBClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.data_url = "https://app.dsbcontrol.de/JsonHandler.ashx/GetData"

    def fetch_menu_links(self):
        """
        Ruft die Menüstruktur vom DSB-Server ab, dekodiert sie und extrahiert 
        alle Links zu Vertretungsplänen (.htm/.html), zusammen mit den Metadaten 
        (Datum und Titel) des übergeordneten Plan-Eintrags.

        Gibt eine Liste von Dictionaries zurück: 
        [{'detail': 'https://...', 'date': '...', 'title': '...'}, ...]
        """
        current_time = dt.datetime.now().isoformat()[:-3] + "Z"
        
        params = {
            "UserId": self.username,
            "UserPw": self.password,
            "AppVersion": "2.5.9",
            "Language": "de",
            "OsVersion": "28 8.0",
            "AppId": str(uuid.uuid4()),
            "Device": "SM-G30F",
            "BundleId": "de.heinekingmedia.dsbmobile",
            "Date": current_time,
            "LastUpdate": current_time
        }

        try:
            # --- ANFRAGE VORBEREITEN ---
            params_bytes = json.dumps(params, separators=(',', ':')).encode("UTF-8")
            # Daten komprimieren und Base64-kodieren
            params_compressed = base64.b64encode(gzip.compress(params_bytes)).decode("UTF-8")
            json_req = {"req": {"Data": params_compressed, "DataType": 1}}
            
            # --- POST-ANFRAGE SENDEN ---
            r = requests.post(self.data_url, json=json_req, timeout=15)
            r.raise_for_status()
            
            # --- ANTWORT VERARBEITEN ---

            resp_compressed = json.loads(r.content)["d"]
            # Daten Base64-dekodieren und dekomprimieren
            data = json.loads(gzip.decompress(base64.b64decode(resp_compressed)))
            
            # --- PRÜFUNG DES API-STATUSCODES ---
            if data.get('Resultcode') != 0:
                logger.error(f"DSB API Error (Resultcode {data.get('Resultcode')}): {data.get('ResultStatusInfo')}")
                return []

            # --- ZIELGERICHTETES EXTRAHIEREN DER LINKS MIT METADATEN ---
            links_with_metadata = []
            
            # 1. Das Element mit Title: "Inhalte" finden
            inhalte_item = next(
                (item for item in data.get("ResultMenuItems", []) if item.get("Title") == "Inhalte"),
                None
            )
            
            if not inhalte_item:
                logger.warning("DSB Menu Item 'Inhalte' nicht gefunden.")
                return []
                
            # 2. Das Element mit Title: "Pläne" (Pl\u00e4ne) in den Childs von "Inhalte" finden
            # (Beachten Sie, dass "Pläne" in JSON als "Pl\u00e4ne" kodiert sein kann)
            plaene_item = next(
                (child for child in inhalte_item.get("Childs", []) if child.get("Title") == "Pläne"),
                None
            )
            
            if not plaene_item:
                logger.warning("DSB Child Item 'Pläne' nicht gefunden.")
                return []

            # 3. Die Childs (die einzelnen Plan-Einträge) im Root-Objekt von "Pläne" durchgehen
            root_childs = plaene_item.get("Root", {}).get("Childs", [])
            
            for child in root_childs:
                # Metadaten des Plan-Eintrags (Parent)
                parent_date = child.get("Date")
                parent_title = child.get("Title")
                
                # Der eigentliche Link ist im verschachtelten Child-Element enthalten
                nested_childs = child.get("Childs")

                if isinstance(nested_childs, list) and nested_childs:
                    # Basierend auf den JSON-Beispielen ist der Detail-Link im ersten inneren Child
                    link_object = nested_childs[0]
                    detail_link = link_object.get("Detail")

                    # Filter: Stellt sicher, dass es ein gültiger Vertretungsplan-Link ist
                    is_valid_plan = detail_link and \
                                    (detail_link.endswith(".htm") or detail_link.endswith(".html"))
                    
                    if is_valid_plan:
                         links_with_metadata.append({
                             "detail": detail_link,
                             "date": parent_date,
                             "title": parent_title
                         })

            
            logger.info(f"DSB Links gefunden: {len(links_with_metadata)} gefilterte Vertretungspläne.")
            logger.debug(f"DSB Gefundene Links (mit Metadaten): {links_with_metadata}")
            
            return links_with_metadata

        except Exception as e:
            # Fängt Netzwerkfehler oder Dekomprimierungs-/JSON-Fehler ab
            logger.error(f"DSB Abruf fehlgeschlagen: {e}", exc_info=True)
            return []