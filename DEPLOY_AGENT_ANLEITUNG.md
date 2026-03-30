# 🚀 ForgePilot Deploy-Agent - Benutzeranleitung

## Was ist der Deploy-Agent?

Der **Deploy-Agent** ist ein KI-gestützter Installations-Assistent, der Sie **Schritt für Schritt** durch den Deployment-Prozess auf Ihrem Unraid-Server begleitet.

### 🎯 Hauptfeatures

1. **Automatische Screen-Beobachtung** (alle 5 Sekunden)
2. **KI-Analyse** Ihrer Screenshots
3. **Konkrete Befehle** mit Kopieren-Button
4. **Live-Chat** für Fragen
5. **Pause/Resume** Funktionalität
6. **Deployment-Protokoll**

---

## 📋 Workflow

### 1. Projekt entwickeln

Entwickeln Sie Ihr Projekt ganz normal in ForgePilot bis es **fertig und getestet** ist.

### 2. Deploy-Button erscheint

Sobald Ihr Projekt fertig ist und "Bereit für Push" angezeigt wird, erscheint neben dem **GitHub-Push-Button** auch ein **Deploy-Button**.

### 3. Deploy starten

Klicken Sie auf den **Deploy-Button** (🚀 Rocket-Icon).

Ein **Deploy-Chat-Fenster** öffnet sich.

### 4. Screen-Sharing aktivieren

Im Deploy-Chat sehen Sie einen Button:

```
📹 Screen-Sharing starten
```

**Klicken Sie darauf.**

Ihr Browser fragt nach Berechtigung:
- ✅ Wählen Sie **Ihr Unraid-Browser-Fenster** ODER
- ✅ Wählen Sie **Ihren ganzen Bildschirm**

### 5. Automatische Beobachtung

Ab jetzt:
- 🎥 Macht ForgePilot **alle 5 Sekunden automatisch einen Screenshot**
- 🤖 Die **KI analysiert**, was auf dem Bildschirm zu sehen ist
- 💬 Der Agent gibt **konkrete Anweisungen und Befehle**

### 6. Befehle ausführen

Wenn der Agent einen Befehl vorschlägt:

```bash
docker ps | grep forgepilot
```

Sehen Sie neben dem Befehl einen **📋 Kopieren-Button**.

1. Klicken Sie auf **Kopieren**
2. Gehen Sie zu Ihrem **Unraid-Terminal**
3. Fügen Sie den Befehl ein (`Strg+V` oder `Cmd+V`)
4. Drücken Sie **Enter**

Der Agent sieht im nächsten Screenshot das Ergebnis und gibt weitere Anweisungen.

### 7. Bei Fragen

Sie können jederzeit im Chat **Fragen stellen**:

```
"Wie finde ich meine Container-ID?"
"Was bedeutet dieser Fehler?"
"Welchen Port soll ich verwenden?"
```

Der Agent antwortet basierend auf dem, was er sieht und Ihrem Deployment-Kontext.

### 8. Deployment abschließen

Wenn alles läuft, klicken Sie auf:

```
✅ Abschließen
```

Das Deployment wird als **erfolgreich** markiert.

---

## ⏸️ Deployment pausieren

Sie können das Deployment jederzeit **pausieren**:

1. Klicken Sie auf **⏸️ Pausieren**
2. Screen-Sharing wird gestoppt
3. Deployment-Status wird gespeichert

**Später fortsetzen:**

1. Öffnen Sie das Projekt erneut
2. Der Deploy-Button zeigt **"⏸️ Pausiert"**
3. Klicken Sie auf **▶️ Fortsetzen**
4. Deployment läuft weiter

---

## 🎥 Was sieht der Agent?

Der Agent analysiert **genau das**, was auf Ihrem Bildschirm zu sehen ist:

### ✅ Erkannt werden:

- **Terminal-Ausgaben** und Befehle
- **Fehlermeldungen** (rot markiert)
- **Docker-Befehle** und Container-Status
- **Unraid-UI** (Docker-Tab, Console, etc.)
- **Logs** und Statusmeldungen
- **Konfigurationsdateien**

### 📊 Was passiert mit den Screenshots?

**Wichtig:**
- Screenshots werden **NICHT auf der Festplatte gespeichert**
- Sie existieren **nur temporär im Speicher**
- Nach der Analyse werden sie **sofort gelöscht**
- **Kein permanentes Speichern**, keine Datenschutz-Sorgen

---

## 💡 Tipps für bestes Ergebnis

### 1. Zeigen Sie dem Agent das richtige Fenster

Stellen Sie sicher, dass Ihr **Unraid-Browser oder Terminal** gut sichtbar ist, wenn Sie Screen-Sharing aktivieren.

### 2. Vollbildmodus verwenden

Für beste Analyse: Unraid im **Vollbild** öffnen.

### 3. Warten nach Befehlen

Nach Ausführung eines Befehls:
- ⏰ Warten Sie **5-10 Sekunden**
- Der Agent macht automatisch einen Screenshot
- Sie erhalten die nächste Anweisung

### 4. Bei langen Prozessen

Wenn ein Befehl lange dauert (z.B. `docker pull`):
- Lassen Sie das Terminal offen
- Der Agent sieht den Fortschritt
- Er meldet sich, wenn fertig

### 5. Fehler zeigen

Wenn etwas schiefgeht:
- ❌ Lassen Sie die Fehlermeldung **sichtbar**
- 🎥 Der Agent sieht sie beim nächsten Screenshot
- 💡 Er analysiert und schlägt Lösungen vor

---

## 🔧 Beispiel-Ablauf: Docker-Container deployen

### Schritt 1: Deploy starten
- Klick auf 🚀 **Deploy**
- Klick auf 📹 **Screen-Sharing starten**
- Unraid-Browser-Tab auswählen

### Schritt 2: Agent analysiert

**Agent sieht:** Unraid-Dashboard  
**Agent sagt:**
```
Ich sehe, du bist auf dem Unraid-Dashboard.
Öffne bitte den Docker-Tab, um den Container zu installieren.
```

### Schritt 3: Docker-Tab öffnen

Sie navigieren zu **Docker** in Unraid.

**Agent sieht:** Docker-Übersicht  
**Agent sagt:**
```
Gut! Ich sehe die Docker-Übersicht.
Klicke auf "Add Container" am unteren Rand.
```

### Schritt 4: Container-Config

Sie klicken auf "Add Container".

**Agent sieht:** Container-Formular  
**Agent gibt:**
```bash
Name: my-app
Repository: ghcr.io/username/my-app:latest
Port: 3000 → 3000
```

**Mit Kopieren-Buttons** für jeden Wert.

### Schritt 5: Weitere Konfiguration

**Agent fragt:**
```
Wo möchtest du die Daten speichern?
Empfohlen: /mnt/user/appdata/my-app
```

**Gibt Befehl:**
```bash
mkdir -p /mnt/user/appdata/my-app
```

### Schritt 6: Container starten

**Agent sagt:**
```
Klicke auf "Apply" um den Container zu starten.
```

Sie klicken auf Apply.

**Agent sieht:** Container startet  
**Agent sagt:**
```
Container wird gestartet... Warte auf Status.
```

### Schritt 7: Überprüfung

**Agent gibt:**
```bash
docker logs my-app
```

Sie führen aus.

**Agent sieht:** Logs ohne Fehler  
**Agent sagt:**
```
✅ Container läuft erfolgreich!
Öffne http://your-unraid-ip:3000 um die App zu testen.
```

### Schritt 8: Abschluss

Sie testen die App → funktioniert!

Klick auf **✅ Abschließen** im Deploy-Chat.

**Fertig!** 🎉

---

## ❓ Häufige Fragen

### Kann ich mehrere Projekte gleichzeitig deployen?

Ja! Jedes Projekt hat sein eigenes Deployment.

### Was passiert wenn ich Screen-Sharing stoppe?

Das Deployment pausiert automatisch. Sie können es später fortsetzen.

### Funktioniert es mit SSH-Terminal?

Ja! Zeigen Sie einfach Ihr SSH-Terminal-Fenster beim Screen-Sharing.

### Kann der Agent Befehle automatisch ausführen?

Nein, aus Sicherheitsgründen **nicht**. Sie müssen jeden Befehl **manuell** ausführen (Kopieren & Einfügen). So behalten Sie die **volle Kontrolle**.

### Wie oft wird ein Screenshot gemacht?

Alle **5 Sekunden** automatisch, solange Screen-Sharing aktiv ist.

### Was wenn der Agent etwas falsch erkennt?

Korrigieren Sie ihn einfach im Chat:
```
"Das ist nicht Docker, das ist die Console."
"Der Fehler ist woanders, schau hier..."
```

Der Agent passt sich an.

---

## 🚨 Troubleshooting

### Screen-Sharing startet nicht

**Problem:** Browser verweigert Screen-Sharing  
**Lösung:**
1. Prüfen Sie Browser-Berechtigungen
2. Verwenden Sie Chrome, Edge oder Firefox (empfohlen)
3. Safari auf macOS funktioniert auch

### Agent antwortet nicht

**Problem:** Keine Antwort nach Screenshot  
**Lösung:**
1. Warten Sie 10-15 Sekunden
2. Prüfen Sie Netzwerkverbindung
3. Schauen Sie in die Browser-Konsole (F12)

### "Analysiere..." bleibt hängen

**Problem:** Screenshot-Analyse hängt  
**Lösung:**
1. Stoppen Sie Screen-Sharing
2. Starten Sie Screen-Sharing neu
3. Falls wiederholt: Backend-Logs prüfen

### Befehle funktionieren nicht

**Problem:** Befehl gibt Fehler  
**Lösung:**
1. Zeigen Sie die Fehlermeldung dem Agent
2. Er sieht sie beim nächsten Screenshot
3. Er schlägt Alternativen vor

---

## 🎓 Best Practices

### ✅ DO

- Screen-Sharing mit Unraid-Browser starten
- Fehler sichtbar lassen
- Auf Agent-Antworten warten
- Bei Unklarheiten nachfragen
- Terminal-Ausgaben vollständig zeigen

### ❌ DON'T

- Nicht zu schnell zwischen Fenstern wechseln
- Nicht während Analyse andere Tabs öffnen
- Nicht ungefragt von Befehlen abweichen
- Nicht Screen-Sharing abbrechen ohne Pause

---

## 📝 Zusammenfassung

Der **Deploy-Agent** macht Deployment **einfach**:

1. 🚀 **Deploy-Button** klicken
2. 📹 **Screen-Sharing** starten
3. 🤖 Agent **beobachtet** automatisch
4. 💬 Agent gibt **Befehle**
5. 📋 **Kopieren** & ausführen
6. ✅ **Fertig!**

**Keine Screenshots mehr manuell hochladen.**  
**Keine externen KI-Tools mehr.**  
**Alles in ForgePilot. Live. Einfach.**

---

**Version:** 1.2.0+  
**Feature:** Deploy-Agent mit automatischer Screen-Observation  
**Status:** Production-ready
