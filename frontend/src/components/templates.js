// Project Templates for ForgePilot
export const PROJECT_TEMPLATES = {
  react: {
    id: "react",
    name: "React App",
    description: "Moderne React-Anwendung mit Hooks und Components",
    icon: "⚛️",
    color: "from-cyan-500 to-blue-500",
    files: [
      {
        path: "index.html",
        content: `<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>React App</title>
    <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-900 text-white">
    <div id="root"></div>
    <script type="text/babel" src="App.jsx"></script>
</body>
</html>`
      },
      {
        path: "App.jsx",
        content: `const { useState, useEffect } = React;

function App() {
  const [count, setCount] = useState(0);
  
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-6">
        <h1 className="text-4xl font-bold">React App</h1>
        <p className="text-zinc-400">Counter: {count}</p>
        <div className="flex gap-4 justify-center">
          <button 
            onClick={() => setCount(c => c - 1)}
            className="px-4 py-2 bg-zinc-700 rounded hover:bg-zinc-600"
          >
            -
          </button>
          <button 
            onClick={() => setCount(c => c + 1)}
            className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-500"
          >
            +
          </button>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);`
      }
    ],
    prompt: "Erstelle eine React-Anwendung mit"
  },
  
  vue: {
    id: "vue",
    name: "Vue.js App",
    description: "Reaktive Vue.js 3 Anwendung mit Composition API",
    icon: "💚",
    color: "from-emerald-500 to-green-500",
    files: [
      {
        path: "index.html",
        content: `<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vue App</title>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-900 text-white">
    <div id="app"></div>
    <script src="app.js"></script>
</body>
</html>`
      },
      {
        path: "app.js",
        content: `const { createApp, ref } = Vue;

createApp({
  setup() {
    const count = ref(0);
    const increment = () => count.value++;
    const decrement = () => count.value--;
    
    return { count, increment, decrement };
  },
  template: \`
    <div class="min-h-screen flex items-center justify-center">
      <div class="text-center space-y-6">
        <h1 class="text-4xl font-bold">Vue.js App</h1>
        <p class="text-zinc-400">Counter: {{ count }}</p>
        <div class="flex gap-4 justify-center">
          <button @click="decrement" class="px-4 py-2 bg-zinc-700 rounded hover:bg-zinc-600">-</button>
          <button @click="increment" class="px-4 py-2 bg-emerald-600 rounded hover:bg-emerald-500">+</button>
        </div>
      </div>
    </div>
  \`
}).mount('#app');`
      }
    ],
    prompt: "Erstelle eine Vue.js-Anwendung mit"
  },
  
  node: {
    id: "node",
    name: "Node.js API",
    description: "Express.js REST API mit CRUD-Operationen",
    icon: "🟢",
    color: "from-green-500 to-lime-500",
    files: [
      {
        path: "server.js",
        content: `const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// In-memory data store
let items = [
  { id: 1, name: 'Item 1', description: 'Beschreibung 1' },
  { id: 2, name: 'Item 2', description: 'Beschreibung 2' },
];

// GET all items
app.get('/api/items', (req, res) => {
  res.json(items);
});

// GET single item
app.get('/api/items/:id', (req, res) => {
  const item = items.find(i => i.id === parseInt(req.params.id));
  if (!item) return res.status(404).json({ error: 'Item not found' });
  res.json(item);
});

// POST new item
app.post('/api/items', (req, res) => {
  const item = {
    id: items.length + 1,
    name: req.body.name,
    description: req.body.description
  };
  items.push(item);
  res.status(201).json(item);
});

// PUT update item
app.put('/api/items/:id', (req, res) => {
  const item = items.find(i => i.id === parseInt(req.params.id));
  if (!item) return res.status(404).json({ error: 'Item not found' });
  item.name = req.body.name || item.name;
  item.description = req.body.description || item.description;
  res.json(item);
});

// DELETE item
app.delete('/api/items/:id', (req, res) => {
  const index = items.findIndex(i => i.id === parseInt(req.params.id));
  if (index === -1) return res.status(404).json({ error: 'Item not found' });
  items.splice(index, 1);
  res.status(204).send();
});

app.listen(PORT, () => console.log(\`Server running on port \${PORT}\`));`
      },
      {
        path: "package.json",
        content: `{
  "name": "node-api",
  "version": "1.0.0",
  "description": "Express.js REST API",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  },
  "devDependencies": {
    "nodemon": "^3.0.0"
  }
}`
      }
    ],
    prompt: "Erstelle eine Node.js API mit"
  },
  
  python: {
    id: "python",
    name: "Python FastAPI",
    description: "Moderne Python API mit FastAPI und Pydantic",
    icon: "🐍",
    color: "from-yellow-500 to-amber-500",
    files: [
      {
        path: "main.py",
        content: `from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Python API", version="1.0.0")

# Data model
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None

# In-memory store
items_db: List[Item] = [
    Item(id=1, name="Item 1", description="Beschreibung 1"),
    Item(id=2, name="Item 2", description="Beschreibung 2"),
]

@app.get("/")
def root():
    return {"message": "Python FastAPI", "version": "1.0.0"}

@app.get("/api/items", response_model=List[Item])
def get_items():
    return items_db

@app.get("/api/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    item = next((i for i in items_db if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.post("/api/items", response_model=Item)
def create_item(item: Item):
    item.id = len(items_db) + 1
    items_db.append(item)
    return item

@app.put("/api/items/{item_id}", response_model=Item)
def update_item(item_id: int, updated: Item):
    for i, item in enumerate(items_db):
        if item.id == item_id:
            updated.id = item_id
            items_db[i] = updated
            return updated
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/api/items/{item_id}")
def delete_item(item_id: int):
    for i, item in enumerate(items_db):
        if item.id == item_id:
            items_db.pop(i)
            return {"message": "Item deleted"}
    raise HTTPException(status_code=404, detail="Item not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)`
      },
      {
        path: "requirements.txt",
        content: `fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0`
      }
    ],
    prompt: "Erstelle eine Python FastAPI mit"
  },
  
  landing: {
    id: "landing",
    name: "Landing Page",
    description: "Moderne Marketing-Landingpage mit Tailwind CSS",
    icon: "🚀",
    color: "from-purple-500 to-pink-500",
    files: [
      {
        path: "index.html",
        content: `<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Landing Page</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="style.css">
</head>
<body class="bg-zinc-950 text-white">
    <!-- Hero Section -->
    <header class="min-h-screen flex items-center justify-center px-6">
        <div class="text-center max-w-3xl">
            <h1 class="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
                Willkommen
            </h1>
            <p class="text-xl text-zinc-400 mb-8">
                Eine moderne Landing Page mit atemberaubendem Design.
            </p>
            <div class="flex gap-4 justify-center">
                <a href="#features" class="px-6 py-3 bg-purple-600 hover:bg-purple-500 rounded-lg font-medium transition">
                    Mehr erfahren
                </a>
                <a href="#contact" class="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-lg font-medium transition">
                    Kontakt
                </a>
            </div>
        </div>
    </header>
    
    <!-- Features Section -->
    <section id="features" class="py-24 px-6 bg-zinc-900">
        <div class="max-w-5xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-12">Features</h2>
            <div class="grid md:grid-cols-3 gap-8">
                <div class="p-6 bg-zinc-800 rounded-xl">
                    <div class="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center mb-4">⚡</div>
                    <h3 class="text-xl font-semibold mb-2">Schnell</h3>
                    <p class="text-zinc-400">Blitzschnelle Performance für beste User Experience.</p>
                </div>
                <div class="p-6 bg-zinc-800 rounded-xl">
                    <div class="w-12 h-12 bg-pink-500/20 rounded-lg flex items-center justify-center mb-4">🎨</div>
                    <h3 class="text-xl font-semibold mb-2">Modern</h3>
                    <p class="text-zinc-400">Zeitgemäßes Design mit modernen Technologien.</p>
                </div>
                <div class="p-6 bg-zinc-800 rounded-xl">
                    <div class="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center mb-4">📱</div>
                    <h3 class="text-xl font-semibold mb-2">Responsiv</h3>
                    <p class="text-zinc-400">Optimiert für alle Geräte und Bildschirmgrößen.</p>
                </div>
            </div>
        </div>
    </section>
    
    <script src="script.js"></script>
</body>
</html>`
      },
      {
        path: "style.css",
        content: `/* Custom styles */
html {
    scroll-behavior: smooth;
}

body {
    font-family: system-ui, -apple-system, sans-serif;
}`
      },
      {
        path: "script.js",
        content: `// Smooth scroll and animations
document.addEventListener('DOMContentLoaded', () => {
    console.log('Landing Page loaded');
});`
      }
    ],
    prompt: "Erstelle eine Landing Page mit"
  },
  
  dashboard: {
    id: "dashboard",
    name: "Dashboard",
    description: "Admin-Dashboard mit Charts und Statistiken",
    icon: "📊",
    color: "from-blue-500 to-indigo-500",
    files: [
      {
        path: "index.html",
        content: `<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-zinc-950 text-white">
    <div class="flex min-h-screen">
        <!-- Sidebar -->
        <aside class="w-64 bg-zinc-900 border-r border-zinc-800 p-4">
            <h1 class="text-xl font-bold mb-8">Dashboard</h1>
            <nav class="space-y-2">
                <a href="#" class="flex items-center gap-3 px-3 py-2 rounded bg-zinc-800">📊 Übersicht</a>
                <a href="#" class="flex items-center gap-3 px-3 py-2 rounded hover:bg-zinc-800">👥 Benutzer</a>
                <a href="#" class="flex items-center gap-3 px-3 py-2 rounded hover:bg-zinc-800">📦 Produkte</a>
                <a href="#" class="flex items-center gap-3 px-3 py-2 rounded hover:bg-zinc-800">⚙️ Einstellungen</a>
            </nav>
        </aside>
        
        <!-- Main Content -->
        <main class="flex-1 p-8">
            <h2 class="text-2xl font-bold mb-8">Übersicht</h2>
            
            <!-- Stats -->
            <div class="grid grid-cols-4 gap-6 mb-8">
                <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                    <p class="text-zinc-400 text-sm">Benutzer</p>
                    <p class="text-3xl font-bold">1,234</p>
                </div>
                <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                    <p class="text-zinc-400 text-sm">Umsatz</p>
                    <p class="text-3xl font-bold">€12,345</p>
                </div>
                <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                    <p class="text-zinc-400 text-sm">Bestellungen</p>
                    <p class="text-3xl font-bold">567</p>
                </div>
                <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                    <p class="text-zinc-400 text-sm">Konversion</p>
                    <p class="text-3xl font-bold">3.2%</p>
                </div>
            </div>
            
            <!-- Chart -->
            <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                <h3 class="text-lg font-semibold mb-4">Umsatz (letzte 7 Tage)</h3>
                <canvas id="chart" height="100"></canvas>
            </div>
        </main>
    </div>
    <script src="dashboard.js"></script>
</body>
</html>`
      },
      {
        path: "dashboard.js",
        content: `// Dashboard Chart
const ctx = document.getElementById('chart').getContext('2d');
new Chart(ctx, {
    type: 'line',
    data: {
        labels: ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'],
        datasets: [{
            label: 'Umsatz',
            data: [1200, 1900, 1500, 2100, 1800, 2400, 2200],
            borderColor: '#8b5cf6',
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            fill: true,
            tension: 0.4
        }]
    },
    options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
            y: { grid: { color: '#27272a' }, ticks: { color: '#71717a' } },
            x: { grid: { display: false }, ticks: { color: '#71717a' } }
        }
    }
});`
      }
    ],
    prompt: "Erstelle ein Dashboard mit"
  }
};

export const TEMPLATE_LIST = Object.values(PROJECT_TEMPLATES);
