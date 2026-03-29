# 🎮 ForgePilot Preview-System Anleitung

## Problem: "Weißes Fenster" in der Preview

Wenn die Preview nur ein weißes Fenster zeigt, gibt es mehrere mögliche Ursachen:

### Häufigste Ursachen

#### 1. ❌ **Fehlerhafter generierter Code**
Der Master Agent hat Code mit Fehlern generiert:
- Syntax-Fehler im JavaScript
- Fehlende CSS (keine sichtbaren Elemente)
- Falsche Pfade zu Dateien
- Code wird nicht ausgeführt

#### 2. ❌ **Absolute Pfade statt relative**
```html
<!-- FALSCH ❌ -->
<link rel="stylesheet" href="/css/style.css">
<script src="/assets/script.js"></script>

<!-- RICHTIG ✅ -->
<link rel="stylesheet" href="style.css">
<script src="script.js"></script>
```

#### 3. ❌ **Code ohne visuelle Elemente beim Laden**
```javascript
// FALSCH ❌ - Nichts wird gezeichnet beim Laden
function draw() {
    // ... zeichnet etwas
}
// Aber draw() wird nie aufgerufen!

// RICHTIG ✅ - Initial rendering
function draw() {
    // ... zeichnet etwas
}
draw(); // Sofort beim Laden aufrufen!
// ODER:
window.onload = () => draw();
```

---

## ✅ Was wir verbessert haben

### 1. Master Agent System Prompt erweitert

Der Master Agent hat jetzt **explizite Anweisungen** für sichtbare Previews:

```
KRITISCH FÜR PREVIEW:
□ CSS kann inline im <style> Tag sein ODER als separate style.css
□ JavaScript kann inline im <script> Tag sein ODER als separate script.js
□ KEINE relativen Pfade wie "../css/style.css"
□ Alle Ressourcen im WURZEL-Verzeichnis des Projekts
□ Teste im Browser: Sieht man SOFORT etwas?

FÜR SPIELE zusätzlich:
□ Spielfeld ist SOFORT sichtbar (nicht erst nach Tastendruck!)
```

### 2. verify_game Tool verbessert

Neue Checks im `verify_game` Tool:

- ✅ Prüft ob CSS/Styling vorhanden ist
- ✅ Warnt vor absoluten Pfaden (`src="/..."`)
- ✅ Prüft ob `draw()`/`render()` Funktionen initial aufgerufen werden
- ✅ Validiert Background-Styling

### 3. Strengere Qualitätsstandards

Der Master Agent muss jetzt sicherstellen:
- Preview ist **sofort sichtbar** beim Öffnen
- Keine weißen/leeren Seiten mehr
- Alle visuellen Elemente werden initial gerendert

---

## 🔧 So funktioniert die Preview

### Frontend-Seite (Ihr Browser auf Unraid)

```javascript
// App.js verwendet relative URLs in Production
const PREVIEW_BASE = ''; // Leer in Production
const preview_url = '/api/projects/{id}/preview/index.html';

// Iframe src wird zu:
src="/api/projects/{id}/preview/index.html"
```

### Backend-Seite (FastAPI)

```python
@api_router.get("/projects/{project_id}/preview/{file_path:path}")
async def serve_preview(project_id: str, file_path: str):
    # Serviert Dateien aus dem Workspace
    workspace = Path(project.workspace_path)
    target_path = workspace / file_path
    return FileResponse(target_path)
```

### Nginx Routing

```
/api/projects/*/preview/* → Backend (Port 8001)
```

---

## 🎯 "Open Preview" Button

Der Button oben rechts im Preview-Fenster öffnet die Preview in einem neuen Browser-Tab:

```javascript
onClick={() => window.open(previewInfo.preview_url, '_blank')}
```

In Unraid wird dies zu:
```
http://your-unraid-ip:3000/api/projects/{id}/preview/index.html
```

---

## 🧪 So testen Sie ob die Preview funktioniert

### Test 1: Einfaches HTML (manuelle Datei)

1. Gehen Sie zu einem Projekt
2. Klicken Sie auf "Editor"
3. Erstellen Sie eine `index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
    <style>
        body {
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: Arial;
        }
        h1 { color: white; font-size: 48px; }
    </style>
</head>
<body>
    <h1>✅ Preview funktioniert!</h1>
</body>
</html>
```

4. Speichern Sie die Datei
5. Klicken Sie auf "Preview"
6. Sie sollten **sofort** den farbigen Hintergrund und Text sehen

**Wenn Sie ein weißes Fenster sehen:**
- Öffnen Sie Browser-Konsole (F12)
- Prüfen Sie auf JavaScript-Fehler
- Prüfen Sie die Netzwerk-Tab ob `index.html` geladen wird

### Test 2: Agent generiertes Spiel

1. Erstellen Sie ein neues Projekt
2. Fragen Sie: "Erstelle ein einfaches Tetris-Spiel"
3. Warten Sie bis der Master Agent fertig ist
4. Klicken Sie auf "Preview"
5. Das Spielfeld sollte **sofort sichtbar** sein

**Wenn Sie ein weißes Fenster sehen:**
- Klicken Sie auf "Editor"
- Öffnen Sie `index.html`
- Prüfen Sie ob `<style>` oder `<link href="style.css">` vorhanden ist
- Öffnen Sie `script.js`
- Prüfen Sie ob am Ende `draw()` oder `init()` aufgerufen wird

---

## 🐛 Debugging-Schritte

### Schritt 1: Prüfen Sie die Browser-Konsole

1. Öffnen Sie die Preview
2. Drücken Sie `F12` (Developer Tools)
3. Gehen Sie zum "Console" Tab
4. Suchen Sie nach roten Fehlermeldungen:

```
Uncaught ReferenceError: draw is not defined
→ Problem: Funktion existiert nicht

Failed to load resource: 404 (Not Found) - style.css
→ Problem: CSS-Datei fehlt oder falscher Pfad

Uncaught SyntaxError: Unexpected token
→ Problem: JavaScript-Syntax-Fehler
```

### Schritt 2: Prüfen Sie die Dateistruktur

```
/app/workspaces/{project-id}/
├── index.html     ✅ MUSS vorhanden sein
├── script.js      ✅ Empfohlen (oder inline <script>)
└── style.css      ✅ Empfohlen (oder inline <style>)
```

### Schritt 3: Prüfen Sie HTML-Pfade

Öffnen Sie `index.html` und suchen Sie nach:

```html
<!-- FALSCH ❌ -->
<link rel="stylesheet" href="/css/style.css">
<link rel="stylesheet" href="../assets/style.css">

<!-- RICHTIG ✅ -->
<link rel="stylesheet" href="style.css">
```

### Schritt 4: Prüfen Sie initiales Rendering

Öffnen Sie `script.js` und prüfen Sie das Ende der Datei:

```javascript
// FALSCH ❌ - Nichts passiert beim Laden
function gameLoop() {
    // ...
}

// RICHTIG ✅ - Spiel startet sofort
function gameLoop() {
    // ...
}

// Initial render
init();
gameLoop();
```

---

## 💡 Best Practices für Agent-generierten Code

### Für Sie als Benutzer:

Wenn Sie ein Spiel/App erstellen lassen:

**✅ Gute Anfrage:**
```
Erstelle ein Tetris-Spiel mit:
- Sofort sichtbarem Spielfeld beim Laden
- Farbigem Hintergrund
- Anzeige des aktuellen Scores
- Start-Button um das Spiel zu beginnen
```

**❌ Schlechte Anfrage:**
```
Tetris
```

### Was der Master Agent jetzt tut:

1. **PLANNER**: Recherchiert Best Practices
2. **CODER**: Schreibt vollständigen Code
3. **Nach jeder Datei**: Liest die Datei und prüft Vollständigkeit
4. **TESTER**: Führt `test_code` und `verify_game` aus
5. **REVIEWER**: Liest **alle** Dateien und prüft sie nochmals
6. **NUR wenn alles grün**: Markiert als fertig

---

## 🚀 "Open Preview" in neuem Tab

Der Button oben rechts (Symbol: ↗) öffnet die Preview in einem neuen Browser-Tab.

**Warum?**
- Größere Ansicht zum Testen
- Unabhängig vom ForgePilot-UI
- Echtes Browser-Verhalten

**URL-Format:**
```
http://your-unraid:3000/api/projects/{id}/preview/index.html
```

Sie können diese URL auch:
- Bookmarken
- In einem anderen Browser öffnen
- Auf einem anderen Gerät öffnen (solange es Zugriff auf Ihr Unraid hat)

---

## ⚙️ Technische Details

### CSP (Content Security Policy)

ForgePilot setzt **keine** restriktiven CSP-Header für Preview-Dateien.
Das bedeutet:
- ✅ Inline `<script>` und `<style>` funktionieren
- ✅ Externe CDN-Links funktionieren (z.B. Bootstrap, jQuery)
- ✅ Canvas und WebGL funktionieren

### CORS (Cross-Origin Resource Sharing)

Das Backend hat CORS vollständig aktiviert:
```python
app.add_middleware(CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### File-Serving

Der Backend-Endpoint serviert Dateien mit korrekten Content-Types:
```python
content_types = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml"
}
```

---

## 🎓 Zusammenfassung

**Problem:** Preview zeigt weißes Fenster  
**Ursache:** Meistens fehlerhafter generierter Code  
**Lösung:** Master Agent mit strengeren Qualitätsstandards  

**Verbessert:**
- ✅ Explizite Anweisungen für sichtbare Preview
- ✅ Checks für CSS/Styling
- ✅ Warnung vor absoluten Pfaden
- ✅ Prüfung ob initial rendering stattfindet

**Nächste Schritte für Sie:**
1. Updaten Sie ForgePilot auf Unraid (neuer Code)
2. Erstellen Sie ein Test-Projekt
3. Falls immer noch weiß: Browser-Konsole prüfen (F12)
4. Falls nötig: Hier im Chat melden mit Fehlerdetails

---

**Stand:** Version 1.1.7+  
**Getestet:** ✅ Preview funktioniert in Emergent-Umgebung  
**Unraid:** ⏳ Bereit zum Testen nach Update
