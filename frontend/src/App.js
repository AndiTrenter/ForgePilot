import { useState, useEffect, useRef, useCallback } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { 
  Send, Loader2, GitBranch, FolderGit2, Play, RefreshCw, 
  Home, Settings, ChevronRight, FileCode, Terminal, 
  CheckCircle2, AlertCircle, Clock, Zap, Bug, Eye,
  Plus, Trash2, ExternalLink, X, MessageSquare
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// ============== API Functions ==============
const api = {
  // Projects
  getProjects: () => axios.get(`${API}/projects`),
  createProject: (data) => axios.post(`${API}/projects`, data),
  getProject: (id) => axios.get(`${API}/projects/${id}`),
  deleteProject: (id) => axios.delete(`${API}/projects/${id}`),
  
  // Messages
  getMessages: (projectId) => axios.get(`${API}/projects/${projectId}/messages`),
  
  // Agents
  getAgents: (projectId) => axios.get(`${API}/projects/${projectId}/agents`),
  
  // Logs
  getLogs: (projectId) => axios.get(`${API}/projects/${projectId}/logs`),
  
  // Roadmap
  getRoadmap: (projectId) => axios.get(`${API}/projects/${projectId}/roadmap`),
  
  // GitHub
  importGitHub: (data) => axios.post(`${API}/github/import`, data),
};

// ============== Components ==============

const Logo = () => (
  <div className="font-['JetBrains_Mono'] font-bold text-lg tracking-tight flex items-center gap-2">
    <div className="w-6 h-6 bg-white rounded-sm flex items-center justify-center">
      <span className="text-black text-sm font-bold">F</span>
    </div>
    <span>ForgePilot</span>
  </div>
);

const AgentIcon = ({ type, size = 16 }) => {
  const icons = {
    orchestrator: Zap,
    planner: FileCode,
    coder: Terminal,
    reviewer: Eye,
    tester: CheckCircle2,
    debugger: Bug,
    git: GitBranch,
  };
  const Icon = icons[type] || Zap;
  return <Icon size={size} />;
};

const AgentStatusPill = ({ agent, isActive }) => {
  const statusColors = {
    idle: "bg-zinc-700",
    running: "bg-blue-500 animate-pulse",
    completed: "bg-emerald-500",
    error: "bg-rose-500",
  };

  return (
    <div 
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900 border transition-all duration-300 ${
        isActive ? "border-blue-500/50 shadow-lg shadow-blue-500/10" : "border-zinc-800"
      }`}
      data-testid={`agent-status-${agent.agent_type}`}
    >
      <div className={`w-2 h-2 rounded-full ${statusColors[agent.status]}`} />
      <AgentIcon type={agent.agent_type} size={14} />
      <span className="text-sm capitalize text-zinc-300">{agent.agent_type}</span>
    </div>
  );
};

const ChatMessage = ({ message, isLast }) => {
  const isUser = message.role === "user";
  
  return (
    <div 
      className={`chat-message animate-fade-in flex ${isUser ? "justify-end" : "justify-start"}`}
      data-testid={`chat-message-${message.id}`}
    >
      <div 
        className={`max-w-[85%] ${
          isUser 
            ? "bg-zinc-800 border border-zinc-700 text-zinc-100 p-4 rounded-xl rounded-tr-sm" 
            : "text-zinc-300 p-0"
        }`}
      >
        {!isUser && (
          <div className="flex items-center gap-2 mb-2 text-xs text-zinc-500">
            <AgentIcon type={message.agent_type || "orchestrator"} size={12} />
            <span className="capitalize">{message.agent_type || "Orchestrator"}</span>
          </div>
        )}
        <div className="markdown-content whitespace-pre-wrap">{message.content}</div>
      </div>
    </div>
  );
};

const LogEntry = ({ log }) => {
  const levelColors = {
    info: "log-info",
    success: "log-success",
    warning: "log-warning",
    error: "log-error",
  };

  const levelIcons = {
    info: "○",
    success: "✓",
    warning: "⚠",
    error: "✕",
  };

  return (
    <div className={`terminal-line flex gap-2 ${levelColors[log.level]}`}>
      <span className="text-zinc-600">{new Date(log.timestamp).toLocaleTimeString()}</span>
      <span>{levelIcons[log.level]}</span>
      <span className="text-zinc-500">[{log.source}]</span>
      <span>{log.message}</span>
    </div>
  );
};

// ============== Start Screen ==============

const StartScreen = () => {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState("");
  const [projectType, setProjectType] = useState("fullstack");
  const [isLoading, setIsLoading] = useState(false);
  const [recentProjects, setRecentProjects] = useState([]);
  const [showGitHubModal, setShowGitHubModal] = useState(false);
  const textareaRef = useRef(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const res = await api.getProjects();
      setRecentProjects(res.data.slice(0, 5));
    } catch (e) {
      console.error("Failed to load projects", e);
    }
  };

  const handleSubmit = async () => {
    if (!prompt.trim()) return;
    
    setIsLoading(true);
    try {
      const res = await api.createProject({
        name: prompt.split('\n')[0].substring(0, 50) || "Neues Projekt",
        description: prompt,
        project_type: projectType,
      });
      navigate(`/workspace/${res.data.id}`);
    } catch (e) {
      console.error("Failed to create project", e);
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      handleSubmit();
    }
  };

  const projectTypes = [
    { id: "fullstack", label: "Full Stack App", icon: Terminal },
    { id: "mobile", label: "Mobile App", icon: FileCode },
    { id: "landing", label: "Landing Page", icon: Eye },
  ];

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      {/* Navigation */}
      <nav className="h-14 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-xl flex items-center justify-between px-6 sticky top-0 z-50">
        <Logo />
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setShowGitHubModal(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md transition-colors"
            data-testid="github-import-btn"
          >
            <FolderGit2 size={16} />
            <span>GitHub Import</span>
          </button>
          <button className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md transition-colors">
            <Settings size={18} />
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center p-6 sm:p-12 md:p-24">
        <div className="max-w-3xl w-full flex flex-col items-center space-y-12">
          {/* Hero Text */}
          <div className="text-center space-y-4">
            <h1 className="text-4xl sm:text-5xl font-medium tracking-tighter text-zinc-50">
              Was möchtest du bauen?
            </h1>
            <p className="text-lg text-zinc-500">
              Beschreibe dein Projekt. ForgePilot plant, entwickelt und testet es für dich.
            </p>
          </div>

          {/* Project Type Selector */}
          <div className="flex items-center gap-2 p-1 bg-zinc-900 rounded-lg border border-zinc-800">
            {projectTypes.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setProjectType(id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  projectType === id
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
                data-testid={`project-type-${id}`}
              >
                <Icon size={16} />
                {label}
              </button>
            ))}
          </div>

          {/* Prompt Box */}
          <div 
            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl overflow-hidden focus-within:border-zinc-600 transition-colors duration-300"
            data-testid="prompt-container"
          >
            <textarea
              ref={textareaRef}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Beschreibe dein Projekt in natürlicher Sprache...

Beispiel: Baue mir eine Todo-App mit React und Node.js. Die App soll Benutzer-Authentifizierung haben und die Todos in MongoDB speichern."
              className="w-full min-h-[200px] bg-transparent p-6 text-lg placeholder:text-zinc-600 focus:outline-none"
              data-testid="main-prompt-input"
            />
            <div className="flex items-center justify-between p-4 border-t border-zinc-800 bg-zinc-900/50">
              <div className="flex items-center gap-4 text-xs text-zinc-500">
                <span>⌘ + Enter zum Starten</span>
              </div>
              <button
                onClick={handleSubmit}
                disabled={!prompt.trim() || isLoading}
                className="flex items-center gap-2 bg-white text-black hover:bg-zinc-200 font-medium px-5 py-2.5 rounded-md transition-all disabled:opacity-50 disabled:cursor-not-allowed btn-primary"
                data-testid="submit-prompt-btn"
              >
                {isLoading ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Send size={18} />
                )}
                <span>Projekt starten</span>
              </button>
            </div>
          </div>

          {/* Recent Projects */}
          {recentProjects.length > 0 && (
            <div className="w-full space-y-4">
              <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-zinc-500">
                Aktuelle Projekte
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {recentProjects.map((project) => (
                  <button
                    key={project.id}
                    onClick={() => navigate(`/workspace/${project.id}`)}
                    className="flex items-center gap-3 p-4 bg-zinc-900 border border-zinc-800 rounded-lg text-left hover:border-zinc-700 hover:bg-zinc-800/50 transition-all group"
                    data-testid={`recent-project-${project.id}`}
                  >
                    <div className="w-10 h-10 bg-zinc-800 rounded-md flex items-center justify-center text-zinc-400 group-hover:text-white transition-colors">
                      <FileCode size={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-zinc-200 truncate">{project.name}</p>
                      <p className="text-xs text-zinc-500 truncate">{project.project_type}</p>
                    </div>
                    <ChevronRight size={16} className="text-zinc-600 group-hover:text-zinc-400 transition-colors" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* GitHub Import Modal */}
      {showGitHubModal && (
        <GitHubImportModal onClose={() => setShowGitHubModal(false)} onImport={(project) => {
          setShowGitHubModal(false);
          navigate(`/workspace/${project.id}`);
        }} />
      )}
    </div>
  );
};

// ============== GitHub Import Modal ==============

const GitHubImportModal = ({ onClose, onImport }) => {
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleImport = async () => {
    if (!repoUrl.trim()) return;
    
    setIsLoading(true);
    setError("");
    
    try {
      const res = await api.importGitHub({ repo_url: repoUrl, branch });
      onImport(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Import fehlgeschlagen");
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4" data-testid="github-import-modal">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <FolderGit2 size={20} />
            <h2 className="text-lg font-medium">Von GitHub importieren</h2>
          </div>
          <button onClick={onClose} className="p-1 text-zinc-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>
        
        <div className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-2">Repository URL</label>
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/user/repo"
              className="w-full bg-zinc-800 border border-zinc-700 text-white px-3 py-2.5 rounded-md focus:outline-none focus:border-zinc-500 placeholder:text-zinc-600"
              data-testid="github-repo-url-input"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-2">Branch</label>
            <input
              type="text"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="main"
              className="w-full bg-zinc-800 border border-zinc-700 text-white px-3 py-2.5 rounded-md focus:outline-none focus:border-zinc-500 placeholder:text-zinc-600"
              data-testid="github-branch-input"
            />
          </div>
          
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-md text-rose-400 text-sm">
              {error}
            </div>
          )}
        </div>
        
        <div className="flex items-center justify-end gap-3 p-4 border-t border-zinc-800">
          <button
            onClick={onClose}
            className="px-4 py-2 text-zinc-400 hover:text-white transition-colors"
          >
            Abbrechen
          </button>
          <button
            onClick={handleImport}
            disabled={!repoUrl.trim() || isLoading}
            className="flex items-center gap-2 bg-white text-black hover:bg-zinc-200 font-medium px-4 py-2 rounded-md transition-all disabled:opacity-50"
            data-testid="github-import-confirm-btn"
          >
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : <GitBranch size={16} />}
            Importieren
          </button>
        </div>
      </div>
    </div>
  );
};

// ============== Workspace ==============

const Workspace = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [messages, setMessages] = useState([]);
  const [agents, setAgents] = useState([]);
  const [logs, setLogs] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("preview");
  const chatEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    loadProjectData();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [projectId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadProjectData = async () => {
    try {
      const [projectRes, messagesRes, agentsRes, logsRes] = await Promise.all([
        api.getProject(projectId),
        api.getMessages(projectId),
        api.getAgents(projectId),
        api.getLogs(projectId),
      ]);
      
      setProject(projectRes.data);
      setMessages(messagesRes.data);
      setAgents(agentsRes.data);
      setLogs(logsRes.data);
      
      // If new project with description, start initial chat
      if (messagesRes.data.length === 0 && projectRes.data.description) {
        sendMessage(projectRes.data.description);
      }
    } catch (e) {
      console.error("Failed to load project", e);
      navigate("/");
    }
  };

  const sendMessage = async (content) => {
    if (!content?.trim()) return;
    
    const userMessage = {
      id: Date.now().toString(),
      role: "user",
      content: content.trim(),
      created_at: new Date().toISOString(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API}/projects/${projectId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, content: content.trim() }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiContent = "";
      let aiMessageId = Date.now().toString() + "_ai";
      
      // Add empty AI message
      setMessages(prev => [...prev, {
        id: aiMessageId,
        role: "assistant",
        content: "",
        created_at: new Date().toISOString(),
        agent_type: "orchestrator",
      }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const text = decoder.decode(value);
        const lines = text.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.content) {
                aiContent += data.content;
                setMessages(prev => prev.map(msg => 
                  msg.id === aiMessageId ? { ...msg, content: aiContent } : msg
                ));
              }
              if (data.done) {
                // Refresh logs
                const logsRes = await api.getLogs(projectId);
                setLogs(logsRes.data);
              }
            } catch (e) {
              // Skip invalid JSON
            }
          }
        }
      }
    } catch (e) {
      console.error("Chat error:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };

  const activeAgent = agents.find(a => a.status === "running");

  if (!project) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-zinc-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      {/* Navigation */}
      <nav className="h-14 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-xl flex items-center justify-between px-4 sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate("/")} className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md transition-colors">
            <Home size={18} />
          </button>
          <div className="h-6 w-px bg-zinc-800" />
          <Logo />
          <div className="h-6 w-px bg-zinc-800" />
          <span className="text-sm text-zinc-400 max-w-[200px] truncate">{project.name}</span>
        </div>
        
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-md transition-colors" data-testid="deploy-btn">
            <Play size={14} />
            Deploy
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-white text-sm rounded-md transition-colors" data-testid="preview-btn">
            <ExternalLink size={14} />
            Preview öffnen
          </button>
        </div>
      </nav>

      {/* Workspace Layout */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-12 h-[calc(100vh-3.5rem)] overflow-hidden">
        {/* Left Panel - Chat */}
        <div className="col-span-1 md:col-span-4 lg:col-span-4 border-r border-zinc-800 bg-zinc-950 flex flex-col h-full">
          {/* Agent Timeline */}
          <div className="p-4 border-b border-zinc-800 bg-zinc-900/30" data-testid="agent-timeline">
            <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500 mb-3">Agent Status</h3>
            <div className="flex flex-wrap gap-2">
              {agents.map((agent) => (
                <AgentStatusPill 
                  key={agent.agent_type} 
                  agent={agent} 
                  isActive={agent.status === "running"}
                />
              ))}
            </div>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-6" data-testid="chat-message-list">
            {messages.map((message, index) => (
              <ChatMessage 
                key={message.id} 
                message={message} 
                isLast={index === messages.length - 1}
              />
            ))}
            {isLoading && messages[messages.length - 1]?.role === "user" && (
              <div className="flex items-center gap-2 text-zinc-500">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-sm">Agent arbeitet...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <div className="p-4 border-t border-zinc-800 bg-zinc-900/50">
            <div className="flex items-end gap-2">
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Nachricht an Agent..."
                rows={2}
                className="flex-1 bg-zinc-800 border border-zinc-700 text-white px-3 py-2.5 rounded-md focus:outline-none focus:border-zinc-500 placeholder:text-zinc-600 resize-none"
                data-testid="chat-input"
              />
              <button
                onClick={() => sendMessage(inputValue)}
                disabled={!inputValue.trim() || isLoading}
                className="p-2.5 bg-white text-black rounded-md hover:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="send-message-btn"
              >
                {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
              </button>
            </div>
          </div>
        </div>

        {/* Right Panel - Preview & Logs */}
        <div className="col-span-1 md:col-span-8 lg:col-span-8 bg-zinc-900/50 flex flex-col h-full overflow-hidden">
          {/* Tabs */}
          <div className="h-12 border-b border-zinc-800 flex items-center px-4 bg-zinc-950/50">
            <div className="flex items-center gap-1">
              {[
                { id: "preview", label: "Preview", icon: Eye },
                { id: "logs", label: "Logs", icon: Terminal },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-all ${
                    activeTab === id
                      ? "border-white text-white"
                      : "border-transparent text-zinc-400 hover:text-zinc-100"
                  }`}
                  data-testid={`tab-${id}`}
                >
                  <Icon size={14} />
                  {label}
                </button>
              ))}
            </div>
            <div className="flex-1" />
            <button className="p-2 text-zinc-400 hover:text-white transition-colors" data-testid="refresh-preview-btn">
              <RefreshCw size={16} />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-hidden">
            {activeTab === "preview" ? (
              <div className="h-full p-4" data-testid="preview-panel">
                <div className="h-full bg-zinc-950 rounded-lg border border-zinc-800 overflow-hidden flex flex-col">
                  {/* Mock Browser Bar */}
                  <div className="h-10 bg-zinc-900 border-b border-zinc-800 flex items-center px-4 gap-2">
                    <div className="flex gap-1.5">
                      <div className="w-3 h-3 rounded-full bg-zinc-700" />
                      <div className="w-3 h-3 rounded-full bg-zinc-700" />
                      <div className="w-3 h-3 rounded-full bg-zinc-700" />
                    </div>
                    <div className="flex-1 mx-4">
                      <div className="bg-zinc-800 rounded px-3 py-1 text-xs text-zinc-500">
                        localhost:3000
                      </div>
                    </div>
                  </div>
                  {/* Preview Content */}
                  <div className="flex-1 flex items-center justify-center text-zinc-600" data-testid="live-preview-iframe">
                    <div className="text-center space-y-4">
                      <div className="w-16 h-16 mx-auto bg-zinc-800 rounded-lg flex items-center justify-center">
                        <Eye size={32} className="text-zinc-600" />
                      </div>
                      <div>
                        <p className="font-medium text-zinc-400">Preview nicht verfügbar</p>
                        <p className="text-sm text-zinc-600">Starte ein Projekt, um die Live-Vorschau zu sehen</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full p-4 overflow-auto" data-testid="log-console-view">
                <div className="terminal h-full bg-zinc-950 rounded-lg border border-zinc-800 p-4 overflow-auto">
                  {logs.length === 0 ? (
                    <div className="text-zinc-600 text-center py-8">
                      <Terminal size={24} className="mx-auto mb-2 opacity-50" />
                      <p>Noch keine Logs vorhanden</p>
                    </div>
                  ) : (
                    logs.map((log) => <LogEntry key={log.id} log={log} />)
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ============== App ==============

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<StartScreen />} />
          <Route path="/workspace/:projectId" element={<Workspace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
