import time
import os
import sys
import requests
import subprocess
import re
from bs4 import BeautifulSoup
from datetime import datetime
import datetime as dt
import gzip, uuid, base64, json

# --- BENUTZERPARAMETER ---
if len(sys.argv) < 7:
    print("Usage: build_bot.py <user> <password> <git_user> <git_token> <git_repo> <discord_webhook>")
    sys.exit(1)

DSB_USER = sys.argv[1]
DSB_PASS = sys.argv[2]
GIT_USER = sys.argv[3]
GIT_TOKEN = sys.argv[4]
GIT_REPO = sys.argv[5]
DISCORD_WEBHOOK = sys.argv[6]

last_plans = {}

PLANS_DIR = os.path.join(os.path.dirname(__file__), "dsb-database/plans")
os.makedirs(PLANS_DIR, exist_ok=True)

# --------------------------
# --- DSB PLAN FUNKTIONEN ---
# --------------------------

def get_dsb_links(username: str, password: str):
    DATA_URL = "https://app.dsbcontrol.de/JsonHandler.ashx/GetData"
    current_time = dt.datetime.now().isoformat()[:-3] + "Z"

    params = {
        "UserId": username,
        "UserPw": password,
        "AppVersion": "2.5.9",
        "Language": "de",
        "OsVersion": "28 8.0",
        "AppId": str(uuid.uuid4()),
        "Device": "SM-G930F",
        "BundleId": "de.heinekingmedia.dsbmobile",
        "Date": current_time,
        "LastUpdate": current_time
    }

    params_bytestring = json.dumps(params, separators=(',', ':')).encode("UTF-8")
    params_compressed = base64.b64encode(gzip.compress(params_bytestring)).decode("UTF-8")

    json_data = {"req": {"Data": params_compressed, "DataType": 1}}
    r = requests.post(DATA_URL, json=json_data, timeout=15)
    r.raise_for_status()

    data_compressed = json.loads(r.content)["d"]
    data = json.loads(gzip.decompress(base64.b64decode(data_compressed)))

    if data['Resultcode'] != 0:
        raise Exception(data['ResultStatusInfo'])

    links = []
    for page in data["ResultMenuItems"][0]["Childs"]:
        for child in page["Root"]["Childs"]:
            if isinstance(child["Childs"], list):
                for sub_child in child["Childs"]:
                    links.append(sub_child["Detail"])
            else:
                links.append(child["Childs"]["Detail"])

    return [link for link in links if link.endswith(".htm") and "subst" in link]


def make_filename_from_title(title: str) -> str:
    try:
        parts = title.split()
        date_str = parts[0]
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        return f"{date_obj.strftime('%Y-%m-%d')}.html"
    except Exception as e:
        print(f" [ERROR] Konnte Dateinamen aus '{title}' nicht erzeugen: {e}")
        safe_title = re.sub(r'[^0-9A-Za-z]+', "_", title)
        return f"{safe_title}.html"


def save_plan_html(url, title):
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            filename = os.path.join(PLANS_DIR, make_filename_from_title(title))
            with open(filename, "w", encoding="utf-8") as f:
                f.write(res.text)
            print(f" [LOG] Plan gespeichert: {filename}")
        else:
            print(f" [ERROR] Plan konnte nicht geladen werden: {url} ({res.status_code})")
    except Exception as e:
        print(f" [ERROR] Fehler beim Speichern von {url}: {e}")


def get_pi_temp():
    try:
        res = os.popen("vcgencmd measure_temp").readline()
        temp = float(res.replace("temp=", "").replace("'C\n", ""))
        return temp
    except Exception:
        return None


def send_to_discord(plans, new_keys):
    fields = []
    for key, data in plans.items():
        title = f"{data['title']}"
        if key in new_keys:
            title += " 🌟 (neu)"
        fields.append({
            "name": title,
            "value": f"[Vertretungsplan öffnen]({data['url']})",
            "inline": False
        })

    pi_temp = get_pi_temp()
    temp_text = f"Aktuelle Pi-Temperatur: {pi_temp:.1f}°C" if pi_temp else "Temperatur unbekannt"

    data = {
        "username": "DSB-Bot",
        "avatar_url": "https://www.dsbmobile.de/img/logo_dsbmobile.png",
        "embeds": [
            {
                "title": "Aktuelle Vertretungspläne",
                "color": 0x1abc9c,
                "fields": fields,
                "footer": {
                    "text": f"by Jokko | {temp_text}",
                    "icon_url": "https://cdn.discordapp.com/attachments/1414969864790999072/1414993991027658844/Jokko_Profile_Better.png"
                }
            }
        ]
    }
    try:
        response = requests.post(DISCORD_WEBHOOK, json=data)
        if response.status_code == 204:
            print(" [LOG] Webhook erfolgreich gesendet.")
        else:
            print(f" [ERROR] Fehler beim Senden des Webhooks: {response.status_code}, {response.text}")
    except Exception as e:
        print(f" [ERROR] Webhook konnte nicht gesendet werden: {e}")


def fetch_plan_title(url):
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            title_div = soup.find("div", class_="mon_title")
            if title_div:
                return title_div.text.strip()
    except Exception as e:
        print(f" [ERROR] Konnte {url} nicht laden: {e}")
    return "Unbekannt"


# --------------------------
# --- GIT PUSH FUNKTION ---
# --------------------------

def push_to_git(git_user, git_token, git_repo):
    try:
        repo_path = os.path.join(os.path.dirname(__file__), "dsb-database")
        repo_path = os.path.abspath(repo_path)
        os.chdir(repo_path)

        remote_url = f"https://{git_user}:{git_token}@github.com/{git_user}/{git_repo}.git"
        subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Automated update"], check=False)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print(" [LOG] Git Push erfolgreich!")
    except Exception as e:
        print(f" [ERROR] Git Push fehlgeschlagen: {e}")


# --------------------------
# --- HAUPTLOOP ---
# --------------------------

def check_dsbmobile():
    global last_plans
    try:
        found_urls = get_dsb_links(DSB_USER, DSB_PASS)

        if not found_urls:
            print(" [ERROR] Keine passenden Links gefunden.")
            return

        plans = {}
        for u in found_urls:
            title = fetch_plan_title(u)
            plans[title] = {"url": u, "title": title}

        print(f" [LOG] Gefundene Pläne: {list(plans.keys())}")

        new_keys = set(plans.keys()) - set(last_plans.keys())
        updated = False
        for key in plans:
            if key not in last_plans or plans[key]["url"] != last_plans.get(key, {}).get("url"):
                new_keys.add(key)
                updated = True

        if updated:
            send_to_discord(plans, new_keys)
            for key in new_keys:
                save_plan_html(plans[key]["url"], plans[key]["title"])

            push_to_git(GIT_USER, GIT_TOKEN, GIT_REPO)
            last_plans = plans

    except Exception as e:
        print(f" [ERROR] Fehler beim Abrufen: {e}")
        time.sleep(10)


while True:
    check_dsbmobile()
    now = time.localtime()
    sleep_seconds = 60 - now.tm_sec
    time.sleep(sleep_seconds)