# DSB Vertretungsplan Bot

Ein automatisierter Bot, der Vertretungspläne von [DSBMobile](https://www.dsbmobile.de) abruft, speichert, auf GitHub pusht und über Discord benachrichtigt. Zusätzlich überwacht er die CPU-Temperatur eines Raspberry Pi und sendet Warnungen bei Überhitzung.

---

## Funktionen

* Automatisches Abrufen der aktuellen Vertretungspläne von DSBMobile
* Speichern der Pläne lokal
* Benachrichtigungen über neue Pläne auf Discord
* Automatischer GitHub-Push der Änderungen
* Überwachung der Raspberry Pi CPU-Temperatur mit Discord-Warnungen

---

## Voraussetzungen

* Python 3.10+
* Bibliotheken: `requests`, `beautifulsoup4`
* Git installiert
* Discord-Webhooks
* GitHub-Repository

---

## Installation

1. Repository klonen:

   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. Abhängigkeiten installieren:

   ```bash
   pip install requests beautifulsoup4
   ```

---

## Konfiguration

Der Bot benötigt folgende Parameter:

| Parameter               | Beschreibung                              |
| ----------------------- | ----------------------------------------- |
| `DSB_USER`              | Benutzername für DSBMobile                |
| `DSB_PASS`              | Passwort für DSBMobile                    |
| `GIT_USER`              | GitHub-Benutzername                       |
| `GIT_TOKEN`             | GitHub-Personal Access Token              |
| `GIT_REPO`              | GitHub-Repository-Name                    |
| `DISCORD_WEBHOOK_WARN`  | Discord-Webhook für Temperaturwarnungen   |
| `DISCORD_WEBHOOK_PLANS` | Discord-Webhook für neue Vertretungspläne |

---

## Starten des Bots

```bash
python start_server.py <DSB_USER> <DSB_PASS> <GIT_USER> <GIT_TOKEN> <GIT_REPO> <DISCORD_WEBHOOK_WARN> <DISCORD_WEBHOOK_PLANS>
```

* Der Bot überwacht die CPU-Temperatur, ruft neue Vertretungspläne ab, speichert sie lokal, sendet Discord-Benachrichtigungen und pusht Änderungen automatisch zu GitHub.
* Neue Pläne werden automatisch erkannt und hervorgehoben.