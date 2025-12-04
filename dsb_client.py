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
            params_bytes = json.dumps(params, separators=(',', ':')).encode("UTF-8")
            params_compressed = base64.b64encode(gzip.compress(params_bytes)).decode("UTF-8")
            json_req = {"req": {"Data": params_compressed, "DataType": 1}}
            
            r = requests.post(self.data_url, json=json_req, timeout=15)
            r.raise_for_status()
            
            resp_compressed = json.loads(r.content)["d"]
            data = json.loads(gzip.decompress(base64.b64decode(resp_compressed)))
            
            if data.get('Resultcode') != 0:
                logger.error(f"DSB API Error: {data.get('ResultStatusInfo')}")
                return []

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
            
            return [l for l in links if l.endswith(".htm") and "subst" in l]

        except Exception as e:
            logger.error(f"DSB Abruf fehlgeschlagen: {e}", exc_info=True)
            return []