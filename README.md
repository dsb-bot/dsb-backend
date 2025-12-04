# DSB Vertretungsplan Bot

Automatischer Vertretungsplan-Bot für **DSB Mobile**, inkl. **Git-Archivierung**, **Discord-Benachrichtigungen** und **Temperaturüberwachung** (für Raspberry Pi).

---

## ✨ Features

* **Automatischer DSB-Abruf** (neue oder geänderte Pläne)
* **Git-Auto-Sync**

  * Klont Repository automatisch beim ersten Start
  * Hält es aktuell (`git pull`)
  * Pusht neue HTML-Pläne automatisch
* **Discord-Benachrichtigungen**

  * Warnungen (Fehler, Temperatur)
  * Meldung neuer Pläne
* **Hardware-Monitoring**

  * Temperaturwarnung (konfigurierbar)
* **Saubere Modulstruktur**

---

## 📦 Installation

### 1. Repository herunterladen

Lege den Bot in ein beliebiges Verzeichnis, z. B.:

```
/home/pi/dsb-bot
```

### 2. Abhängigkeiten installieren

```
pip install -r requirements.txt
```

### 3. `.env` Datei erstellen

**Nicht teilen!** Enthält Passwörter.

```
# --- DSB Zugangsdaten ---
DSB_USER=dein_login
DSB_PASS=dein_passwort

# --- GitHub ---
GIT_USER=DeinGitHubName
GIT_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
GIT_REPO=mein-plan-archiv

# --- Discord Webhooks ---
DISCORD_WEBHOOK_WARN=https://discord.com/api/webhooks/...warn
DISCORD_WEBHOOK_PLANS=https://discord.com/api/webhooks/...plans

# --- Einstellungen ---
TEMP_THRESHOLD=70
```

---

## ▶️ Starten

```
python start_server.py
```

Beim ersten Start passiert automatisch:

* Repository `GIT_REPO` wird **geklont**, falls nicht vorhanden
* ansonsten wird ein **git pull** durchgeführt
* danach startet der Plan-Check-Loop & Temperaturmonitor

---

## 📂 Ordnerstruktur

```
.
├── start_server.py
├── server-build/
│   └── build_bot.py
├── .env
├── requirements.txt
└── dsb-database/       # automatisch erstellt
    └── plans/
        ├── 2023-10-01.html
        └── 2023-10-02.html
```

---

## ❗ Troubleshooting

* **Git Authentication failed**
  → Stelle sicher, dass der Token **repo-Rechte** hat.

* **Temperatur wird nicht angezeigt**
  → funktioniert nur auf Raspberry Pi.

* **Git-Konflikte**
  → Ordner `dsb-database` löschen → Bot neu starten.

---

## ⚖️ Hinweis

Dieses Projekt ist **inoffiziell** und steht in keiner Verbindung zu DSB Mobile / Heinekingmedia.