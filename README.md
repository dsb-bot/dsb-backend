# DSB-Bot Backend

Dieses Repository enthält das Backend-Skript für **DSB-Bot**, das automatisch Vertretungspläne von DSBMobile abruft, speichert, GitHub pusht und Discord benachrichtigt.

---

## Funktionen

- Abrufen aktueller Vertretungspläne.
- Speichern der Pläne in `dsb-database/plans`.
- Automatische Discord Benachrichtigung bei neuen Plänen.
- GitHub Push für automatische Updates.
- Endlosschleife zur kontinuierlichen Überwachung.
- Raspberry Pi Temperatur optional in Discord-Embed.

---

## Installation

1. Repository klonen:
   ```bash
   git clone https://github.com/USERNAME/dsb-bot-backend.git
   cd dsb-bot-backend
````

2. Python 3 und benötigte Pakete installieren:

   ```bash
   pip install requests beautifulsoup4
   ```

3. Pläne-Verzeichnis wird automatisch erstellt:

   ```
   dsb-database/plans
   ```

---

## Verwendung

Starte das Skript mit:

```bash
python build_bot.py <dsb_user> <dsb_pass> <git_user> <git_token> <git_repo> <discord_webhook>
```

**Parameter:**

| Parameter           | Beschreibung                               |
| ------------------- | ------------------------------------------ |
| `<dsb_user>`        | DSBMobile Benutzername                     |
| `<dsb_pass>`        | DSBMobile Passwort                         |
| `<git_user>`        | GitHub Benutzername                        |
| `<git_token>`       | GitHub Personal Access Token               |
| `<git_repo>`        | GitHub Repository Name                     |
| `<discord_webhook>` | Discord Webhook URL für Benachrichtigungen |

**Beispiel:**

```bash
python build_bot.py max.mustermann geheim123 mygithub abcdef123456 my-dsb-database https://discord.com/api/webhooks/xxx/yyy
```

---

## Hinweise

* Python 3 erforderlich.
* Webhook muss gültig sein, sonst werden Discord-Nachrichten nicht gesendet.
* GitHub-Push setzt voraus, dass Repository existiert und Token Push-Berechtigung hat.
* Das Skript läuft kontinuierlich und prüft jede Minute auf neue Pläne.