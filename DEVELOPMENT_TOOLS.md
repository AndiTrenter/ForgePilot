# ForgePilot - Vorinstallierte Development-Tools

**Version:** 2.5.3  
**Zweck:** ForgePilot hat ALLE nötigen Tools für die Preview-Entwicklung bereits vorinstalliert.

---

## 🔧 Vorinstallierte Tools

### Node.js Ecosystem
```bash
Node.js: v20.20.1
npm: v10.8.2
yarn: ✅ installiert
```

### Python Ecosystem
```bash
Python: 3.11.15
pip: ✅ installiert
```

### DevOps & Containers
```bash
Git: ✅
Docker: ✅
docker-compose: ✅
```

### Build Tools
```bash
bash/shell: ✅
make: ✅
curl, wget: ✅
```

---

## 🚀 Was das bedeutet für den Agent

### ❌ FALSCH (Alt):
```
Agent: "Ohne eine funktionierende npm-Umgebung kann ich die 
        React-Bibliotheken nicht installieren. Für eine lokale 
        Ausführung auf deinem System fällt deshalb das manuelle 
        Setup von npm an:
        
        1. **Installiere Node.js**
        2. npm init -y
        3. npm install react react-dom"
        
User: 🤦 "Warum kann ForgePilot das nicht selbst?"
```

### ✅ RICHTIG (Neu v2.5.3):
```
Agent: *erstellt package.json*
Agent: *führt run_command("npm install") aus*
Agent: *startet Preview*
Agent: "✅ Preview läuft! Teste jetzt mit browser_test"

User: 🎉 "Perfekt!"
```

---

## 📝 Workflow für den Agent

### React/Node.js Projekt:
```javascript
1. create_file("package.json", {
     "dependencies": { "react": "^18.0.0" }
   })
2. run_command("npm install")
3. create_file("src/App.js", ...)
4. run_command("npm start")
5. browser_test(...)
```

### Python/Flask Projekt:
```python
1. create_file("requirements.txt", "flask\nrequests")
2. run_command("pip install -r requirements.txt")
3. create_file("app.py", ...)
4. run_command("python app.py &")
5. browser_test(...)
```

### Full-Stack mit Docker:
```yaml
1. setup_docker_service(type="mongodb", name="db")
2. create_file("docker-compose.yml", ...)
3. run_command("docker-compose up -d")
4. create_file(backend & frontend files)
5. run_command("npm install")
6. browser_test(...)
```

---

## 🎯 Agent-Regeln (System Prompt v2.5.3)

### NIEMALS:
- ❌ "Bitte installiere Node.js manuell"
- ❌ "Du brauchst npm auf deinem System"
- ❌ "Ohne Python kann ich nicht..."
- ❌ User bitten irgendwas zu installieren

### IMMER:
- ✅ run_command("npm install") selbst ausführen
- ✅ run_command("pip install ...") selbst ausführen
- ✅ Alle Tools nutzen die ForgePilot hat
- ✅ Selbstständig Dependencies installieren
- ✅ Preview direkt zum Laufen bringen

---

## 🔍 Verfügbare Packages in ForgePilot

### Python (pip):
- FastAPI ✅
- Flask ✅
- Requests ✅
- Motor (MongoDB) ✅
- Pydantic ✅
- ... und alle über pip installierbaren Packages

### Node (npm/yarn):
- React ✅
- Express ✅
- Axios ✅
- ... und alle über npm installierbaren Packages

### Docker Services (setup_docker_service):
- MongoDB ✅
- PostgreSQL ✅
- MySQL ✅
- Redis ✅
- Elasticsearch ✅
- RabbitMQ ✅

---

## 💡 Für den User

**Du musst NICHTS installieren!**

ForgePilot hat:
- ✅ Node.js + npm
- ✅ Python + pip
- ✅ Docker
- ✅ Git
- ✅ Alle gängigen Build-Tools

Der Agent installiert selbst:
- ✅ React, Vue, Angular
- ✅ Express, Flask, FastAPI
- ✅ MongoDB, PostgreSQL
- ✅ Alle Packages die das Projekt braucht

**Du gibst nur die Projektidee** → Agent baut alles selbst!

---

## 🚨 Wichtig

### Unterschied zwischen:

**1. ForgePilot (Development)**
- Hat alle Tools vorinstalliert ✅
- Agent nutzt run_command
- Preview läuft direkt

**2. Finale Deployment (Production)**
- User/Server installiert aus requirements.txt
- package.json / docker-compose.yml
- Das ist normal und korrekt!

**ForgePilot = Self-sufficient Development Environment**  
**Deployed App = Braucht Dependencies vom Manifest**

---

## ✅ Was v2.5.3 changed

**Vorher:**
- Agent sagte "installiere Node.js"
- User musste manuell setup machen
- Preview funktionierte nicht sofort

**Nachher:**
- Agent nutzt vorinstallierte Tools
- run_command für npm/pip install
- Preview funktioniert direkt ✅

---

**Stand:** 31. März 2026  
**Version:** 2.5.3  
**Status:** ✅ PRODUCTION READY
