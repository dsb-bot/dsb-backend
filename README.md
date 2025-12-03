# DSB-Bot Backend

Dieses Repository enthält das Backend-Skript für **DSB-Bot**, das automatisch Vertretungspläne der **Main-Taunus-Schule** von DSBMobile abruft, speichert und über GitHub bereitstellt. Zusätzlich werden neue Pläne über einen **Discord Webhook** benachrichtigt.

---

## Funktionen

* Abrufen aktueller Vertretungspläne von DSBMobile.
* Speichern der Pläne lokal in `dsb-database/plans`.
* Automatische Benachrichtigung über Discord bei neuen oder geänderten Plänen.
* Push der aktualisierten Pläne in ein GitHub-Repository.
* Unterstützung für kontinuierliches Monitoring in einer Endlosschleife.
* Optional: Raspberry Pi Temperatur in Discord-Nachrichten.

---

## Installation

1. Repository klonen:

   ```bash
   git clone https://github.com/USERNAME/dsb-bot-backend.git
   cd dsb-bot-backend
   ```

2. Python 3 und benötigte Pakete installieren:

   ```bash
   pip install requests beautifulsoup4
   ```

3. Verzeichnis für Pläne wird automatisch erstellt:

   ```
   dsb-database/plans
   ```

---

## Verwendung

Starte das Skript mit folgenden Parametern:

```bash
python build_bot.py <dsb_user> <dsb_pass> <git_user> <git_token> <git_repo>
```

**Parameter:**

| Parameter     | Beschreibung                       |
| ------------- | ---------------------------------- |
| `<dsb_user>`  | DSBMobile Benutzername             |
| `<dsb_pass>`  | DSBMobile Passwort                 |
| `<git_user>`  | GitHub Benutzername                |
| `<git_token>` | GitHub Personal Access Token       |
| `<git_repo>`  | GitHub Repository Name (für Pläne) |

**Beispiel:**

```bash
python build_bot.py max.mustermann geheim123 mygithub abcdef123456 my-dsb-database
```

Das Skript läuft in einer Endlosschleife und überprüft **jede Minute**, ob neue Pläne verfügbar sind.

---

## Discord Webhook

* Stelle sicher, dass du die Variable `DISCORD_WEBHOOK` im Skript auf deinen Webhook setzt.
* Neue Pläne werden automatisch als Embed-Nachricht gepostet, inklusive Plan-Link und optionaler Raspberry Pi Temperatur.

---

## Speicherort der Pläne

* Pläne werden als `.html`-Dateien im Verzeichnis `dsb-database/plans` gespeichert.
* Dateinamen entsprechen dem Datum des Plans im Format `YYYY-MM-DD.html`.

---

## Hinweise

* Das Skript ist auf Python 3 ausgelegt.
* Fehlerhafte oder fehlende Pläne werden geloggt, das Skript läuft weiter.
* GitHub-Push setzt voraus, dass das Repository existiert und das Token ausreichende Berechtigungen hat.

---

## Lizenz

Dieses Projekt ist **frei nutzbar**, Attribution an den Autor empfohlen.
