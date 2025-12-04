import requests
import json
import uuid
import base64
import gzip
import datetime as dt
from utils import logger # Importiert den konfigurierten Logger

class DSBClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.data_url = "https://app.dsbcontrol.de/JsonHandler.ashx/GetData"

    def fetch_menu_links(self):
        current_time = dt.datetime.now().isoformat()[:-3] + "Z"
        
        params = {
            "UserId": self.username,
            "UserPw": self.password,
            "AppVersion": "2.5.9",
            "Language": "de",
            "OsVersion": "28 8.0",
            "AppId": str(uuid.uuid4()),
            "Device": "SM-G930F",
            "BundleId": "de.heinekingmedia.dsbmobile",
            "Date": current_time,
            "LastUpdate": current_time
        }

        try:
            # --- DEBUGGING: ANFRAGE VORBEREITEN ---
            params_bytes = json.dumps(params, separators=(',', ':')).encode("UTF-8")
            params_compressed = base64.b64encode(gzip.compress(params_bytes)).decode("UTF-8")
            json_req = {"req": {"Data": params_compressed, "DataType": 1}}
            
            # Protokolliert die verschlüsselte Anfrage, die an den Server geht
            logger.debug(f"DSB Request URL: {self.data_url}")
            logger.debug(f"DSB Request Body (encrypted): {json_req}")
            
            # --- POST-ANFRAGE SENDEN ---
            r = requests.post(self.data_url, json=json_req, timeout=15)
            r.raise_for_status()
            
            # --- DEBUGGING: ANTWORT VERARBEITEN ---
            
            # Protokolliert den rohen, verschlüsselten Inhalt
            resp_content = r.content.decode('utf-8')
            logger.debug(f"DSB Response Content (raw JSON): {resp_content}")

            # Dekomprimierung starten
            resp_compressed = json.loads(r.content)["d"]
            data = json.loads(gzip.decompress(base64.b64decode(resp_compressed)))
            
            # Protokolliert die entschlüsselte und dekomprimierte Antwort
            logger.debug(f"DSB Response Content (decrypted JSON): {json.dumps(data, indent=2)}") 
            
            # --- PRÜFUNG DES API-STATUSCODES ---
            if data.get('Resultcode') != 0:
                # Fängt Fehler ab, die von der API selbst (z.B. falsche Login-Daten) gemeldet werden
                logger.error(f"DSB API Error (Resultcode {data.get('Resultcode')}): {data.get('ResultStatusInfo')}")
                return []

            # --- EXTRAHIEREN DER LINKS ---
            links = []
            menu_items = data.get("ResultMenuItems", [{}])[0].get("Childs", [])
            for page in menu_items:
                root_childs = page.get("Root", {}).get("Childs", [])
                for child in root_childs:
                    if isinstance(child.get("Childs"), list):
                        for sub in child["Childs"]:
                            links.append(sub["Detail"])
                    else:
                        details = child.get("Childs", {}).get("Detail")
                        if details: links.append(details)
            
            logger.info(f"DSB Links gefunden: {len(links)} Vertretungspläne.")
            logger.debug(f"DSB Gefundene Links: {links}")
            
            # Filtert nur die HTML-Pläne heraus
            return [l for l in links if l.endswith(".htm") and "subst" in l]

        except Exception as e:
            # Fängt Netzwerkfehler (requests.post) oder Dekomprimierungsfehler ab
            logger.error(f"DSB Abruf fehlgeschlagen: {e}", exc_info=True)
            return []