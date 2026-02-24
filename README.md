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

# --- DSB Lehrer Zugangsdaten --- (optional, leerlassen wenn nicht benötigt)
DSB_TEACHER_USER=238701
DSB_TEACHER_PASS=Leitbild

# --- GitHub ---
GIT_USER=DeinGitHubName
GIT_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
GIT_REPO=mein-plan-archiv

# --- Discord Webhooks ---
DISCORD_WEBHOOK_WARN=https://discord.com/api/webhooks/...warn
DISCORD_WEBHOOK_PLANS=https://discord.com/api/webhooks/...plans

# --- Einstellungen ---

# OPTIONAL: ID der Rolle, die bei Warnungen gepingt werden soll (z.B. 123456789012345678)
DISCORD_PING_ROLE_ID=123456789012345678

# Temp-Warnung ab X Grad
TEMP_THRESHOLD=64
```

---

## ▶️ Starten

```
python main.py
```

Beim ersten Start passiert automatisch:

* Repository `GIT_REPO` wird **geklont**, falls nicht vorhanden
* ansonsten wird ein **git pull** durchgeführt
* danach startet der Plan-Check-Loop & Temperaturmonitor

---

## 📂 Ordnerstruktur

```
.
├── .env                  # Deine Konfiguration (NICHT teilen!)
├── main.py               # Start-Skript
├── config.py             # Lädt Einstellungen
├── bot_logic.py          # Hauptablauf
├── dsb_client.py         # Verbindung zu DSB
├── git_manager.py        # Git Clone/Push Logik
├── discord_notifier.py   # Senden von Nachrichten
├── utils.py              # Hilfstools (Temp Check)
├── requirements.txt      # Python Pakete
│
└── dsb-database/         # <--- Dieses Verzeichnis wird automatisch erstellt/geclont!
    ├── .git/             # Git Metadaten
    └── plans/            # Hier landen die HTML-Dateien
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