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
            # --- ANFRAGE VORBEREITEN ---
            params_bytes = json.dumps(params, separators=(',', ':')).encode("UTF-8")
            params_compressed = base64.b64encode(gzip.compress(params_bytes)).decode("UTF-8")
            json_req = {"req": {"Data": params_compressed, "DataType": 1}}
            
            logger.debug(f"DSB Request URL: {self.data_url}")
            logger.debug(f"DSB Request Body (encrypted): {json_req}")
            
            # --- POST-ANFRAGE SENDEN ---
            r = requests.post(self.data_url, json=json_req, timeout=15)
            r.raise_for_status()
            
            # --- ANTWORT VERARBEITEN ---
            resp_content = r.content.decode('utf-8')
            logger.debug(f"DSB Response Content (raw JSON): {resp_content}")

            resp_compressed = json.loads(r.content)["d"]
            data = json.loads(gzip.decompress(base64.b64decode(resp_compressed)))
            
            logger.debug(f"DSB Response Content (decrypted JSON): {json.dumps(data, indent=2)}") 
            
            # --- PRÜFUNG DES API-STATUSCODES ---
            if data.get('Resultcode') != 0:
                logger.error(f"DSB API Error (Resultcode {data.get('Resultcode')}): {data.get('ResultStatusInfo')}")
                return []

            # --- ZIELGERICHTETES EXTRAHIEREN DER LINKS ---
            links = []
            
            # 1. Das Element mit Title: "Inhalte" finden
            inhalte_item = next(
                (item for item in data.get("ResultMenuItems", []) if item.get("Title") == "Inhalte"),
                None
            )
            
            if not inhalte_item:
                logger.warning("DSB Menu Item 'Inhalte' nicht gefunden.")
                return []
                
            # 2. Das Element mit Title: "Pläne" (Pl\u00e4ne) in den Childs von "Inhalte" finden
            plaene_item = next(
                (child for child in inhalte_item.get("Childs", []) if child.get("Title") == "Pläne"),
                None
            )
            
            if not plaene_item:
                logger.warning("DSB Child Item 'Pläne' nicht gefunden.")
                return []

            # 3. Die Childs im Root-Objekt von "Pläne" durchgehen
            root_childs = plaene_item.get("Root", {}).get("Childs", [])
            
            for child in root_childs:
                # Fall 1: Der Link ist direkt in den Child-Elementen verschachtelt (wie in Ihrem ersten Beispiel)
                # D.h., das Child-Element hat eine Liste von 'Childs', die die Detail-Links enthalten.
                if isinstance(child.get("Childs"), list) and child["Childs"]:
                    for sub in child["Childs"]:
                        # Es wird der 'Detail'-Wert des innersten Elements verwendet
                        if sub.get("Detail"):
                            links.append(sub["Detail"])
                
                # Fall 2: Der Link ist direkt im Detail-Feld des Root-Childs enthalten
                # (Auch wenn in Ihren Beispielen nicht der Fall, ist die ursprüngliche Logik hier sicherer,
                # aber die Anforderung war, nur die verschachtelten zu nehmen.
                # Wir halten uns an die Struktur Ihrer Beispieldaten, wo die Links *immer* # im Sub-Child sind, oder an die generische Struktur eines Listeneintrags.)
                
                # Um nur die *Vertretungsplan*-Links zu erwischen, bleiben wir bei der tieferen Schachtelung, 
                # da Ihre Beispiele zeigen, dass der eigentliche Link tief im 'Childs'-Array steckt,
                # obwohl der Originalcode hier etwas generischer war.
                
                # Wir nehmen nur Links, die wir in den inneren Childs finden, da dies in beiden 
                # Beispielen die gewünschten 'subst_001.htm' Links liefert.

            
            # Der ursprüngliche Code enthielt eine zusätzliche Logik, die sich auf den
            # `Root`-Knoten von `ResultMenuItems` bezog, was nicht in Ihren Beispielen ist,
            # aber die Extraktion der Links aus den **inneren Childs** von **"Pläne"** ist nun 
            # durch die oben implementierte, gezieltere Navigation abgedeckt und berücksichtigt 
            # beide Ihrer JSON-Strukturen, da sie beide demselben Pfad folgen:
            # ResultMenuItems[Title="Inhalte"] -> Childs[Title="Pläne"] -> Root -> Childs[] -> Childs[] -> "Detail"
            
            
            logger.info(f"DSB Links gefunden: {len(links)} Vertretungspläne.")
            logger.debug(f"DSB Gefundene Links: {links}")
            
            # Filtert nur die HTML-Pläne heraus (wie im Originalcode)
            return [l for l in links if l.endswith(".htm") or l.endswith(".html")]

        except Exception as e:
            logger.error(f"DSB Abruf fehlgeschlagen: {e}", exc_info=True)
            return []